import cv2
import numpy as np
from photopicker.backend.models import PhotoGrade

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
    reasons = []
    score = 100
    sharpness = detect_blur(img)
    exposure = detect_exposure(img)
    shake = detect_shake(img)
    if sharpness < 50:
        reasons.append("blurry")
        score -= 25
    if exposure["overexposed"]:
        reasons.append("overexposed")
        score -= 20
    if exposure["underexposed"]:
        reasons.append("underexposed")
        score -= 20
    if shake:
        reasons.append("shake")
        score -= 15
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
    """Quality detection including face analysis."""
    result = detect_quality_with_reasons(img)
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
