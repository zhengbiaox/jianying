import math
import re
from pathlib import Path

import cv2
import imagehash
import numpy as np
from PIL import Image


# ---------------------------------------------------------------------------
# 1. Multi-hash feature extraction
# ---------------------------------------------------------------------------

def compute_hashes(img_path: str) -> dict:
    """Compute multiple perceptual hashes for an image."""
    try:
        img = Image.open(img_path).convert("RGB")
        img.thumbnail((512, 512), Image.Resampling.LANCZOS)
        return {
            "phash": str(imagehash.phash(img, hash_size=8)),
            "dhash": str(imagehash.dhash(img, hash_size=8)),
            "whash": str(imagehash.whash(img, hash_size=8)),
            "ahash": str(imagehash.average_hash(img, hash_size=8)),
        }
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# 2. HSV colour histogram (3x3 blocks, 144-dim, L2-normalised)
# ---------------------------------------------------------------------------

def compute_color_hist(img_path: str) -> np.ndarray | None:
    """HSV 3x3 block histogram (144-dim). L2 normalised."""
    try:
        img = cv2.imread(img_path)
        if img is None:
            return None
        h, w = img.shape[:2]
        if max(h, w) > 384:
            scale = 384.0 / max(h, w)
            img = cv2.resize(
                img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA
            )
            h, w = img.shape[:2]
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        feats = []
        ys = [0, h // 3, 2 * h // 3, h]
        xs = [0, w // 3, 2 * w // 3, w]
        for i in range(3):
            for j in range(3):
                block = hsv[ys[i] : ys[i + 1], xs[j] : xs[j + 1]]
                hist_h = cv2.calcHist([block], [0], None, [16], [0, 180]).flatten()
                hist_s = cv2.calcHist([block], [1], None, [16], [0, 256]).flatten()
                hist_v = cv2.calcHist([block], [2], None, [16], [0, 256]).flatten()
                for arr in (hist_h, hist_s, hist_v):
                    s = arr.sum()
                    if s > 0:
                        arr /= s
                feats.extend([hist_h, hist_s, hist_v])
        vec = np.concatenate(feats).astype(np.float32)
        n = float(np.linalg.norm(vec))
        if n < 1e-8:
            return None
        return vec / n
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 3. Hamming distance
# ---------------------------------------------------------------------------

def hash_distance(h1: str, h2: str) -> int:
    """Hamming distance between two hex hash strings."""
    try:
        return bin(int(h1, 16) ^ int(h2, 16)).count("1")
    except (ValueError, TypeError):
        return 64


# ---------------------------------------------------------------------------
# 4. Time similarity
# ---------------------------------------------------------------------------

TIME_HALFLIFE = 150.0  # seconds


def time_similarity(t1: float | None, t2: float | None) -> float:
    """Exponential-decay time similarity."""
    if t1 is None or t2 is None:
        return 0.0
    dt = abs(t1 - t2)
    return math.exp(-dt / TIME_HALFLIFE)


# ---------------------------------------------------------------------------
# 5. Face clustering
# ---------------------------------------------------------------------------

FACE_SIMILARITY_THRESHOLD = 0.6


def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-8 or norm_b < 1e-8:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def cluster_faces(photo_list: list[dict]) -> dict[str, list[str]]:
    """Cluster photos by face embeddings using union-find.

    Args:
        photo_list: List of dicts with 'photo_id' and 'face_embeddings'.

    Returns:
        {group_id: [photo_ids]} for groups with at least one face.
    """
    n = len(photo_list)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    face_indices = []
    for i, photo in enumerate(photo_list):
        embeddings = photo.get("face_embeddings", [])
        if embeddings:
            face_indices.append((i, embeddings))

    if not face_indices:
        return {}

    for i, (idx_a, emb_a) in enumerate(face_indices):
        for j in range(i + 1, len(face_indices)):
            idx_b, emb_b = face_indices[j]
            for ea in emb_a:
                for eb in emb_b:
                    if cosine_similarity(ea, eb) >= FACE_SIMILARITY_THRESHOLD:
                        union(idx_a, idx_b)
                        break
                else:
                    continue
                break

    clusters = {}
    for idx, embeddings in face_indices:
        root = find(idx)
        if root not in clusters:
            clusters[root] = []
        clusters[root].append(photo_list[idx]["photo_id"])

    result = {}
    for root, members in clusters.items():
        group_id = f"face_{root}"
        result[group_id] = members

    return result


# ---------------------------------------------------------------------------
# 6. Filename burst detection
# ---------------------------------------------------------------------------

BURST_NUMBER_DELTA = 3
BURST_TIME_GAP = 1.2  # seconds
BURST_HASH_MAX = 18


def filename_number(name: str) -> int | None:
    """Extract trailing number from filename stem."""
    m = re.search(r"(\d+)(?=\.[^.]+$|$)", name)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def filename_prefix(name: str) -> str:
    """Get filename prefix before trailing number."""
    base = name.rsplit(".", 1)[0]
    m = re.match(r"^(.*?)(\d+)$", base)
    return m.group(1) if m else base


def detect_bursts(file_infos: list[dict]) -> list[set[int]]:
    """Detect burst sequences by filename + time."""
    keyed = []
    for i, info in enumerate(file_infos):
        name = Path(info["path"]).name
        num = filename_number(name)
        if num is None:
            continue
        prefix = filename_prefix(name)
        t = info.get("timestamp")
        keyed.append((prefix, num, t, i))

    if not keyed:
        return []

    keyed.sort(key=lambda x: (x[0], x[1]))

    n = len(file_infos)
    union = list(range(n))

    def find(x: int) -> int:
        while union[x] != x:
            union[x] = union[union[x]]
            x = union[x]
        return x

    def merge(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            union[ra] = rb

    for j in range(1, len(keyed)):
        p0, n0, t0, i0 = keyed[j - 1]
        p1, n1, t1, i1 = keyed[j]
        if p0 != p1:
            continue
        if n1 - n0 > BURST_NUMBER_DELTA:
            continue
        if t0 is not None and t1 is not None and (t1 - t0) > BURST_TIME_GAP:
            continue
        h0 = file_infos[i0].get("phash")
        h1 = file_infos[i1].get("phash")
        if h0 and h1:
            ham = hash_distance(h0, h1)
            if ham > BURST_HASH_MAX:
                continue
        merge(i0, i1)

    groups: dict[int, set[int]] = {}
    for i in range(n):
        r = find(i)
        groups.setdefault(r, set()).add(i)
    return [g for g in groups.values() if len(g) >= 2]


# ---------------------------------------------------------------------------
# 6. Time hard break
# ---------------------------------------------------------------------------

HARD_BREAK_SECONDS = 45 * 60  # 45 minutes


def split_by_time(file_infos: list[dict]) -> list[list[int]]:
    """Split photos into segments by time gaps > 45 minutes."""
    if not file_infos:
        return []
    indexed = [
        (i, file_infos[i].get("timestamp") or 0) for i in range(len(file_infos))
    ]
    indexed.sort(key=lambda x: x[1])
    segments = [[indexed[0][0]]]
    for idx, t in indexed[1:]:
        t_prev = file_infos[segments[-1][-1]].get("timestamp") or 0
        if t > 0 and t_prev > 0 and (t - t_prev) > HARD_BREAK_SECONDS:
            segments.append([idx])
        else:
            segments[-1].append(idx)
    return segments


# ---------------------------------------------------------------------------
# 7. Pairwise similarity (multi-signal fusion)
# ---------------------------------------------------------------------------

def pair_similarity(info_a: dict, info_b: dict) -> float:
    """Compute multi-signal similarity between two photos. Returns [0, 1]."""
    # Hash similarity (4 hashes)
    hash_sims = []
    for key in ("phash", "dhash", "whash", "ahash"):
        h1 = info_a.get(key)
        h2 = info_b.get(key)
        if h1 and h2:
            d = hash_distance(h1, h2)
            hash_sims.append(max(0, 1 - d / 32))
    sim_hash = float(np.mean(hash_sims)) if hash_sims else 0.0

    # Colour histogram similarity
    c1 = info_a.get("color_hist")
    c2 = info_b.get("color_hist")
    if c1 is not None and c2 is not None:
        sim_color = float(np.dot(c1, c2))
    else:
        sim_color = 0.0

    # Time similarity
    t1 = info_a.get("timestamp")
    t2 = info_b.get("timestamp")
    sim_time = time_similarity(t1, t2)

    # Filename similarity
    n1 = filename_number(Path(info_a["path"]).name)
    n2 = filename_number(Path(info_b["path"]).name)
    p1 = filename_prefix(Path(info_a["path"]).name)
    p2 = filename_prefix(Path(info_b["path"]).name)
    if p1 == p2 and n1 is not None and n2 is not None:
        d = abs(n1 - n2)
        sim_name = max(0, 1 - d / 30)
    else:
        sim_name = 0.0

    # CLIP similarity (if available)
    clip_a = info_a.get('clip_features')
    clip_b = info_b.get('clip_features')
    if clip_a is not None and clip_b is not None:
        sim_clip = float(np.dot(clip_a, clip_b))
        sim_clip = max(0.0, min(1.0, sim_clip))
    else:
        sim_clip = 0.0

    # DINOv2 similarity (if available)
    dino_a = info_a.get('dinov2_features')
    dino_b = info_b.get('dinov2_features')
    if dino_a is not None and dino_b is not None:
        sim_dino = float(np.dot(dino_a, dino_b))
        sim_dino = max(0.0, min(1.0, sim_dino))
    else:
        sim_dino = 0.0

    # Weighted fusion (adjust weights if models available)
    has_clip = clip_a is not None and clip_b is not None
    has_dino = dino_a is not None and dino_b is not None

    if has_clip and has_dino:
        sim = (
            0.20 * sim_hash
            + 0.10 * sim_color
            + 0.15 * sim_time
            + 0.08 * sim_name
            + 0.20 * sim_clip
            + 0.20 * sim_dino
        )
    elif has_clip:
        sim = (
            0.25 * sim_hash
            + 0.12 * sim_color
            + 0.18 * sim_time
            + 0.08 * sim_name
            + 0.27 * sim_clip
        )
    elif has_dino:
        sim = (
            0.25 * sim_hash
            + 0.12 * sim_color
            + 0.18 * sim_time
            + 0.08 * sim_name
            + 0.27 * sim_dino
        )
    else:
        sim = (
            0.35 * sim_hash
            + 0.20 * sim_color
            + 0.25 * sim_time
            + 0.20 * sim_name
        )

    return max(0.0, min(1.0, sim))


# ---------------------------------------------------------------------------
# 8. Complete-linkage clustering
# ---------------------------------------------------------------------------

def complete_linkage_cluster(
    members: list[int],
    dist_fn,
    threshold: float,
    forced_groups: list[set[int]] | None = None,
) -> list[list[int]]:
    """Complete-linkage clustering with optional forced merges."""
    if not members:
        return []
    clusters: dict[int, set[int]] = {i: {i} for i in members}

    if forced_groups:
        for grp in forced_groups:
            grp_list = sorted(grp & set(members))
            if len(grp_list) < 2:
                continue
            anchor = grp_list[0]
            for j in grp_list[1:]:
                if j in clusters:
                    clusters[anchor].update(clusters.pop(j))

    cache: dict[tuple[int, int], float] = {}

    def cluster_distance(ca: int, cb: int) -> float:
        key = (min(ca, cb), max(ca, cb))
        if key in cache:
            return cache[key]
        max_d = 0.0
        for i in clusters[ca]:
            for j in clusters[cb]:
                d = dist_fn(i, j)
                if d > max_d:
                    max_d = d
                    if max_d > threshold:
                        cache[key] = max_d
                        return max_d
        cache[key] = max_d
        return max_d

    while True:
        ids = list(clusters.keys())
        if len(ids) < 2:
            break
        best_pair = None
        best_d = float("inf")
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                d = cluster_distance(ids[i], ids[j])
                if d < best_d:
                    best_d = d
                    best_pair = (ids[i], ids[j])
        if best_pair is None or best_d > threshold:
            break
        a, b = best_pair
        clusters[a].update(clusters.pop(b))
        for k in list(cache.keys()):
            if a in k or b in k:
                del cache[k]

    return [sorted(c) for c in clusters.values()]


# ---------------------------------------------------------------------------
# 9. Split oversized groups
# ---------------------------------------------------------------------------

MAX_GROUP_SIZE = 25


def split_oversized(
    groups: list[list[int]], file_infos: list[dict]
) -> list[list[int]]:
    """Recursively split groups larger than MAX_GROUP_SIZE at the largest time gap."""
    out: list[list[int]] = []
    stack = list(groups)
    while stack:
        g = stack.pop()
        if len(g) <= MAX_GROUP_SIZE:
            out.append(g)
            continue
        timed = sorted([(file_infos[i].get("timestamp") or 0, i) for i in g])
        best_gap, best_k = -1.0, len(timed) // 2
        for k in range(1, len(timed)):
            gap = timed[k][0] - timed[k - 1][0]
            if gap > best_gap:
                best_gap = gap
                best_k = k
        stack.append([i for _, i in timed[:best_k]])
        stack.append([i for _, i in timed[best_k:]])
    return out


# ---------------------------------------------------------------------------
# 10. Main grouping function
# ---------------------------------------------------------------------------

def process_single_photo(img_path: str, photo_id: str) -> dict:
    """Process a single photo: extract quality info AND grouping features.
    Returns dict with quality info and features for grouping."""
    result = {
        'photo_id': photo_id,
        'path': img_path,
        'quality': None,
        'hashes': {},
        'color_hist': None,
        'clip_features': None,
        'dinov2_features': None,
        'timestamp': None,
        'face_embeddings': [],
    }

    try:
        img = cv2.imread(img_path)
        if img is None:
            return result

        from photopicker.backend.detector import detect_quality_with_face
        result['quality'] = detect_quality_with_face(img, img_path)

        pil_img = Image.open(img_path).convert('RGB')
        pil_img.thumbnail((512, 512), Image.Resampling.LANCZOS)
        result['hashes'] = {
            'phash': str(imagehash.phash(pil_img, hash_size=8)),
            'dhash': str(imagehash.dhash(pil_img, hash_size=8)),
            'whash': str(imagehash.whash(pil_img, hash_size=8)),
            'ahash': str(imagehash.average_hash(pil_img, hash_size=8)),
        }

        result['color_hist'] = compute_color_hist(img_path)

        try:
            exif = pil_img._getexif() or {}
            dt_str = exif.get(36867) or exif.get(306)
            if dt_str:
                from datetime import datetime
                dt = datetime.strptime(str(dt_str).strip(), "%Y:%m:%d %H:%M:%S")
                result['timestamp'] = dt.timestamp()
        except Exception:
            pass

        from photopicker.backend.vision import extract_clip_features, extract_dinov2_features, detect_faces
        result['clip_features'] = extract_clip_features(img_path)
        result['dinov2_features'] = extract_dinov2_features(img_path)

        faces = detect_faces(img_path)
        if faces:
            result['face_embeddings'] = [f['embedding'].tolist() if hasattr(f['embedding'], 'tolist') else list(f['embedding']) for f in faces]

    except Exception:
        pass

    return result


def group_photos(
    photo_paths: dict[str, str],
    timestamps: dict[str, float] | None = None,
    threshold: float = 0.50,
    precomputed_infos: list[dict] | None = None,
) -> dict[str, list[str]]:
    """Group photos by multi-signal similarity.

    Returns: ``{group_id: [photo_ids]}``

    If ``precomputed_infos`` is provided, uses those instead of re-extracting features.
    """
    timestamps = timestamps or {}

    if precomputed_infos is not None:
        file_infos = []
        for info in precomputed_infos:
            fi: dict = {
                "id": info["photo_id"],
                "path": info["path"],
                "timestamp": info.get("timestamp"),
                "phash": info["hashes"].get("phash"),
                "dhash": info["hashes"].get("dhash"),
                "whash": info["hashes"].get("whash"),
                "ahash": info["hashes"].get("ahash"),
                "color_hist": info.get("color_hist"),
                "clip_features": info.get("clip_features"),
                "dinov2_features": info.get("dinov2_features"),
            }
            file_infos.append(fi)
        photo_ids = [info["photo_id"] for info in precomputed_infos]
    else:
        file_infos = []
        photo_ids = list(photo_paths.keys())
        for pid in photo_ids:
            path = photo_paths[pid]
            info: dict = {
                "id": pid,
                "path": path,
                "timestamp": timestamps.get(pid),
            }
            hashes = compute_hashes(path)
            info.update(hashes)
            info["color_hist"] = compute_color_hist(path)
            file_infos.append(info)

        try:
            from photopicker.backend.vision import extract_clip_features, extract_dinov2_features
            for info in file_infos:
                info['clip_features'] = extract_clip_features(info['path'])
                info['dinov2_features'] = extract_dinov2_features(info['path'])
        except Exception:
            pass

    n = len(file_infos)
    if n == 0:
        return {}
    if n == 1:
        return {"scene_0": [photo_ids[0]]}

    # Step 1: burst detection
    bursts = detect_bursts(file_infos)

    # Step 2: time hard break
    segments = split_by_time(file_infos)

    # Step 3: distance function with cache
    pair_cache: dict[tuple[int, int], float] = {}

    def dist(i: int, j: int) -> float:
        if i == j:
            return 0.0
        key = (min(i, j), max(i, j))
        if key in pair_cache:
            return pair_cache[key]
        s = pair_similarity(file_infos[i], file_infos[j])
        d = 1.0 - s
        pair_cache[key] = d
        return d

    # Step 4: segment-wise clustering
    all_groups: list[list[int]] = []
    for seg in segments:
        seg_set = set(seg)
        local_forced = [g & seg_set for g in bursts if len(g & seg_set) >= 2]
        sub_groups = complete_linkage_cluster(
            seg, dist, threshold=threshold, forced_groups=local_forced
        )
        all_groups.extend(sub_groups)

    # Step 5: split oversized
    all_groups = split_oversized(all_groups, file_infos)

    # Step 6: sort within groups by time
    for g in all_groups:
        g.sort(key=lambda i: file_infos[i].get("timestamp") or 0)

    # Step 7: build result
    result: dict[str, list[str]] = {}
    for gi, group in enumerate(all_groups):
        group_id = f"scene_{gi}"
        result[group_id] = [file_infos[i]["id"] for i in group]

    return result


# ---------------------------------------------------------------------------
# Backward-compatible aliases
# ---------------------------------------------------------------------------

def compute_phash(img_path: str, hash_size: int = 16) -> np.ndarray:
    """Compute perceptual hash of an image (legacy API)."""
    try:
        img = cv2.imread(img_path)
        if img is None:
            return np.zeros(hash_size * hash_size, dtype=np.float32)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(
            gray, (hash_size * 4, hash_size * 4), interpolation=cv2.INTER_AREA
        )
        resized = np.float32(resized)
        dct = cv2.dct(resized)
        dct_low = dct[:hash_size, :hash_size]
        median = np.median(dct_low)
        hash_vec = (dct_low > median).flatten().astype(np.float32)
        return hash_vec
    except Exception:
        return np.zeros(hash_size * hash_size, dtype=np.float32)


def extract_phash_features(photo_paths: dict[str, str]) -> dict[str, np.ndarray]:
    """Extract pHash features for all photos (legacy API, uses compute_hashes internally)."""
    features = {}
    for photo_id, path in photo_paths.items():
        features[photo_id] = compute_phash(path)
    return features


def compute_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


def group_by_similarity(
    features: dict[str, np.ndarray], threshold: float = 0.8
) -> dict[str, list[str]]:
    """Legacy grouping API. Builds simple cosine-similarity groups."""
    if len(features) == 0:
        return {}
    ids = list(features.keys())
    vectors = np.array([features[k] for k in ids])
    similarity_matrix = np.dot(vectors, vectors.T)
    distance_matrix = 1 - similarity_matrix
    np.fill_diagonal(distance_matrix, 0)
    distance_matrix = np.clip(distance_matrix, 0, None)
    from sklearn.cluster import AgglomerativeClustering

    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=1 - threshold,
        metric="precomputed",
        linkage="average",
    )
    labels = clustering.fit_predict(distance_matrix)
    groups: dict[str, list[str]] = {}
    for photo_id, label in zip(ids, labels):
        group_key = f"scene_{label}"
        if group_key not in groups:
            groups[group_key] = []
        groups[group_key].append(photo_id)
    return groups
