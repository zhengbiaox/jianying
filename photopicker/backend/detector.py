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
