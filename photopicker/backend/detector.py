import cv2
import numpy as np
from photopicker.backend.models import PhotoGrade


def tenengrad(arr: np.ndarray) -> float:
    """Sobel gradient squared sum. More robust to noise than Laplacian."""
    if arr.shape[0] < 3 or arr.shape[1] < 3:
        return 0.0
    gx = arr[1:-1, 2:] - arr[1:-1, :-2]
    gy = arr[2:, 1:-1] - arr[:-2, 1:-1]
    return float((gx * gx + gy * gy).mean())


def fft_high_freq_ratio(arr: np.ndarray) -> tuple[float, float]:
    """Returns (high_freq_ratio, anisotropy). Higher ratio = sharper."""
    if arr.shape[0] < 16 or arr.shape[1] < 16:
        return 0.0, 0.0
    h, w = arr.shape
    s = min(h, w)
    y0, x0 = (h - s) // 2, (w - s) // 2
    crop = arr[y0:y0+s, x0:x0+s]
    if s > 256:
        crop = cv2.resize(crop.astype(np.float32), (256, 256), interpolation=cv2.INTER_AREA)
        s = 256
    crop = crop - crop.mean()
    win = np.outer(np.hanning(s), np.hanning(s)).astype(np.float32)
    spec = np.fft.fftshift(np.fft.fft2(crop * win))
    mag = np.abs(spec).astype(np.float32)
    mag[s//2, s//2] = 0.0
    yy, xx = np.mgrid[:s, :s].astype(np.float32)
    r = np.sqrt((yy - s/2)**2 + (xx - s/2)**2)
    r_max = s / 2.0
    high_mask = r > 0.30 * r_max
    total = float(mag.sum() + 1e-8)
    high_ratio = float(mag[high_mask].sum()) / total
    band = (r > 0.10 * r_max) & (r < 0.50 * r_max)
    if band.sum() < 50:
        return high_ratio, 0.0
    theta = np.arctan2(yy - s/2, xx - s/2)
    theta = np.where(theta < 0, theta + np.pi, theta)
    n_bins = 12
    bin_idx = np.minimum(n_bins - 1, (theta / np.pi * n_bins).astype(np.int32))
    sums = np.bincount(bin_idx[band], weights=mag[band], minlength=n_bins)
    counts = np.bincount(bin_idx[band], minlength=n_bins).astype(np.float32) + 1e-6
    avg = sums / counts
    aniso = float((avg.max() - avg.min()) / (avg.max() + 1e-8))
    return high_ratio, aniso


def edge_width_marziliano(arr: np.ndarray) -> float | None:
    """Measure edge width along horizontal direction. Larger = blurrier."""
    if arr.shape[0] < 16 or arr.shape[1] < 16:
        return None
    a = arr.astype(np.float32)
    a_u8 = np.clip(a, 0, 255).astype(np.uint8)
    edges = cv2.Canny(a_u8, 50, 150)
    ys, xs = np.where(edges > 0)
    if len(xs) < 50:
        return None
    if len(xs) > 800:
        idx = np.random.default_rng(0).choice(len(xs), 800, replace=False)
        ys, xs = ys[idx], xs[idx]
    widths = []
    h, w = a.shape
    for y, x in zip(ys, xs):
        if x < 3 or x > w - 4:
            continue
        left = x
        for k in range(1, 12):
            if x - k < 1: break
            if a[y, x-k] >= a[y, x-k+1]: left = x - k
            else: break
        right = x
        for k in range(1, 12):
            if x + k > w - 2: break
            if a[y, x+k] <= a[y, x+k-1]: right = x + k
            else: break
        wpx = right - left
        if 1 <= wpx <= 25:
            widths.append(wpx)
    if len(widths) < 30:
        return None
    return float(np.mean(widths))


def nine_grid_exposure(arr: np.ndarray) -> dict:
    """9-grid exposure analysis. Returns worst cell metrics."""
    h, w = arr.shape
    if h < 9 or w < 9:
        return {"worst_dark": 0, "worst_bright": 0, "worst_clip_dark": 0, "worst_clip_bright": 0}
    ys = [0, h//3, 2*h//3, h]
    xs = [0, w//3, 2*w//3, w]
    worst_dark, worst_bright = 255.0, 0.0
    worst_clip_dark, worst_clip_bright = 0.0, 0.0
    for i in range(3):
        for j in range(3):
            block = arr[ys[i]:ys[i+1], xs[j]:xs[j+1]]
            if block.size == 0: continue
            m = float(block.mean())
            worst_dark = min(worst_dark, m)
            worst_bright = max(worst_bright, m)
            worst_clip_dark = max(worst_clip_dark, float((block <= 8).mean()))
            worst_clip_bright = max(worst_clip_bright, float((block >= 247).mean()))
    return {"worst_dark": worst_dark, "worst_bright": worst_bright,
            "worst_clip_dark": worst_clip_dark, "worst_clip_bright": worst_clip_bright}


def horizon_tilt_degrees(arr: np.ndarray) -> float | None:
    """Hough line detection for horizon tilt. Returns degrees."""
    if arr.shape[0] < 64 or arr.shape[1] < 64:
        return None
    a_u8 = np.clip(arr, 0, 255).astype(np.uint8)
    edges = cv2.Canny(a_u8, 50, 150)
    min_len = max(40, int(min(arr.shape) * 0.35))
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=80, minLineLength=min_len, maxLineGap=10)
    if lines is None or len(lines) == 0:
        return None
    angles, weights = [], []
    for ln in lines[:200]:
        x1, y1, x2, y2 = ln[0]
        length = np.hypot(x2-x1, y2-y1)
        if length < min_len: continue
        theta = np.degrees(np.arctan2(y2-y1, x2-x1))
        if theta > 90: theta -= 180
        elif theta < -90: theta += 180
        dev = min(abs(theta), abs(90 - abs(theta)))
        angles.append(dev)
        weights.append(length)
    if not angles:
        return None
    arr_a, arr_w = np.array(angles), np.array(weights)
    n_take = max(1, len(arr_a) // 3)
    idx = np.argsort(arr_a)[:n_take]
    return float(np.average(arr_a[idx], weights=arr_w[idx]))


def saliency_map(arr: np.ndarray) -> np.ndarray | None:
    """Spectral residual saliency map. Returns float32 0-1."""
    h, w = arr.shape[:2]
    if h < 8 or w < 8:
        return None
    small = cv2.resize(arr, (64, 64), interpolation=cv2.INTER_AREA).astype(np.float32)
    f = np.fft.fft2(small)
    log_amp = np.log(np.abs(f) + 1e-8)
    kernel = np.ones((3, 3), np.float32) / 9.0
    smooth = cv2.filter2D(log_amp, -1, kernel)
    residual = log_amp - smooth
    phase = np.angle(f)
    recon = np.fft.ifft2(np.exp(residual + 1j * phase))
    smap = np.abs(recon) ** 2
    smap = cv2.GaussianBlur(smap.astype(np.float32), (9, 9), 2.5)
    smap = cv2.resize(smap, (w, h), interpolation=cv2.INTER_LINEAR)
    mn, mx = smap.min(), smap.max()
    if mx - mn < 1e-8:
        return None
    smap = (smap - mn) / (mx - mn)
    if smap.std() < 0.01:
        return None
    return smap


def salient_sharpness(arr: np.ndarray, smap: np.ndarray | None) -> float | None:
    """Laplacian variance in salient region (top 20% saliency)."""
    if smap is None or arr.shape[0] < 16 or arr.shape[1] < 16:
        return None
    sm = smap.astype(np.float32)
    if sm.std() < 0.01:
        return None
    if sm.shape != arr.shape:
        sm = cv2.resize(sm, (arr.shape[1], arr.shape[0]), interpolation=cv2.INTER_LINEAR)
    thr = np.quantile(sm, 0.80)
    mask = sm >= thr
    if mask.sum() < 100:
        return None
    center = arr[1:-1, 1:-1].astype(np.float32) * 4
    lap = center - arr[:-2, 1:-1].astype(np.float32) - arr[2:, 1:-1].astype(np.float32) \
          - arr[1:-1, :-2].astype(np.float32) - arr[1:-1, 2:].astype(np.float32)
    m = mask[1:-1, 1:-1]
    sel = lap[m]
    if sel.size < 100:
        return None
    return float(sel.var())


def detect_quality_enhanced(img: np.ndarray) -> dict:
    """Enhanced quality detection with multi-metric fusion."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    arr = gray.astype(np.float32)

    # Multi-sharpness
    lap = detect_blur(img)
    teng = tenengrad(arr)
    high_ratio, aniso = fft_high_freq_ratio(arr)
    ew = edge_width_marziliano(arr)

    # Normalize to 0-1
    lap_n = min(1.0, np.log1p(max(0, lap)) / np.log1p(900))
    teng_n = min(1.0, np.log1p(max(0, teng)) / np.log1p(2000))
    high_n = min(1.0, max(0, high_ratio) / 0.40)
    ew_n = max(0, min(1.0, (10 - ew) / 7)) if ew is not None else None

    parts = [lap_n, teng_n, high_n]
    if ew_n is not None:
        parts.append(ew_n)
    blur_combined = float(np.mean(parts))

    # Saliency
    smap = saliency_map(arr)
    sal_sharp = salient_sharpness(arr, smap)

    # Exposure
    exposure = detect_exposure(img)
    nine = nine_grid_exposure(arr)

    # Horizon
    horizon = horizon_tilt_degrees(arr)

    # Build reasons
    reasons = []
    score = 100

    if sal_sharp is not None and sal_sharp < 550:
        reasons.append("very_blurry")
        score -= 25
    elif sal_sharp is not None and sal_sharp < 750:
        reasons.append("subject_blurry")
        score -= 12
    elif blur_combined < 0.28:
        reasons.append("very_blurry")
        score -= 25

    if aniso > 0.62 and ew is not None and ew > 5.0:
        reasons.append("motion_blur")
        score -= 20

    if exposure["overexposed"] or nine["worst_clip_bright"] >= 0.82:
        reasons.append("overexposed")
        score -= 20
    if exposure["underexposed"] or nine["worst_clip_dark"] >= 0.82:
        reasons.append("underexposed")
        score -= 20

    if horizon is not None and horizon > 15:
        reasons.append("horizon_severe")
        score -= 22
    elif horizon is not None and horizon > 4.5:
        reasons.append("horizon_tilt")
        score -= 12

    score = max(0, min(100, score))

    return {
        "score": score,
        "grade": score_to_grade(score).value,
        "reasons": reasons,
        "sharpness": round(lap, 1),
        "blur_combined": round(blur_combined, 3),
        "salient_sharpness": round(sal_sharp, 1) if sal_sharp is not None else None,
        "horizon_tilt": round(horizon, 1) if horizon is not None else None,
    }

def detect_blur(img: np.ndarray) -> float:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    return float(laplacian_var)

def detect_exposure(img: np.ndarray, overexpose_threshold: float = 0.1,
                    underexpose_threshold: float = 0.1) -> dict:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist = hist / hist.sum()
    overexposed = float(hist[240:].sum()) > overexpose_threshold
    underexposed = float(hist[:15].sum()) > underexpose_threshold
    return {"overexposed": overexposed, "underexposed": underexposed}

def detect_shake(img: np.ndarray) -> bool:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    gradient_mag = np.sqrt(sobelx ** 2 + sobely ** 2)
    return float(gradient_mag.var()) < 100

def calculate_score(is_closed_eye: bool, sharpness: float,
                    exposure_ok: bool, is_shake: bool) -> int:
    score = 100
    if is_closed_eye:
        score -= 55
    if not exposure_ok:
        score -= 20
    if sharpness < 50:
        score -= 25
    if is_shake:
        score -= 15
    return max(0, min(100, score))

def score_to_grade(score: int, threshold: int = 60) -> PhotoGrade:
    if score >= threshold + 20:
        return PhotoGrade.GREEN
    elif score >= threshold:
        return PhotoGrade.YELLOW
    else:
        return PhotoGrade.RED

def detect_quality_with_reasons(img: np.ndarray) -> dict:
    enhanced = detect_quality_enhanced(img)
    reasons = list(enhanced["reasons"])
    score = enhanced["score"]
    sharpness = enhanced["sharpness"]

    # Legacy shake detection for backward compatibility
    shake = detect_shake(img)
    if shake and "shake" not in reasons:
        reasons.append("shake")
        score -= 15

    # Legacy blurry label for backward compatibility
    if enhanced["blur_combined"] < 0.28 and "blurry" not in reasons:
        reasons.append("blurry")

    score = max(0, min(100, score))
    grade = score_to_grade(score)
    return {
        "score": score,
        "grade": grade.value,
        "reasons": reasons,
        "sharpness": sharpness,
    }


def detect_faces(img: np.ndarray) -> list[dict]:
    """Detect faces and eye state using MediaPipe."""
    try:
        import mediapipe as mp
        mp_face_mesh = mp.solutions.face_mesh
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        with mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=5,
            refine_landmarks=True,
            min_detection_confidence=0.5
        ) as face_mesh:
            results = face_mesh.process(rgb)
            if not results.multi_face_landmarks:
                return []
            faces = []
            for face_landmarks in results.multi_face_landmarks:
                left_eye = [face_landmarks.landmark[i] for i in [33, 160, 158, 133, 153, 144]]
                right_eye = [face_landmarks.landmark[i] for i in [362, 385, 387, 263, 373, 380]]

                def eye_ratio(eye):
                    v1 = ((eye[1].x - eye[5].x)**2 + (eye[1].y - eye[5].y)**2) ** 0.5
                    v2 = ((eye[2].x - eye[4].x)**2 + (eye[2].y - eye[4].y)**2) ** 0.5
                    h = ((eye[0].x - eye[3].x)**2 + (eye[0].y - eye[3].y)**2) ** 0.5
                    return (v1 + v2) / (2.0 * h) if h > 0 else 0

                left_ratio = eye_ratio(left_eye)
                right_ratio = eye_ratio(right_eye)
                avg_ratio = (left_ratio + right_ratio) / 2
                eyes_closed = avg_ratio < 0.2

                h, w = img.shape[:2]
                xs = [lm.x * w for lm in face_landmarks.landmark]
                ys = [lm.y * h for lm in face_landmarks.landmark]
                bbox = {
                    "x": int(min(xs)), "y": int(min(ys)),
                    "w": int(max(xs) - min(xs)), "h": int(max(ys) - min(ys))
                }

                faces.append({
                    "bbox": bbox,
                    "eyes_closed": eyes_closed,
                    "eye_ratio": round(avg_ratio, 3),
                })
            return faces
    except (ImportError, AttributeError):
        return []


def detect_quality_with_face(img: np.ndarray) -> dict:
    """Quality detection including face analysis with enhanced metrics."""
    result = detect_quality_with_reasons(img)
    enhanced = detect_quality_enhanced(img)
    result["blur_combined"] = enhanced["blur_combined"]
    result["salient_sharpness"] = enhanced["salient_sharpness"]
    result["horizon_tilt"] = enhanced["horizon_tilt"]
    faces = detect_faces(img)
    result["faces"] = faces
    result["face_count"] = len(faces)

    if faces:
        closed_eyes = any(f["eyes_closed"] for f in faces)
        if closed_eyes:
            if "closed_eyes" not in result["reasons"]:
                result["reasons"].append("closed_eyes")
            result["score"] = max(0, result["score"] - 30)
            result["grade"] = score_to_grade(result["score"]).value

    return result
