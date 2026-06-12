import os
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from photopicker.backend.models import (
    PhotoInfo, PhotoGrade, SceneGroup, FilterLevel, PKResult, ExportRequest, SessionState
)
from photopicker.backend.scanner import scan_folder, pair_jpg_raw
from photopicker.backend.grouper import group_by_similarity, extract_phash_features
from photopicker.backend.detector import detect_blur, detect_exposure, detect_shake, calculate_score, score_to_grade, detect_quality_with_reasons, detect_quality_with_face
from photopicker.backend.exporter import export_photos, export_winners_losers
from photopicker.backend.state import save_session, load_session
from photopicker.backend.cache import get_thumbnail as get_cached_thumbnail
from photopicker.backend.runtime import get_device, device_info

app = FastAPI(title="PhotoPicker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    global current_folder, clip_model, session_state, cache_dir
    current_folder = folder_path
    cache_dir = os.path.join(folder_path, ".photopicker_cache")
    pairs = pair_jpg_raw(folder_path)
    raw_pair_db.clear()
    photos_db.clear()
    for jpg_path, raw_path in pairs.items():
        photo_id = str(uuid.uuid4())[:8]
        photo = PhotoInfo(
            id=photo_id,
            path=jpg_path,
            raw_path=raw_path,
        )
        photos_db[photo_id] = photo
        raw_pair_db[photo_id] = raw_path
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
    if cache_dir:
        cached_path = get_cached_thumbnail(photo.path, cache_dir)
        return FileResponse(cached_path, media_type="image/jpeg")
    return FileResponse(photo.path, media_type="image/jpeg")


@app.post("/api/detect")
def run_detection():
    for photo_id, photo in photos_db.items():
        try:
            import cv2
            img = cv2.imread(photo.path)
            if img is None:
                continue
            result = detect_quality_with_face(img)
            photo.score = result["score"]
            photo.grade = PhotoGrade(result["grade"])
        except Exception:
            continue
    if session_state:
        save_session(session_state, current_folder)
    return {"detected": len(photos_db)}


@app.post("/api/group")
def run_grouping(threshold: float = 0.75):
    global session_state
    groups_db.clear()
    features = {}

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
                continue
        print(f"CLIP: extracted features for {len(features)} photos")
    else:
        photo_paths = {pid: p.path for pid, p in photos_db.items()}
        features = extract_phash_features(photo_paths)
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
    if session_state:
        save_session(session_state, current_folder)
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
    result = export_photos(photo_paths, raw_paths, req.output_dir, req.folder_name)
    return result


@app.post("/api/pk/undo")
def pk_undo():
    if not session_state:
        raise HTTPException(400, "No session")
    current = session_state.groups[session_state.current_group] if session_state.groups else None
    if not current:
        raise HTTPException(400, "No current group")
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
    for jpg_path, raw_path in pairs.items():
        photo_id = str(uuid.uuid4())[:8]
        photo = PhotoInfo(id=photo_id, path=jpg_path, raw_path=raw_path)
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
