import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

from photopicker.backend.models import (
    PhotoInfo, PhotoGrade, SceneGroup, FilterLevel, PKResult, ExportRequest, SessionState, GroupState
)
from photopicker.backend.scanner import scan_folder, pair_jpg_raw
from photopicker.backend.grouper import group_photos
from photopicker.backend.detector import detect_blur, detect_exposure, detect_shake, calculate_score, score_to_grade, detect_quality_with_reasons, detect_quality_with_face
from photopicker.backend.exporter import export_photos, export_winners_losers
from photopicker.backend.state import save_session, load_session
from photopicker.backend.cache import get_thumbnail as get_cached_thumbnail
from photopicker.backend.runtime import get_device, device_info
from photopicker.backend.logger import setup_logger, get_logger
from photopicker.backend.watermark import add_watermark, batch_watermark, read_exif
from photopicker.backend.aesthetic import compute_aesthetic_score
from photopicker.backend.preferences import PreferenceTracker

REASON_CN = {
    "blurry": "清晰度不足",
    "very_blurry": "画面较模糊",
    "subject_blurry": "主体不够清晰",
    "motion_blur": "拍摄时抖动",
    "overexposed": "高光过亮",
    "underexposed": "暗部偏暗",
    "closed_eyes": "眼睛未睁开",
    "shake": "手持不稳",
    "low_quality": "画质有待提升",
    "horizon_tilt": "水平线稍有倾斜",
    "horizon_severe": "水平线明显倾斜",
    "low_contrast": "对比度偏低",
    "low_information": "画面内容较少",
    "too_small": "分辨率偏低",
    "tiny_file": "文件体积偏小",
}

app = FastAPI(title="PhotoPicker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8010", "http://localhost:8010", "http://127.0.0.1:8000", "http://localhost:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

photos_db: dict[str, PhotoInfo] = {}
groups_db: dict[str, SceneGroup] = {}
raw_pair_db: dict[str, str | None] = {}
current_folder: str = ""
clip_model = None
clip_preprocess = None
session_state: SessionState | None = None
cache_dir: str = ""
runtime_preference = "auto"

progress_state = {"status": "idle", "done": 0, "total": 0, "label": ""}
pref_tracker: PreferenceTracker | None = None

process_state = {
    "status": "idle",
    "done": 0,
    "total": 0,
    "current_photo": "",
    "rejected_count": 0,
    "groups_count": 0,
    "events": [],
}
process_cancel = threading.Event()

BROKEN_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 360"><rect width="100%" height="100%" fill="#1a1a2e"/><text x="50%" y="50%" text-anchor="middle" font-family="sans-serif" font-size="20" fill="#666">Error</text></svg>'.encode("utf-8")


def _load_clip():
    global clip_model, clip_preprocess
    if clip_model is not None:
        return True
    try:
        import os
        os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
        import torch
        import open_clip
        clip_model, _, clip_preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="laion2b_s34b_b79k"
        )
        clip_model.eval()
        return True
    except Exception as e:
        print(f"CLIP model load failed: {e}")
        clip_model = None
        return False



@app.post("/api/import")
def import_folder(folder_path: str):
    global current_folder, clip_model, session_state, cache_dir, pref_tracker
    current_folder = folder_path
    pref_tracker = PreferenceTracker(folder_path)
    cache_dir = os.path.join(folder_path, ".photopicker_cache")
    setup_logger(folder_path)
    pairs = pair_jpg_raw(folder_path)
    raw_pair_db.clear()
    photos_db.clear()
    for jpg_path, pair_info in pairs.items():
        photo_id = str(uuid.uuid4())[:8]
        photo = PhotoInfo(
            id=photo_id,
            path=jpg_path,
            raw_path=pair_info["raw"],
            xmp_path=pair_info["xmp"],
        )
        photos_db[photo_id] = photo
        raw_pair_db[photo_id] = pair_info["raw"]
    session_state = SessionState(folder=folder_path)
    save_session(session_state, folder_path)
    return {"count": len(photos_db), "message": "Import complete"}


@app.post("/api/reset")
def reset_all():
    global session_state, current_folder, cache_dir, photos_db, groups_db

    if cache_dir and os.path.exists(cache_dir):
        shutil.rmtree(cache_dir, ignore_errors=True)

    if current_folder:
        state_file = os.path.join(current_folder, ".photopicker_state.json")
        if os.path.exists(state_file):
            os.remove(state_file)

    photos_db.clear()
    groups_db.clear()
    session_state = None
    current_folder = ""
    cache_dir = ""

    return {"ok": True, "message": "已重置"}


@app.get("/api/photos")
def get_photos(grade: str | None = None, scene: str | None = None):
    result = list(photos_db.values())
    if grade:
        result = [p for p in result if p.grade.value == grade]
    if scene:
        result = [p for p in result if p.scene_group == scene]
    return result


@app.get("/api/photos/{photo_id}")
def get_photo(photo_id: str):
    if photo_id not in photos_db:
        raise HTTPException(status_code=404, detail="Photo not found")
    return photos_db[photo_id]


@app.get("/api/thumbnail/{photo_id}")
def get_thumbnail(photo_id: str):
    if photo_id not in photos_db:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo = photos_db[photo_id]
    try:
        if cache_dir:
            cached_path = get_cached_thumbnail(photo.path, cache_dir)
            return FileResponse(cached_path, media_type="image/jpeg")
        return FileResponse(photo.path, media_type="image/jpeg")
    except Exception:
        return Response(content=BROKEN_SVG, media_type="image/svg+xml")


@app.get("/api/preview/{photo_id}")
def get_preview(photo_id: str):
    if photo_id not in photos_db:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo = photos_db[photo_id]
    try:
        return FileResponse(
            photo.path,
            media_type="image/jpeg",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )
    except Exception:
        return Response(content=BROKEN_SVG, media_type="image/svg+xml")


@app.post("/api/detect")
def run_detection():
    progress_state["status"] = "detecting"
    progress_state["done"] = 0
    progress_state["total"] = len(photos_db)
    progress_state["label"] = "检测中"
    get_logger().info(f"Starting detection for {len(photos_db)} photos")
    for photo_id, photo in photos_db.items():
        try:
            import cv2
            img = cv2.imread(photo.path)
            if img is None:
                progress_state["done"] += 1
                continue
            result = detect_quality_with_face(img)
            photo.score = result["score"]
            photo.grade = PhotoGrade(result["grade"])
        except Exception:
            pass
        progress_state["done"] += 1
    progress_state["status"] = "done"
    if session_state:
        save_session(session_state, current_folder)
    return {"detected": len(photos_db)}


@app.post("/api/aesthetic")
def run_aesthetic():
    for photo_id, photo in photos_db.items():
        try:
            result = compute_aesthetic_score(photo.path)
            photo.aesthetic_score = result["score"]
        except Exception:
            continue
    return {"scored": len(photos_db)}


@app.post("/api/group")
def run_grouping(threshold: float = 0.38):
    global session_state
    groups_db.clear()

    progress_state["status"] = "grouping"
    progress_state["done"] = 0
    progress_state["total"] = len(photos_db)
    progress_state["label"] = "分组中"
    get_logger().info(f"Starting grouping with threshold {threshold}")

    # Always use multi-signal grouping (time + hash + color + filename)
    photo_paths = {pid: p.path for pid, p in photos_db.items()}
    grouped = group_photos(photo_paths, threshold=threshold)
    progress_state["done"] = len(photos_db)
    print(f"Multi-signal grouping completed for {len(photos_db)} photos")

    for group_id, photo_ids in grouped.items():
        cover_id = photo_ids[0]
        groups_db[group_id] = SceneGroup(
            id=group_id,
            photos=photo_ids,
            cover_photo_id=cover_id
        )
        for pid in photo_ids:
            if pid in photos_db:
                photos_db[pid].scene_group = group_id

    # NO auto-select for single-photo groups — user decides in PK view

    if session_state:
        from photopicker.backend.models import GroupState
        session_state.groups = []
        for gid, g in groups_db.items():
            gs = GroupState(id=gid, images=list(g.photos))
            if len(g.photos) == 1:
                gs.left = g.photos[0]
                gs.right = None
                gs.pending = []
            else:
                gs.left = g.photos[0]
                gs.right = g.photos[1]
                gs.pending = g.photos[2:]
            session_state.groups.append(gs)
        session_state.threshold = threshold
        save_session(session_state, current_folder)

    progress_state["status"] = "done"
    return {"groups": len(groups_db)}


@app.get("/api/groups")
def get_groups():
    return list(groups_db.values())


def advance_group(group: GroupState, action: str) -> dict:
    """Advance the PK state machine (elimination pairing mode).

    Elimination logic — each photo only appears ONCE:
    - 'left': left is selected, right is eliminated. Both slots refilled from pending.
    - 'right': right is selected, left is eliminated. Both slots refilled from pending.
    - 'both': both are selected. Both slots refilled from pending.
    - 'none': both are eliminated. Both slots refilled from pending.
    - 'keep': (single mode) keep the photo as winner.
    - 'reject': (single mode) reject the photo.
    """
    result = {'action': action, 'finished': False, 'winners': []}

    # Single-mode specific actions
    if action == 'keep':
        winner = group.left or group.right
        if winner:
            group.extra_winners.append(winner)
        group.left = None
        group.right = None
        group.finished = True
        result['finished'] = True
        result['winners'] = [winner] if winner else []
        return result

    if action == 'reject':
        victim = group.left or group.right
        if victim:
            group.losers.append(victim)
        group.left = None
        group.right = None
        group.finished = True
        result['finished'] = True
        return result

    # Multi-photo elimination pairing
    if action == 'left':
        # Left selected, right eliminated
        if group.left:
            group.extra_winners.append(group.left)
            result['winners'].append(group.left)
        if group.right:
            group.losers.append(group.right)
        group.left = None
        group.right = None
    elif action == 'right':
        # Right selected, left eliminated
        if group.right:
            group.extra_winners.append(group.right)
            result['winners'].append(group.right)
        if group.left:
            group.losers.append(group.left)
        group.left = None
        group.right = None
    elif action == 'both':
        # Both selected
        if group.left:
            group.extra_winners.append(group.left)
            result['winners'].append(group.left)
        if group.right:
            group.extra_winners.append(group.right)
            result['winners'].append(group.right)
        group.left = None
        group.right = None
    elif action == 'none':
        # Both eliminated
        if group.left:
            group.losers.append(group.left)
        if group.right:
            group.losers.append(group.right)
        group.left = None
        group.right = None

    # Refill BOTH slots from pending
    if group.pending:
        group.left = group.pending.pop(0)
    if group.pending:
        group.right = group.pending.pop(0)

    # Check finished condition: no more photos to show
    if not group.left and not group.right:
        group.finished = True
    elif group.left and not group.right and not group.pending:
        # Odd photo remaining — show as single mode next round
        pass

    result['finished'] = group.finished
    return result


@app.post("/api/pk/advance")
def pk_advance(group_id: str, action: str):
    """Arena PK advance.

    Actions:
    - 'left': champion (left) wins, challenger (right) eliminated
    - 'right': challenger (right) wins, becomes new champion
    - 'both': keep both photos
    - 'none': reject both photos
    - 'keep': (single mode) keep the photo
    - 'reject': (single mode) reject the photo
    """
    if not session_state:
        raise HTTPException(400, "No session")

    if action not in ('left', 'right', 'both', 'none', 'keep', 'reject'):
        raise HTTPException(400, f"Invalid action: {action}")

    target_group = None
    for gs in session_state.groups:
        if gs.id == group_id:
            target_group = gs
            break

    if not target_group:
        raise HTTPException(404, "Group not found")
    if target_group.finished:
        raise HTTPException(400, "Group already finished")

    # Save snapshot for undo
    target_group.save_snapshot()

    # Record which photos are being decided on (before advance changes state)
    left_before = target_group.left
    right_before = target_group.right

    # Mark losers in photos_db
    if action == 'left' and right_before and right_before in photos_db:
        photos_db[right_before].is_rejected = True
        photos_db[right_before].is_selected = False
    elif action == 'right' and left_before and left_before in photos_db:
        photos_db[left_before].is_rejected = True
        photos_db[left_before].is_selected = False
    elif action == 'both':
        # Both kept — mark as selected
        if left_before and left_before in photos_db:
            photos_db[left_before].is_selected = True
        if right_before and right_before in photos_db:
            photos_db[right_before].is_selected = True
    elif action == 'none':
        # Both rejected
        if left_before and left_before in photos_db:
            photos_db[left_before].is_rejected = True
            photos_db[left_before].is_selected = False
        if right_before and right_before in photos_db:
            photos_db[right_before].is_rejected = True
            photos_db[right_before].is_selected = False
    elif action == 'keep':
        victim = left_before or right_before
        if victim and victim in photos_db:
            photos_db[victim].is_selected = True
    elif action == 'reject':
        victim = left_before or right_before
        if victim and victim in photos_db:
            photos_db[victim].is_rejected = True
            photos_db[victim].is_selected = False

    # Advance the state machine
    result = advance_group(target_group, action)

    # The pk_advance endpoint already marked photo states above (before advance),
    # but advance_group also tracks extra_winners/losers.
    # Ensure all extra_winners are marked as selected
    for ew in target_group.extra_winners:
        if ew in photos_db:
            photos_db[ew].is_selected = True
            photos_db[ew].is_rejected = False

    save_session(session_state, current_folder)

    # Return current group state for frontend
    return {
        'action': action,
        'finished': target_group.finished,
        'left': target_group.left,
        'right': target_group.right,
        'pending_count': len(target_group.pending),
        'losers_count': len(target_group.losers),
        'winners_count': len(target_group.extra_winners),
    }


@app.get("/api/pk/status")
def pk_status():
    if not session_state:
        return {"complete": False, "total_groups": 0, "finished_groups": 0, "selected_count": 0}

    total = len(session_state.groups)
    finished = sum(1 for g in session_state.groups if g.finished)
    selected = sum(1 for p in photos_db.values() if p.is_selected)

    return {
        "complete": finished >= total and total > 0,
        "total_groups": total,
        "finished_groups": finished,
        "selected_count": selected,
    }


@app.get("/api/pk/current")
def get_current_pk():
    """Get the current group to process in the PK arena.

    Returns the first unfinished group, or done=True if all finished.
    Multi-photo groups are returned first, then single-photo groups.
    """
    if not session_state:
        raise HTTPException(400, "No session")

    # Sort: multi-photo groups first, single-photo groups after
    multi_groups = [g for g in session_state.groups if len(g.images) > 1 and not g.finished]
    single_groups = [g for g in session_state.groups if len(g.images) == 1 and not g.finished]
    unfinished = multi_groups + single_groups

    if not unfinished:
        total = len(session_state.groups)
        finished = sum(1 for g in session_state.groups if g.finished)
        return {
            'done': True,
            'total_groups': total,
            'finished_groups': finished,
            'selected_count': sum(1 for p in photos_db.values() if p.is_selected),
            'rejected_count': sum(1 for p in photos_db.values() if p.is_rejected),
        }

    g = unfinished[0]
    total = len(session_state.groups)
    finished = sum(1 for gs in session_state.groups if gs.finished)
    # Single mode: originally 1 photo, OR odd remaining photo (left filled but right empty, no pending)
    is_single = len(g.images) == 1 or (g.left and not g.right and not g.pending)

    return {
        'done': False,
        'group_id': g.id,
        'group_size': len(g.images),
        'is_single': is_single,
        'left': g.left,
        'right': g.right,
        'pending_count': len(g.pending),
        'losers_count': len(g.losers),
        'winners_count': len(g.extra_winners),
        'decided_count': len(g.losers) + len(g.extra_winners),
        'total_groups': total,
        'finished_groups': finished,
        'multi_remaining': len(multi_groups),
        'single_remaining': len(single_groups),
    }


@app.get("/api/pk/group_state")
def get_group_state(group_id: str):
    if not session_state:
        raise HTTPException(400, "No session")
    for gs in session_state.groups:
        if gs.id == group_id:
            return {
                'id': gs.id,
                'left': gs.left,
                'right': gs.right,
                'pending': gs.pending,
                'losers': gs.losers,
                'winner': gs.winner,
                'extra_winners': gs.extra_winners,
                'finished': gs.finished,
            }
    raise HTTPException(404, "Group not found")


@app.post("/api/pk/submit")
def submit_pk(result: PKResult):
    if session_state:
        for gs in session_state.groups:
            if result.winner_id in gs.images or result.loser_id in gs.images:
                gs.save_snapshot()
                break
    if result.loser_id in photos_db:
        p = photos_db[result.loser_id]
        p.is_rejected = True
        p.is_selected = False
        p.is_pending = False
    if result.winner_id in photos_db:
        p = photos_db[result.winner_id]
        p.is_selected = True
        p.is_rejected = False
        p.is_pending = False
    if pref_tracker and result.winner_id in photos_db and result.loser_id in photos_db:
        try:
            winner_stats = compute_aesthetic_score(photos_db[result.winner_id].path).get("breakdown", {})
            loser_stats = compute_aesthetic_score(photos_db[result.loser_id].path).get("breakdown", {})
            pref_tracker.record_choice(winner_stats, loser_stats)
        except Exception:
            pass
    if session_state:
        save_session(session_state, current_folder)
    get_logger().info(f"PK: {result.winner_id} beats {result.loser_id}")
    return {"ok": True}


@app.post("/api/photos/{photo_id}/select")
def select_photo(photo_id: str):
    if photo_id not in photos_db:
        raise HTTPException(status_code=404, detail="Photo not found")
    p = photos_db[photo_id]
    p.is_selected = True
    p.is_rejected = False
    p.is_pending = False
    return p


@app.post("/api/photos/{photo_id}/reject")
def reject_photo(photo_id: str):
    if photo_id not in photos_db:
        raise HTTPException(status_code=404, detail="Photo not found")
    p = photos_db[photo_id]
    p.is_rejected = True
    p.is_selected = False
    p.is_pending = False
    return p


@app.post("/api/photos/{photo_id}/rescue")
def rescue_photo(photo_id: str):
    if photo_id not in photos_db:
        raise HTTPException(status_code=404, detail="Photo not found")
    p = photos_db[photo_id]
    p.is_rejected = False
    p.is_pending = False
    return p


@app.post("/api/pk/skip_pair")
def skip_pair(photo_ids: list[str]):
    for pid in photo_ids:
        if pid in photos_db:
            photos_db[pid].is_pending = True
            photos_db[pid].is_selected = False
            photos_db[pid].is_rejected = False
    if session_state:
        save_session(session_state, current_folder)
    return {"ok": True}


@app.get("/api/pending")
def get_pending():
    return [p for p in photos_db.values() if p.is_pending]


@app.post("/api/pending/{photo_id}/select")
def pending_select(photo_id: str):
    if photo_id not in photos_db:
        raise HTTPException(404)
    photos_db[photo_id].is_pending = False
    photos_db[photo_id].is_selected = True
    photos_db[photo_id].is_rejected = False
    return photos_db[photo_id]


@app.post("/api/pending/{photo_id}/reject")
def pending_reject(photo_id: str):
    if photo_id not in photos_db:
        raise HTTPException(404)
    photos_db[photo_id].is_pending = False
    photos_db[photo_id].is_selected = False
    photos_db[photo_id].is_rejected = True
    return photos_db[photo_id]


@app.post("/api/pending/confirm")
def pending_confirm():
    for p in photos_db.values():
        if p.is_pending:
            p.is_pending = False
            p.is_rejected = True
    if session_state:
        save_session(session_state, current_folder)
    return {"ok": True}


@app.get("/api/rejected")
def get_rejected():
    return [p for p in photos_db.values() if p.is_rejected]


@app.get("/api/selected")
def get_selected():
    return [p for p in photos_db.values() if p.is_selected]


@app.post("/api/filter/grade")
def set_filter_grade(level: FilterLevel):
    for photo in photos_db.values():
        if photo.score >= level.value + 20:
            photo.grade = PhotoGrade.GREEN
        elif photo.score >= level.value:
            photo.grade = PhotoGrade.YELLOW
        else:
            photo.grade = PhotoGrade.RED
    return {"level": level.name}


@app.post("/api/export")
def export_selected(req: ExportRequest):
    selected_photos = [photos_db[pid] for pid in req.photo_ids if pid in photos_db]
    photo_paths = [p.path for p in selected_photos]
    raw_paths = {p.path: p.raw_path for p in selected_photos if p.raw_path}
    xmp_paths = {p.path: p.xmp_path for p in selected_photos if p.xmp_path}
    result = export_photos(photo_paths, raw_paths, req.output_dir, req.folder_name, xmp_paths)
    get_logger().info(f"Exported {len(selected_photos)} photos to {req.output_dir}/{req.folder_name}")
    return result


@app.post("/api/pk/undo")
def pk_undo(group_id: str | None = None):
    if not session_state:
        raise HTTPException(400, "No session")
    if not session_state.groups:
        raise HTTPException(400, "No groups in session")

    target = None
    if group_id:
        # Find specified group
        for gs in session_state.groups:
            if gs.id == group_id:
                target = gs
                break
    else:
        # Find the most recently modified group (last one with undo history)
        # Try current unfinished group first, then any group with undo_stack
        multi_groups = [g for g in session_state.groups if len(g.images) > 1 and not g.finished]
        single_groups = [g for g in session_state.groups if len(g.images) == 1 and not g.finished]
        unfinished = multi_groups + single_groups
        if unfinished and unfinished[0].undo_stack:
            target = unfinished[0]
        else:
            # Find any group with undo history (most recent action)
            for gs in reversed(session_state.groups):
                if gs.undo_stack:
                    target = gs
                    break

    if not target:
        raise HTTPException(400, "Nothing to undo")
    if not target.undo_stack:
        raise HTTPException(400, "Nothing to undo for this group")

    # Get info about what was undone for restoring photo states
    old_losers = set(target.losers)
    old_extra_winners = set(target.extra_winners)
    old_winner = target.winner

    target.undo()

    # Restore photo states for undone photos
    new_losers = set(target.losers)
    new_extra_winners = set(target.extra_winners)

    # Photos that were losers but no longer are
    for pid in old_losers - new_losers:
        if pid in photos_db:
            photos_db[pid].is_rejected = False
    # Photos that were extra_winners but no longer are
    for pid in old_extra_winners - new_extra_winners:
        if pid in photos_db:
            photos_db[pid].is_selected = False
    # If winner was set but undone
    if old_winner and old_winner != target.winner:
        if old_winner in photos_db:
            photos_db[old_winner].is_selected = False

    save_session(session_state, current_folder)
    return {"ok": True, "group_id": target.id}


@app.post("/api/pk/skip")
def pk_skip():
    if not session_state:
        raise HTTPException(400, "No session")
    session_state.current_group = min(
        session_state.current_group + 1,
        len(session_state.groups) - 1
    )
    save_session(session_state, current_folder)
    return {"ok": True, "current_group": session_state.current_group}


@app.post("/api/groups/threshold")
def set_threshold(threshold: float):
    if not session_state:
        raise HTTPException(400, "No session")
    session_state.threshold = threshold
    save_session(session_state, current_folder)
    return {"threshold": threshold}


@app.get("/api/state")
def get_state():
    if not session_state:
        return {"has_session": False}
    return {
        "has_session": True,
        "folder": session_state.folder,
        "current_group": session_state.current_group,
        "total_groups": len(session_state.groups),
        "threshold": session_state.threshold,
        "mode": session_state.mode,
    }


@app.post("/api/state/resume")
def resume_state(folder_path: str):
    global session_state, current_folder, cache_dir
    loaded = load_session(folder_path)
    if not loaded:
        raise HTTPException(404, "No saved state")
    session_state = loaded
    current_folder = folder_path
    cache_dir = os.path.join(folder_path, ".photopicker_cache")
    pairs = pair_jpg_raw(folder_path)
    photos_db.clear()
    for jpg_path, pair_info in pairs.items():
        photo_id = str(uuid.uuid4())[:8]
        photo = PhotoInfo(id=photo_id, path=jpg_path, raw_path=pair_info["raw"], xmp_path=pair_info["xmp"])
        photos_db[photo_id] = photo
    return {"resumed": True, "current_group": session_state.current_group}


@app.post("/api/export/winners")
def export_winners(mode: str = "copy"):
    if not session_state:
        raise HTTPException(400, "No session")
    winners = []
    losers = []
    for pid, photo in photos_db.items():
        if photo.is_selected:
            winners.append(photo.path)
        elif photo.is_rejected:
            losers.append(photo.path)
    # Build raw_paths mapping for JPG->RAW pairing
    raw_paths = {}
    for p in photos_db.values():
        if p.raw_path:
            raw_paths[p.path] = p.raw_path
    result = export_winners_losers(
        folder=current_folder, winners=winners, losers=losers, mode=mode,
        raw_paths=raw_paths
    )
    return result


@app.get("/api/watermark/preview")
def watermark_preview(photo_id: str):
    if photo_id not in photos_db:
        raise HTTPException(404, "Photo not found")
    photo = photos_db[photo_id]
    exif = read_exif(photo.path)
    return {"exif": exif}


@app.post("/api/watermark/batch")
def watermark_batch(style: str = "standard"):
    selected = [p.path for p in photos_db.values() if p.is_selected]
    if not selected:
        raise HTTPException(400, "No selected photos")
    output_dir = os.path.join(current_folder, "watermarked")
    result = batch_watermark(selected, output_dir, style)
    return result


@app.get("/api/runtime")
def get_runtime():
    info = device_info()
    info["preference"] = runtime_preference
    return info

@app.post("/api/runtime")
def set_runtime(preference: str = "auto"):
    global runtime_preference
    runtime_preference = preference
    device = get_device(preference)
    return {"preference": preference, "device": device}


@app.get("/api/exif/{photo_id}")
def get_exif(photo_id: str):
    if photo_id not in photos_db:
        raise HTTPException(404)
    photo = photos_db[photo_id]
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        img = Image.open(photo.path)
        exif_data = img._getexif()
        if not exif_data:
            return {}
        result = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == 'Make':
                result['make'] = str(value).strip()
            elif tag == 'Model':
                result['model'] = str(value).strip()
            elif tag == 'FocalLength':
                result['focal_length'] = str(value)
            elif tag == 'FNumber':
                result['aperture'] = f'f/{float(value)}'
            elif tag == 'ExposureTime':
                if isinstance(value, tuple):
                    result['shutter'] = f'{value[0]}/{value[1]}s'
                else:
                    result['shutter'] = f'{value}s'
            elif tag == 'ISOSpeedRatings':
                result['iso'] = f'ISO{value}'
            elif tag == 'LensModel':
                result['lens'] = str(value).strip()
        return result
    except Exception:
        return {}



@app.get("/api/progress")
def get_progress():
    return progress_state


@app.post("/api/browse_folder")
def browse_folder_native():
    try:
        if sys.platform == "darwin":
            script = 'tell application "System Events" to activate\nset chosen to POSIX path of (choose folder with prompt "选择照片文件夹")\nreturn chosen'
            proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=120)
            if proc.returncode != 0:
                return {"ok": True, "cancelled": True}
            return {"ok": True, "folder": proc.stdout.strip().rstrip("/")}
        elif sys.platform == "win32":
            import tkinter
            from tkinter import filedialog
            root = tkinter.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            chosen = filedialog.askdirectory(title="选择照片文件夹")
            root.destroy()
            if not chosen:
                return {"ok": True, "cancelled": True}
            return {"ok": True, "folder": chosen}
        else:
            proc = subprocess.run(["zenity", "--file-selection", "--directory"], capture_output=True, text=True, timeout=120)
            if proc.returncode != 0:
                return {"ok": True, "cancelled": True}
            return {"ok": True, "folder": proc.stdout.strip()}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/preview_folder")
def preview_folder(folder_path: str):
    p = Path(folder_path)
    if not p.exists():
        raise HTTPException(404, "Folder not found")
    count = 0
    total_size = 0
    for f in p.rglob("*"):
        if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".arw", ".cr3", ".nef", ".raf", ".dng"}:
            count += 1
            total_size += f.stat().st_size
    return {
        "count": count,
        "size_mb": round(total_size / 1024 / 1024, 1),
        "path": str(p)
    }


@app.get("/api/browse")
def browse_directory(path: str = ""):
    if not path:
        path = str(Path.home())
    target = Path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Not a directory")
    dirs = []
    for item in sorted(target.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            dirs.append({"name": item.name, "path": str(item)})
    return {"current": str(target), "parent": str(target.parent), "dirs": dirs}


@app.get("/api/preferences")
def get_preferences():
    if not pref_tracker:
        return {"decisions": 0}
    return pref_tracker.data


def _run_auto_process(folder_path, filter_level, runtime):
    # READ-ONLY GUARANTEE: This function only reads files and updates in-memory state.
    # No files are moved, copied, or modified until /api/export/final is called.
    global session_state, cache_dir, current_folder, runtime_preference
    try:
        process_state["status"] = "running"
        process_state["done"] = 0
        process_state["events"] = []
        process_state["rejected_count"] = 0
        process_state["groups_count"] = 0

        current_folder = folder_path
        cache_dir = os.path.join(folder_path, ".photopicker_cache")
        runtime_preference = runtime

        pairs = pair_jpg_raw(folder_path)
        raw_pair_db.clear()
        photos_db.clear()

        photo_list = []
        for jpg_path, pair_info in pairs.items():
            if process_cancel.is_set():
                process_state["status"] = "stopped"
                return
            photo_id = str(uuid.uuid4())[:8]
            raw_path = pair_info.get("raw") if isinstance(pair_info, dict) else pair_info
            xmp_path = pair_info.get("xmp") if isinstance(pair_info, dict) else None
            photo = PhotoInfo(id=photo_id, path=jpg_path, raw_path=raw_path, xmp_path=xmp_path)
            photos_db[photo_id] = photo
            raw_pair_db[photo_id] = raw_path
            photo_list.append((photo_id, jpg_path))

        process_state["total"] = len(photo_list)

        from concurrent.futures import ThreadPoolExecutor, as_completed
        import cv2

        # --- Phase 1: Quality detection ---
        # OpenCV/MediaPipe are C++ libs that release the GIL,
        # so ThreadPoolExecutor gives real parallelism here (no need for ProcessPool).
        workers = min(8, max(2, (os.cpu_count() or 4)))

        def detect_one(args):
            photo_id, path = args
            try:
                img = cv2.imread(path)
                if img is None:
                    return photo_id, None
                result = detect_quality_with_face(img)
                return photo_id, result
            except Exception:
                return photo_id, None

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(detect_one, (pid, path)): pid
                for pid, path in photo_list
            }
            for future in as_completed(futures):
                if process_cancel.is_set():
                    process_state["status"] = "stopped"
                    executor.shutdown(wait=False, cancel_futures=True)
                    return

                photo_id, result = future.result()
                process_state["done"] += 1

                if result:
                    photos_db[photo_id].score = result["score"]
                    photos_db[photo_id].grade = PhotoGrade(result["grade"])
                    photos_db[photo_id].reasons = [REASON_CN.get(r, r) for r in result.get("reasons", [])]

                    rejected = result["score"] < filter_level
                    process_state["events"].append({
                        "id": photo_id,
                        "name": os.path.basename(photos_db[photo_id].path),
                        "score": result["score"],
                        "rejected": rejected,
                        "reasons": photos_db[photo_id].reasons,
                    })

                    if rejected:
                        process_state["rejected_count"] += 1

        if not process_cancel.is_set():
            photo_paths = {pid: p.path for pid, p in photos_db.items()}
            # Extract timestamps for better grouping
            timestamps = {}
            from PIL import Image as PILImage
            for pid, path in photo_paths.items():
                try:
                    img = PILImage.open(path)
                    exif = img._getexif() or {}
                    dt_str = exif.get(36867) or exif.get(306)  # DateTimeOriginal or DateTime
                    if dt_str:
                        from datetime import datetime
                        dt = datetime.strptime(str(dt_str).strip(), "%Y:%m:%d %H:%M:%S")
                        timestamps[pid] = dt.timestamp()
                    img.close()
                except Exception:
                    pass
            grouped = group_photos(photo_paths, timestamps=timestamps, threshold=0.50)
            groups_db.clear()
            for group_id, photo_ids in grouped.items():
                groups_db[group_id] = SceneGroup(
                    id=group_id, photos=photo_ids, cover_photo_id=photo_ids[0]
                )
                for pid in photo_ids:
                    if pid in photos_db:
                        photos_db[pid].scene_group = group_id
            process_state["groups_count"] = len(groups_db)

            # Sort photos within each group by quality score (highest first)
            for gid, group in groups_db.items():
                group.photos.sort(key=lambda pid: photos_db[pid].score if pid in photos_db else 0, reverse=True)

        # Single-photo groups: do NOT auto-select, let user decide in PK
        # They will be handled as "single mode" in the PK view

        # Sync groups to session_state for undo support
        group_states = []
        for gid, group in groups_db.items():
            gs = GroupState(
                id=gid,
                images=list(group.photos),
            )
            if len(group.photos) == 1:
                # Single photo: put in left slot, right stays empty
                # User decides in PK view (single mode)
                gs.left = group.photos[0]
                gs.right = None
                gs.pending = []
            else:
                gs.left = group.photos[0]
                gs.right = group.photos[1]
                gs.pending = group.photos[2:]
            group_states.append(gs)

        session_state = SessionState(folder=folder_path, filter_level=filter_level, groups=group_states)
        save_session(session_state, folder_path)
        process_state["status"] = "done"

    except Exception as e:
        process_state["status"] = "error"
        process_state["error"] = str(e)


@app.post("/api/auto_process")
def auto_process(folder_path: str, filter_level: int = 60, runtime: str = "auto"):
    global cache_dir
    if process_state["status"] == "running":
        raise HTTPException(400, "Already running")

    process_cancel.clear()
    cache_dir = os.path.join(folder_path, ".photopicker_cache")
    process_state["status"] = "starting"
    process_state["rejected_count"] = 0
    process_state["groups_count"] = 0
    process_state["events"] = []

    thread = threading.Thread(
        target=_run_auto_process,
        args=(folder_path, filter_level, runtime),
        daemon=True
    )
    thread.start()
    return {"status": "started"}


@app.post("/api/auto_process/stop")
def stop_auto_process():
    process_cancel.set()
    return {"status": "stopping"}


@app.get("/api/auto_process/status")
def get_process_status():
    return process_state


@app.post("/api/prescreen/rescue")
def prescreen_rescue(photo_id: str):
    if photo_id not in photos_db:
        raise HTTPException(404, "Photo not found")
    p = photos_db[photo_id]
    p.is_rejected = False
    p.is_pending = False
    return p


@app.post("/api/prescreen/confirm")
def confirm_prescreen():
    """Confirm prescreen results. Photos below threshold that weren't rescued get rejected.
    Rescued photos (is_rejected=False despite low score) are kept for PK.
    """
    threshold = session_state.filter_level if session_state else 60

    # Photos below threshold with is_rejected still False = rescued by user (via /api/photos/{id}/rescue)
    # Photos below threshold with is_rejected unset (neither True nor False initially) = should be rejected
    # The auto_process doesn't pre-reject, so we mark all low-score photos as rejected
    # EXCEPT those the user has explicitly rescued (is_rejected explicitly set to False by rescue endpoint)
    rescued_ids = set()
    for p in photos_db.values():
        if p.score < threshold:
            if not p.is_rejected:
                # Check if user explicitly rescued (the rescue endpoint sets is_rejected=False)
                # We track rescued in the frontend via rescuedIds, so all non-rejected low-score = rescued
                rescued_ids.add(p.id)
            # If already is_rejected=True, keep it rejected

    # Mark remaining low-score photos as rejected
    for p in photos_db.values():
        if p.score < threshold and p.id not in rescued_ids:
            p.is_rejected = True
            p.is_selected = False
            p.is_pending = False

    # Remove rejected photos from PK groups so they don't appear in arena
    if session_state:
        rejected_set = {pid for pid, p in photos_db.items() if p.is_rejected}
        for gs in session_state.groups:
            if gs.finished:
                continue
            # Remove rejected photos from group state
            if gs.left in rejected_set:
                gs.left = None
            if gs.right in rejected_set:
                gs.right = None
            gs.pending = [pid for pid in gs.pending if pid not in rejected_set]
            gs.images = [pid for pid in gs.images if pid not in rejected_set]

            # Refill slots
            if gs.left is None and gs.pending:
                gs.left = gs.pending.pop(0)
            if gs.right is None and gs.pending:
                gs.right = gs.pending.pop(0)

            # Mark group finished if empty
            if not gs.left and not gs.right and not gs.pending:
                gs.finished = True

        save_session(session_state, current_folder)

    return {"confirmed": True, "rescued": len(rescued_ids)}


@app.get("/api/final_confirm")
def final_confirm():
    selected = [p for p in photos_db.values() if p.is_selected]
    rejected = [p for p in photos_db.values() if p.is_rejected]
    return {
        "入选": len(selected),
        "未入选": len(rejected),
        "total": len(photos_db),
    }


@app.post("/api/export/final")
def export_final(mode: str = "copy"):
    selected = [p.path for p in photos_db.values() if p.is_selected]
    rejected = [p.path for p in photos_db.values() if p.is_rejected]
    # Build raw_paths mapping for JPG->RAW pairing
    raw_paths = {}
    for p in photos_db.values():
        if p.raw_path:
            raw_paths[p.path] = p.raw_path
    result = export_winners_losers(
        folder=current_folder, winners=selected, losers=rejected, mode=mode,
        raw_paths=raw_paths
    )
    return result


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIST / "index.html"))
