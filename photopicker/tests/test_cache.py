import tempfile
import os
import numpy as np
import cv2
from photopicker.backend.cache import get_thumbnail, clear_cache

def test_get_thumbnail_creates_cache():
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "test.jpg")
        img = np.random.randint(0, 255, (1000, 1000, 3), dtype=np.uint8)
        cv2.imwrite(img_path, img)
        cache_dir = os.path.join(tmpdir, "cache")
        thumb_path = get_thumbnail(img_path, cache_dir)
        assert os.path.exists(thumb_path)
        thumb = cv2.imread(thumb_path)
        assert thumb.shape[0] <= 800

def test_get_thumbnail_returns_cached():
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "test.jpg")
        img = np.random.randint(0, 255, (1000, 1000, 3), dtype=np.uint8)
        cv2.imwrite(img_path, img)
        cache_dir = os.path.join(tmpdir, "cache")
        path1 = get_thumbnail(img_path, cache_dir)
        path2 = get_thumbnail(img_path, cache_dir)
        assert path1 == path2
