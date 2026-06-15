import tempfile
import os
import numpy as np
import cv2
from photopicker.backend.aesthetic import compute_aesthetic_score


def test_aesthetic_random_image():
    with tempfile.TemporaryDirectory() as tmpdir:
        img = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        path = os.path.join(tmpdir, "test.jpg")
        cv2.imwrite(path, img)
        result = compute_aesthetic_score(path)
        assert "score" in result
        assert 0 <= result["score"] <= 100
        assert "breakdown" in result


def test_aesthetic_black_image():
    with tempfile.TemporaryDirectory() as tmpdir:
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        path = os.path.join(tmpdir, "black.jpg")
        cv2.imwrite(path, img)
        result = compute_aesthetic_score(path)
        assert result["score"] < 50
