from photopicker.backend.runtime import detect_device, get_device, device_info

def test_detect_device_returns_string():
    result = detect_device()
    assert result in ("cpu", "cuda", "mps")

def test_get_device_auto():
    result = get_device("auto")
    assert result in ("cpu", "cuda", "mps")

def test_get_device_cpu():
    result = get_device("cpu")
    assert result == "cpu"

def test_device_info_has_fields():
    info = device_info()
    assert "device" in info
    assert "available" in info
    assert isinstance(info["available"], list)
