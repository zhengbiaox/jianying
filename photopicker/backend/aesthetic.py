import cv2
import numpy as np


def compute_aesthetic_score(img_path: str) -> dict:
    """Compute aesthetic score based on image statistics.
    Returns score 0-100 and breakdown."""
    img = cv2.imread(img_path)
    if img is None:
        return {"score": 50, "breakdown": {}}

    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 1. Contrast score (0-100)
    contrast = float(gray.std())
    contrast_score = min(100, contrast / 0.6)

    # 2. Saturation score (0-100)
    saturation = float(hsv[:, :, 1].mean())
    sat_score = min(100, saturation / 1.5)

    # 3. Sharpness score (0-100)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F).var()
    sharp_score = min(100, laplacian / 5.0)

    # 4. Composition score - rule of thirds (0-100)
    # Detect salient region and check if it's near thirds lines
    edges = cv2.Canny(gray, 50, 150)
    thirds_x = [w // 3, 2 * w // 3]
    thirds_y = [h // 3, 2 * h // 3]
    # Weight edges near thirds lines higher
    mask = np.zeros_like(edges)
    for tx in thirds_x:
        mask[:, max(0, tx-20):min(w, tx+20)] = 1
    for ty in thirds_y:
        mask[max(0, ty-20):min(h, ty+20), :] = 1
    edge_density = float(edges[mask > 0].mean()) if mask.sum() > 0 else 0
    comp_score = min(100, edge_density * 2)

    # 5. Brightness balance (0-100) - penalize too dark or too bright
    mean_brightness = float(gray.mean())
    bright_score = 100 - abs(mean_brightness - 128) / 1.28

    # Weighted composite
    score = int(
        contrast_score * 0.2 +
        sat_score * 0.2 +
        sharp_score * 0.3 +
        comp_score * 0.15 +
        bright_score * 0.15
    )
    score = max(0, min(100, score))

    return {
        "score": score,
        "breakdown": {
            "contrast": round(contrast_score),
            "saturation": round(sat_score),
            "sharpness": round(sharp_score),
            "composition": round(comp_score),
            "brightness": round(bright_score),
        }
    }


def batch_aesthetic(paths: list[str]) -> dict[str, dict]:
    """Score multiple images."""
    results = {}
    for path in paths:
        results[path] = compute_aesthetic_score(path)
    return results
