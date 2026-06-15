import os

def detect_device() -> str:
    """Auto-detect best available device."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"

def get_device(preference: str = "auto") -> str:
    """Get device based on user preference."""
    if preference == "cpu":
        return "cpu"
    if preference == "gpu":
        detected = detect_device()
        return detected if detected != "cpu" else "cpu"
    return detect_device()

def device_info() -> dict:
    """Get device information."""
    device = detect_device()
    info = {"device": device, "available": []}
    try:
        import torch
        if torch.cuda.is_available():
            info["available"].append("cuda")
            info["cuda_name"] = torch.cuda.get_device_name(0)
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            info["available"].append("mps")
        info["available"].append("cpu")
    except ImportError:
        info["available"] = ["cpu"]
    return info
