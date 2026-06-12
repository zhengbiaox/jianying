import os
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from photopicker.backend.models import (
    PhotoInfo, PhotoGrade, SceneGroup, FilterLevel, PKResult, ExportRequest
)
from photopicker.backend.scanner import scan_folder, pair_jpg_raw
from photopicker.backend.grouper import group_by_similarity
from photopicker.backend.detector import detect_blur, detect_exposure, detect_shake, calculate_score, score_to_grade
from photopicker.backend.exporter import export_photos

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


@app.post("/api/import")
def import_folder(folder_path: str):
    global current_folder, clip_model
    current_folder = folder_path
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
    return FileResponse(photo.path, media_type="image/jpeg")


@app.post("/api/detect")
def run_detection():
    for photo_id, photo in photos_db.items():
        try:
            import cv2
            img = cv2.imread(photo.path)
            if img is None:
                continue
            sharpness = detect_blur(img)
            exposure = detect_exposure(img)
            shake = detect_shake(img)
            score = calculate_score(
                is_closed_eye=False,
                sharpness=sharpness,
                exposure_ok=not exposure["overexposed"] and not exposure["underexposed"],
                is_shake=shake
            )
            photo.score = score
            photo.grade = score_to_grade(score, FilterLevel.BALANCED.value)
        except Exception:
            continue
    return {"detected": len(photos_db)}


@app.post("/api/group")
def run_grouping(threshold: float = 0.8):
    import torch
    import open_clip
    global clip_model
    if clip_model is None:
        clip_model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="laion2b_s34b_b79k"
        )
        tokenizer = open_clip.get_tokenizer("ViT-B-32")
    groups_db.clear()
    features = {}
    for photo_id, photo in photos_db.items():
        try:
            from PIL import Image
            img = Image.open(photo.path).convert("RGB")
            image = preprocess(img).unsqueeze(0)
            with torch.no_grad():
                feat = clip_model.encode_image(image)
                feat = feat / feat.norm(dim=-1, keepdim=True)
            features[photo_id] = feat.squeeze().numpy()
        except Exception:
            continue
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
    return {"groups": len(groups_db)}


@app.get("/api/groups")
def get_groups():
    return list(groups_db.values())


@app.post("/api/pk/submit")
def submit_pk(result: PKResult):
    if result.loser_id in photos_db:
        photos_db[result.loser_id].is_rejected = True
    if result.winner_id in photos_db:
        photos_db[result.winner_id].is_selected = True
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
