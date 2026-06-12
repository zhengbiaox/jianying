import numpy as np
from sklearn.cluster import AgglomerativeClustering


def compute_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


def group_by_similarity(features: dict[str, np.ndarray],
                        threshold: float = 0.8) -> dict[str, list[str]]:
    if len(features) == 0:
        return {}
    ids = list(features.keys())
    vectors = np.array([features[k] for k in ids])
    similarity_matrix = np.dot(vectors, vectors.T)
    distance_matrix = 1 - similarity_matrix
    np.fill_diagonal(distance_matrix, 0)
    distance_matrix = np.clip(distance_matrix, 0, None)
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=1 - threshold,
        metric="precomputed",
        linkage="average"
    )
    labels = clustering.fit_predict(distance_matrix)
    groups: dict[str, list[str]] = {}
    for photo_id, label in zip(ids, labels):
        group_key = f"scene_{label}"
        if group_key not in groups:
            groups[group_key] = []
        groups[group_key].append(photo_id)
    return groups
