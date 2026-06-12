import os
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
from photopicker.backend.grouper import group_by_similarity, extract_phash_features
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
        return FileResponse(photo.path, media_type="image/jpeg")
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
def run_grouping(threshold: float = 0.75):
    global session_state
    groups_db.clear()
    features = {}

    progress_state["status"] = "grouping"
    progress_state["done"] = 0
    progress_state["total"] = len(photos_db)
    progress_state["label"] = "分组中"
    get_logger().info(f"Starting grouping with threshold {threshold}")

    use_clip = _load_clip()

    if use_clip:
        import torch
        from PIL import Image
        device = get_device(runtime_preference)
        clip_model.to(device)
        for photo_id, photo in photos_db.items():
            try:
                img = Image.open(photo.path).convert("RGB")
                image = clip_preprocess(img).unsqueeze(0).to(device)
                with torch.no_grad():
                    feat = clip_model.encode_image(image)
                    feat = feat / feat.norm(dim=-1, keepdim=True)
                features[photo_id] = feat.squeeze().cpu().numpy()
            except Exception:
                pass
            progress_state["done"] += 1
        print(f"CLIP: extracted features for {len(features)} photos")
    else:
        photo_paths = {pid: p.path for pid, p in photos_db.items()}
        features = extract_phash_features(photo_paths)
        progress_state["done"] = len(photos_db)
        print(f"pHash: extracted features for {len(features)} photos")

    grouped = group_by_similarity(features, threshold)
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

    for gid, group in groups_db.items():
        if len(group.photos) == 1:
            pid = group.photos[0]
            if pid in photos_db:
                photos_db[pid].is_selected = True

    if session_state:
        from photopicker.backend.models import GroupState
        session_state.groups = [
            GroupState(id=gid, images=list(g.photos))
            for gid, g in groups_db.items()
        ]
        session_state.threshold = threshold
        save_session(session_state, current_folder)

    progress_state["status"] = "done"
    return {"groups": len(groups_db), "method": "clip" if use_clip else "phash"}


@app.get("/api/groups")
def get_groups():
    return list(groups_db.values())


@app.post("/api/pk/submit")
def submit_pk(result: PKResult):
    if session_state:
        for gs in session_state.groups:
            if result.winner_id in gs.images or result.loser_id in gs.images:
                gs.save_snapshot()
                break
    if result.loser_id in photos_db:
        photos_db[result.loser_id].is_rejected = True
    if result.winner_id in photos_db:
        photos_db[result.winner_id].is_selected = True
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
    photos_db[photo_id].is_selected = True
    photos_db[photo_id].is_rejected = False
    return photos_db[photo_id]


@app.post("/api/photos/{photo_id}/reject")
def reject_photo(photo_id: str):
    if photo_id not in photos_db:
        raise HTTPException(status_code=404, detail="Photo not found")
    photos_db[photo_id].is_rejected = True
    photos_db[photo_id].is_selected = False
    return photos_db[photo_id]


@app.post("/api/photos/{photo_id}/rescue")
def rescue_photo(photo_id: str):
    if photo_id not in photos_db:
        raise HTTPException(status_code=404, detail="Photo not found")
    photos_db[photo_id].is_rejected = False
    return photos_db[photo_id]


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
def pk_undo():
    if not session_state:
        raise HTTPException(400, "No session")
    if not session_state.groups:
        raise HTTPException(400, "No groups in session")
    idx = session_state.current_group
    if idx < 0 or idx >= len(session_state.groups):
        raise HTTPException(400, f"Invalid group index: {idx}")
    current = session_state.groups[idx]
    if not current.undo_stack:
        raise HTTPException(400, "Nothing to undo")
    current.undo()
    save_session(session_state, current_folder)
    return {"ok": True}


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
    result = export_winners_losers(
        folder=current_folder, winners=winners, losers=losers, mode=mode
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

        import cv2
        workers = min(8, max(2, (os.cpu_count() or 4)))
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
            features = extract_phash_features(photo_paths)
            grouped = group_by_similarity(features, 0.75)
            groups_db.clear()
            for group_id, photo_ids in grouped.items():
                groups_db[group_id] = SceneGroup(
                    id=group_id, photos=photo_ids, cover_photo_id=photo_ids[0]
                )
                for pid in photo_ids:
                    if pid in photos_db:
                        photos_db[pid].scene_group = group_id
            process_state["groups_count"] = len(groups_db)

        for gid, group in groups_db.items():
            if len(group.photos) == 1:
                pid = group.photos[0]
                if pid in photos_db:
                    photos_db[pid].is_selected = True

        # Sync groups to session_state for undo support
        group_states = []
        for gid, group in groups_db.items():
            gs = GroupState(
                id=gid,
                images=list(group.photos),
            )
            if len(group.photos) == 1:
                gs.winner = group.photos[0]
                gs.finished = True
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
    photos_db[photo_id].is_rejected = False
    return photos_db[photo_id]


@app.post("/api/prescreen/confirm")
def confirm_prescreen():
    threshold = session_state.filter_level if session_state else 60
    for p in photos_db.values():
        if p.score < threshold:
            p.is_rejected = True
    return {"confirmed": True}


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
    result = export_winners_losers(
        folder=current_folder, winners=selected, losers=rejected, mode=mode
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
