import numpy as np
from unittest.mock import patch, MagicMock


def test_get_device_returns_string():
    from photopicker.backend.vision import get_device
    device = get_device()
    assert isinstance(device, str)
    assert device in ('cpu', 'cuda', 'mps')


def test_load_clip_fails_gracefully():
    import photopicker.backend.vision as vis
    old = vis._clip_model
    vis._clip_model = None
    try:
        with patch('builtins.__import__', side_effect=ImportError('no open_clip')):
            result = vis.load_clip()
            assert result is False
    finally:
        vis._clip_model = old


def test_load_dinov2_fails_gracefully():
    from photopicker.backend.vision import load_dinov2
    with patch.dict('sys.modules', {'torch': None}):
        result = load_dinov2()
        assert result is False


def test_load_insightface_fails_gracefully():
    from photopicker.backend.vision import load_insightface
    with patch.dict('sys.modules', {'insightface': None}):
        result = load_insightface()
        assert result is False


def test_extract_clip_features_returns_none_when_unavailable():
    from photopicker.backend.vision import extract_clip_features
    with patch('photopicker.backend.vision.load_clip', return_value=False):
        result = extract_clip_features('/nonexistent.jpg')
        assert result is None


def test_extract_dinov2_features_returns_none_when_unavailable():
    from photopicker.backend.vision import extract_dinov2_features
    with patch('photopicker.backend.vision.load_dinov2', return_value=False):
        result = extract_dinov2_features('/nonexistent.jpg')
        assert result is None


def test_detect_faces_returns_empty_when_unavailable():
    from photopicker.backend.vision import detect_faces
    with patch('photopicker.backend.vision.load_insightface', return_value=False):
        result = detect_faces('/nonexistent.jpg')
        assert result == []


def test_detect_closed_eyes_returns_false_when_unavailable():
    from photopicker.backend.vision import detect_closed_eyes
    with patch('photopicker.backend.vision.load_insightface', return_value=False):
        result = detect_closed_eyes('/nonexistent.jpg')
        assert result is False


def test_get_model_status_structure():
    from photopicker.backend.vision import get_model_status
    status = get_model_status()
    assert 'clip' in status
    assert 'dinov2' in status
    assert 'insightface' in status
    assert 'device' in status
    assert isinstance(status['clip'], bool)
    assert isinstance(status['dinov2'], bool)
    assert isinstance(status['insightface'], bool)


def test_extract_clip_features_handles_invalid_path():
    from photopicker.backend.vision import extract_clip_features
    with patch('photopicker.backend.vision.load_clip', return_value=True):
        with patch('photopicker.backend.vision._clip_preprocess', None):
            result = extract_clip_features('/nonexistent.jpg')
            assert result is None


def test_extract_dinov2_features_handles_invalid_path():
    from photopicker.backend.vision import extract_dinov2_features
    with patch('photopicker.backend.vision.load_dinov2', return_value=True):
        with patch('photopicker.backend.vision._dinov2_model', None):
            result = extract_dinov2_features('/nonexistent.jpg')
            assert result is None
