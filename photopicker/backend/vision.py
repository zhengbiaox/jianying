import os
import logging
import numpy as np

os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')

logger = logging.getLogger('photopicker')

_clip_model = None
_clip_preprocess = None
_dinov2_model = None
_face_analyzer = None
_device = 'cpu'


def get_device():
    global _device
    try:
        import torch
        if torch.cuda.is_available():
            _device = 'cuda'
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            _device = 'mps'
    except ImportError:
        pass
    return _device


def load_clip():
    global _clip_model, _clip_preprocess
    if _clip_model is not None:
        return True
    try:
        import torch
        import open_clip
        logger.info('Loading CLIP model...')
        _clip_model, _, _clip_preprocess = open_clip.create_model_and_transforms(
            'ViT-B-32', pretrained='laion2b_s34b_b79k'
        )
        _clip_model = _clip_model.to(get_device()).eval()
        logger.info('CLIP model loaded')
        return True
    except Exception as e:
        logger.warning(f'CLIP load failed: {e}')
        _clip_model = None
        return False


_dinov2_processor = None

def load_dinov2():
    global _dinov2_model, _dinov2_processor
    if _dinov2_model is not None:
        return True
    try:
        import torch
        from transformers import AutoModel, AutoImageProcessor
        logger.info('Loading DINOv2 model from HuggingFace...')
        model_name = "facebook/dinov2-base"
        _dinov2_processor = AutoImageProcessor.from_pretrained(model_name)
        _dinov2_model = AutoModel.from_pretrained(model_name)
        _dinov2_model = _dinov2_model.to(get_device()).eval()
        logger.info('DINOv2 model loaded')
        return True
    except Exception as e:
        logger.warning(f'DINOv2 load failed: {e}')
        _dinov2_model = None
        _dinov2_processor = None
        return False


_insightface_load_failed = False

def load_insightface():
    global _face_analyzer, _insightface_load_failed
    if _face_analyzer is not None:
        return True
    if _insightface_load_failed:
        return False
    try:
        from insightface.app import FaceAnalysis
        logger.info('Loading InsightFace model...')
        _face_analyzer = FaceAnalysis(
            name='buffalo_sc',
            root=os.path.expanduser('~/.insightface'),
            providers=['CPUExecutionProvider']
        )
        _face_analyzer.prepare(ctx_id=-1, det_size=(640, 640))
        logger.info('InsightFace model loaded')
        return True
    except Exception as e:
        logger.warning(f'InsightFace load failed: {e}')
        _face_analyzer = None
        _insightface_load_failed = True
        return False


def extract_clip_features(img_path: str) -> np.ndarray | None:
    if not load_clip():
        return None
    try:
        import torch
        from PIL import Image
        img = Image.open(img_path).convert('RGB')
        image = _clip_preprocess(img).unsqueeze(0).to(get_device())
        with torch.no_grad():
            feat = _clip_model.encode_image(image)
            feat = feat / feat.norm(dim=-1, keepdim=True)
        return feat.cpu().squeeze().numpy()
    except Exception:
        return None


def extract_dinov2_features(img_path: str) -> np.ndarray | None:
    if not load_dinov2():
        return None
    try:
        import torch
        from PIL import Image
        img = Image.open(img_path).convert('RGB')
        inputs = _dinov2_processor(images=img, return_tensors="pt")
        inputs = {k: v.to(get_device()) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = _dinov2_model(**inputs)
            feat = outputs.last_hidden_state[:, 0, :]
            feat = feat / feat.norm(dim=-1, keepdim=True)
        return feat.cpu().squeeze().numpy()
    except Exception:
        return None


def detect_faces(img_path: str) -> list[dict]:
    if not load_insightface():
        return []
    try:
        import cv2
        img = cv2.imread(img_path)
        if img is None:
            return []
        faces = _face_analyzer.get(img)
        results = []
        for face in faces:
            results.append({
                'bbox': face.bbox.tolist(),
                'score': float(face.det_score),
                'embedding': face.embedding,
            })
        return results
    except Exception:
        return []


def detect_closed_eyes(img_path: str) -> bool:
    if not load_insightface():
        return False
    try:
        import cv2
        img = cv2.imread(img_path)
        if img is None:
            return False
        faces = _face_analyzer.get(img)
        if not faces:
            return False
        for face in faces:
            kps = face.kps
            if kps is not None and len(kps) >= 2:
                pass
        return False
    except Exception:
        return False


def preload_models():
    """预加载所有模型，启动时调用"""
    logger.info('Preloading models...')
    device = get_device()
    logger.info(f'Using device: {device}')

    load_clip()
    load_dinov2()
    load_insightface()

    status = get_model_status()
    loaded = [k for k, v in status.items() if v is True and k != 'device']
    logger.info(f'Models loaded: {", ".join(loaded) if loaded else "none"}')
    return status


def get_model_status() -> dict:
    return {
        'clip': _clip_model is not None,
        'dinov2': _dinov2_model is not None,
        'insightface': _face_analyzer is not None,
        'device': get_device(),
    }
