import math
import os
import tempfile

import cv2
import numpy as np
import pytest

from photopicker.backend.grouper import (
    compute_color_hist,
    compute_hashes,
    compute_similarity,
    detect_bursts,
    filename_number,
    filename_prefix,
    group_by_similarity,
    group_photos,
    hash_distance,
    pair_similarity,
    split_by_time,
    split_oversized,
    time_similarity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_image(path: str, color: tuple[int, int, int] = (100, 150, 200),
                size: tuple[int, int] = (64, 64)) -> None:
    """Write a small solid-colour JPEG."""
    img = np.full((size[1], size[0], 3), color, dtype=np.uint8)
    cv2.imwrite(path, img)


@pytest.fixture
def tmp_imgs(tmp_path):
    """Create a few small temp images and return their paths."""
    paths = []
    for i, col in enumerate([(255, 0, 0), (0, 255, 0), (0, 0, 255)]):
        p = str(tmp_path / f"img_{i:04d}.jpg")
        _make_image(p, color=col)
        paths.append(p)
    return paths


# ---------------------------------------------------------------------------
# compute_hashes
# ---------------------------------------------------------------------------

def test_compute_hashes_returns_keys(tmp_imgs):
    result = compute_hashes(tmp_imgs[0])
    assert set(result.keys()) == {"phash", "dhash", "whash", "ahash"}


def test_compute_hashes_deterministic(tmp_imgs):
    a = compute_hashes(tmp_imgs[0])
    b = compute_hashes(tmp_imgs[0])
    assert a == b


def test_compute_hashes_different_images(tmp_path):
    # 纯色图的感知哈希相同（算法正常行为），需要用有纹理差异的图来测试
    # 图0：棋盘格（高频纹理）
    board = np.zeros((64, 64, 3), dtype=np.uint8)
    for r in range(64):
        for c in range(64):
            if (r // 8 + c // 8) % 2 == 0:
                board[r, c] = 255
    p0 = str(tmp_path / "board.jpg")
    cv2.imwrite(p0, board)

    # 图1：水平渐变（低频，与棋盘格结构差异大）
    gradient = np.tile(np.linspace(0, 255, 64, dtype=np.uint8), (64, 1))
    gradient = cv2.cvtColor(gradient, cv2.COLOR_GRAY2BGR)
    p1 = str(tmp_path / "gradient.jpg")
    cv2.imwrite(p1, gradient)

    h0 = compute_hashes(p0)
    h1 = compute_hashes(p1)
    assert h0 != h1, "棋盘格与渐变图的感知哈希应当不同"


def test_compute_hashes_bad_path():
    assert compute_hashes("/nonexistent/path.jpg") == {}


# ---------------------------------------------------------------------------
# compute_color_hist
# ---------------------------------------------------------------------------

def test_compute_color_hist_shape(tmp_imgs):
    hist = compute_color_hist(tmp_imgs[0])
    assert hist is not None
    assert hist.shape == (432,)


def test_compute_color_hist_normalised(tmp_imgs):
    hist = compute_color_hist(tmp_imgs[0])
    assert hist is not None
    assert abs(np.linalg.norm(hist) - 1.0) < 1e-5


def test_compute_color_hist_bad_path():
    assert compute_color_hist("/nonexistent/path.jpg") is None


# ---------------------------------------------------------------------------
# hash_distance
# ---------------------------------------------------------------------------

def test_hash_distance_identical():
    assert hash_distance("abcd1234", "abcd1234") == 0


def test_hash_distance_complement():
    # 0xff ^ 0x00 = 0xff -> 8 bits per byte
    assert hash_distance("ff", "00") == 8


def test_hash_distance_invalid():
    assert hash_distance("zz", "00") == 64


# ---------------------------------------------------------------------------
# time_similarity
# ---------------------------------------------------------------------------

def test_time_similarity_identical():
    assert time_similarity(1000.0, 1000.0) == pytest.approx(1.0)


def test_time_similarity_none():
    assert time_similarity(None, 1000.0) == 0.0


def test_time_similarity_decay():
    # At dt == TIME_HALFLIFE (150s), similarity = exp(-1) ≈ 0.368
    s = time_similarity(0.0, 150.0)
    assert abs(s - math.exp(-1)) < 0.01
    # At dt == 0, similarity == 1
    assert time_similarity(100.0, 100.0) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# filename helpers
# ---------------------------------------------------------------------------

def test_filename_number():
    assert filename_number("IMG_0042.jpg") == 42
    assert filename_number("photo.png") is None


def test_filename_prefix():
    assert filename_prefix("IMG_0042.jpg") == "IMG_"
    assert filename_prefix("photo.jpg") == "photo"


# ---------------------------------------------------------------------------
# detect_bursts
# ---------------------------------------------------------------------------

def test_detect_bursts_basic():
    infos = [
        {"path": "/tmp/a/IMG_001.jpg", "timestamp": 1000.0, "phash": "abcd"},
        {"path": "/tmp/a/IMG_002.jpg", "timestamp": 1000.5, "phash": "abcd"},
        {"path": "/tmp/a/IMG_003.jpg", "timestamp": 1001.0, "phash": "abcd"},
    ]
    bursts = detect_bursts(infos)
    assert len(bursts) >= 1
    # All three should be in one burst
    all_members = set()
    for b in bursts:
        all_members.update(b)
    assert {0, 1, 2}.issubset(all_members)


def test_detect_bursts_different_prefix():
    infos = [
        {"path": "/tmp/a/IMG_001.jpg", "timestamp": 1000.0},
        {"path": "/tmp/a/DSC_002.jpg", "timestamp": 1000.5},
    ]
    bursts = detect_bursts(infos)
    assert len(bursts) == 0


# ---------------------------------------------------------------------------
# split_by_time
# ---------------------------------------------------------------------------

def test_split_by_time_no_gap():
    infos = [
        {"timestamp": 100.0},
        {"timestamp": 200.0},
        {"timestamp": 300.0},
    ]
    segs = split_by_time(infos)
    assert len(segs) == 1


def test_split_by_time_big_gap():
    infos = [
        {"timestamp": 100.0},
        {"timestamp": 200.0},
        {"timestamp": 100.0 + 50 * 60},  # >45 min gap
    ]
    segs = split_by_time(infos)
    assert len(segs) == 2


# ---------------------------------------------------------------------------
# pair_similarity
# ---------------------------------------------------------------------------

def test_pair_similarity_identical():
    info = {
        "path": "/tmp/a/IMG_001.jpg",
        "phash": "abcd1234abcd1234",
        "dhash": "abcd1234abcd1234",
        "whash": "abcd1234abcd1234",
        "ahash": "abcd1234abcd1234",
        "color_hist": np.ones(144, dtype=np.float32) / 12.0,
        "timestamp": 1000.0,
        "exif_meta": {"camera": "Canon EOS R5", "lens": "RF 50mm", "focal_length": "50", "aperture": "f/1.8"},
    }
    s = pair_similarity(info, info)
    assert s > 0.99


def test_pair_similarity_different():
    hist = np.ones(144, dtype=np.float32) / 12.0
    a = {
        "path": "/tmp/a/IMG_001.jpg",
        "phash": "0000000000000000",
        "dhash": "0000000000000000",
        "whash": "0000000000000000",
        "ahash": "0000000000000000",
        "color_hist": hist,
        "timestamp": 1000.0,
    }
    b = {
        "path": "/tmp/b/DSC_9999.jpg",
        "phash": "ffffffffffffffff",
        "dhash": "ffffffffffffffff",
        "whash": "ffffffffffffffff",
        "ahash": "ffffffffffffffff",
        "color_hist": -hist,
        "timestamp": 999999.0,
    }
    s = pair_similarity(a, b)
    assert s < 0.1


# ---------------------------------------------------------------------------
# split_oversized
# ---------------------------------------------------------------------------

def test_split_oversized_small_unchanged():
    groups = [[0, 1, 2]]
    result = split_oversized(groups, [{"timestamp": i} for i in range(3)])
    assert result == [[0, 1, 2]]


def test_split_oversized_large_split():
    infos = [{"timestamp": i * 10.0} for i in range(30)]
    # Add a big gap in the middle
    for i in range(15, 30):
        infos[i]["timestamp"] += 10000.0
    groups = [list(range(30))]
    result = split_oversized(groups, infos)
    assert all(len(g) <= 25 for g in result)
    assert sum(len(g) for g in result) == 30


# ---------------------------------------------------------------------------
# group_photos (integration)
# ---------------------------------------------------------------------------

def test_group_photos_empty():
    assert group_photos({}) == {}


def test_group_photos_single(tmp_imgs):
    result = group_photos({"p0": tmp_imgs[0]})
    assert len(result) == 1
    assert list(result.values())[0] == ["p0"]


def test_group_photos_with_timestamps(tmp_imgs):
    paths = {f"p{i}": p for i, p in enumerate(tmp_imgs)}
    ts = {f"p{i}": 1000.0 + i for i in range(len(tmp_imgs))}
    result = group_photos(paths, timestamps=ts, threshold=0.50)
    assert isinstance(result, dict)
    all_ids = set()
    for ids in result.values():
        all_ids.update(ids)
    assert all_ids == set(paths.keys())


# ---------------------------------------------------------------------------
# Legacy API backward compatibility
# ---------------------------------------------------------------------------

def test_legacy_group_by_similarity():
    features = {
        "a": np.array([1.0, 0.0, 0.0]),
        "b": np.array([0.9, 0.1, 0.0]),
        "c": np.array([0.0, 0.0, 1.0]),
    }
    groups = group_by_similarity(features, threshold=0.8)
    assert len(groups) == 2
    group_sizes = sorted(len(g) for g in groups.values())
    assert group_sizes == [1, 2]


def test_legacy_compute_similarity_identical():
    vec = np.array([1.0, 0.0, 0.0])
    assert abs(compute_similarity(vec, vec) - 1.0) < 1e-6


def test_legacy_compute_similarity_orthogonal():
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([0.0, 1.0, 0.0])
    assert abs(compute_similarity(a, b)) < 1e-6
