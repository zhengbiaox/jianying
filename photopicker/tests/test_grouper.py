import numpy as np
from photopicker.backend.grouper import compute_similarity, group_by_similarity

def test_compute_similarity_identical():
    vec = np.array([1.0, 0.0, 0.0])
    sim = compute_similarity(vec, vec)
    assert abs(sim - 1.0) < 0.001

def test_compute_similarity_orthogonal():
    vec_a = np.array([1.0, 0.0, 0.0])
    vec_b = np.array([0.0, 1.0, 0.0])
    sim = compute_similarity(vec_a, vec_b)
    assert abs(sim) < 0.001

def test_group_by_similarity_basic():
    features = {
        "a": np.array([1.0, 0.0, 0.0]),
        "b": np.array([0.9, 0.1, 0.0]),
        "c": np.array([0.0, 0.0, 1.0]),
    }
    groups = group_by_similarity(features, threshold=0.8)
    assert len(groups) == 2
    group_sizes = [len(g) for g in groups.values()]
    assert 2 in group_sizes
    assert 1 in group_sizes
