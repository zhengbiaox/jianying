import hashlib
import os
from pathlib import Path
import cv2

THUMB_MAX_SIZE = 800
THUMB_QUALITY = 85


def _thumb_cache_key(img_path: str) -> str:
    stat = os.stat(img_path)
    raw = f"{img_path}:{stat.st_size}:{stat.st_mtime}"
    return hashlib.md5(raw.encode()).hexdigest()


def get_thumbnail(img_path: str, cache_dir: str) -> str:
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    key = _thumb_cache_key(img_path)
    ext = Path(img_path).suffix.lower()
    cached = cache_path / f"{key}{ext}"
    if cached.exists():
        return str(cached)
    img = cv2.imread(img_path)
    if img is None:
        return img_path
    h, w = img.shape[:2]
    if max(h, w) > THUMB_MAX_SIZE:
        scale = THUMB_MAX_SIZE / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(cached), img, [cv2.IMWRITE_JPEG_QUALITY, THUMB_QUALITY])
    return str(cached)


def clear_cache(cache_dir: str) -> int:
    p = Path(cache_dir)
    if not p.exists():
        return 0
    count = 0
    for f in p.iterdir():
        if f.is_file():
            f.unlink()
            count += 1
    return count
