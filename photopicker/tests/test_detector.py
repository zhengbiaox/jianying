import numpy as np
import cv2
from photopicker.backend.detector import (
    detect_blur, detect_exposure, calculate_score, detect_quality_with_reasons,
    detect_faces, detect_quality_with_face,
    tenengrad, fft_high_freq_ratio, edge_width_marziliano, nine_grid_exposure,
    horizon_tilt_degrees, saliency_map, salient_sharpness, detect_quality_enhanced,
)

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


def test_tenengrad_sharp():
    rng = np.random.default_rng(42)
    arr = rng.integers(0, 255, (100, 100)).astype(np.float32)
    val = tenengrad(arr)
    assert val > 0
    flat = np.ones((100, 100), dtype=np.float32) * 128
    assert tenengrad(flat) == 0.0


def test_fft_high_freq():
    rng = np.random.default_rng(42)
    arr = rng.integers(0, 255, (128, 128)).astype(np.float32)
    high_ratio, aniso = fft_high_freq_ratio(arr)
    assert 0 <= high_ratio <= 1
    assert 0 <= aniso <= 1
    flat = np.ones((128, 128), dtype=np.float32) * 128
    hr, an = fft_high_freq_ratio(flat)
    assert hr == 0.0


def test_nine_grid_exposure():
    arr = np.ones((90, 90), dtype=np.float32) * 128
    result = nine_grid_exposure(arr)
    assert result["worst_dark"] == 128
    assert result["worst_bright"] == 128
    dark = np.zeros((90, 90), dtype=np.float32)
    result2 = nine_grid_exposure(dark)
    assert result2["worst_dark"] == 0


def test_horizon_tilt():
    arr = np.zeros((200, 200), dtype=np.float32)
    arr[100, :] = 255
    result = horizon_tilt_degrees(arr)
    assert result is None or isinstance(result, float)
    small = np.ones((10, 10), dtype=np.float32) * 128
    assert horizon_tilt_degrees(small) is None


def test_saliency_map():
    rng = np.random.default_rng(42)
    arr = rng.integers(0, 255, (100, 100)).astype(np.float32)
    smap = saliency_map(arr)
    if smap is not None:
        assert smap.shape == (100, 100)
        assert smap.min() >= 0
        assert smap.max() <= 1
    small = np.ones((5, 5), dtype=np.float32) * 128
    assert saliency_map(small) is None


def test_detect_quality_enhanced():
    rng = np.random.default_rng(42)
    img = rng.integers(0, 255, (200, 200, 3)).astype(np.uint8)
    result = detect_quality_enhanced(img)
    assert "score" in result
    assert "grade" in result
    assert "reasons" in result
    assert "blur_combined" in result
    assert "salient_sharpness" in result
    assert "horizon_tilt" in result
    assert 0 <= result["score"] <= 100
