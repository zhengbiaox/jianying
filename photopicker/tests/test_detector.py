import numpy as np
import cv2
from photopicker.backend.detector import detect_blur, detect_exposure, calculate_score, detect_quality_with_reasons, detect_faces, detect_quality_with_face

def test_detect_blur_sharp():
    img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    sharpness = detect_blur(img)
    assert sharpness > 0

def test_detect_blur_smooth():
    img = np.ones((100, 100, 3), dtype=np.uint8) * 128
    smoothness = detect_blur(img)
    assert smoothness == 0

def test_detect_exposure_normal():
    img = np.random.randint(80, 180, (100, 100, 3), dtype=np.uint8)
    result = detect_exposure(img)
    assert result["overexposed"] is False
    assert result["underexposed"] is False

def test_detect_exposure_overexposed():
    img = np.ones((100, 100, 3), dtype=np.uint8) * 250
    result = detect_exposure(img)
    assert result["overexposed"] is True

def test_calculate_score_high():
    score = calculate_score(is_closed_eye=False, sharpness=100, exposure_ok=True, is_shake=False)
    assert score >= 80

def test_calculate_score_low_closed_eye():
    score = calculate_score(is_closed_eye=True, sharpness=100, exposure_ok=True, is_shake=False)
    assert score < 50

def test_detect_quality_returns_reasons():
    img = np.ones((100, 100, 3), dtype=np.uint8) * 250
    result = detect_quality_with_reasons(img)
    assert "overexposed" in result["reasons"]
    assert result["score"] < 80

def test_detect_quality_normal():
    img = np.random.randint(80, 180, (100, 100, 3), dtype=np.uint8)
    result = detect_quality_with_reasons(img)
    assert isinstance(result["score"], int)
    assert isinstance(result["reasons"], list)

def test_detect_faces_returns_list():
    img = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
    faces = detect_faces(img)
    assert isinstance(faces, list)

def test_detect_quality_with_face():
    img = np.random.randint(80, 180, (200, 200, 3), dtype=np.uint8)
    result = detect_quality_with_face(img)
    assert "faces" in result
    assert "face_count" in result
    assert isinstance(result["score"], int)
