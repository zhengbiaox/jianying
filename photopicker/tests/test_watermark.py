import tempfile
import os
import numpy as np
from PIL import Image
from photopicker.backend.watermark import read_exif, add_watermark, batch_watermark

def test_read_exif_no_exif():
    with tempfile.TemporaryDirectory() as tmpdir:
        img = Image.new("RGB", (100, 100))
        path = os.path.join(tmpdir, "test.jpg")
        img.save(path)
        exif = read_exif(path)
        assert isinstance(exif, dict)

def test_add_watermark():
    with tempfile.TemporaryDirectory() as tmpdir:
        img = Image.new("RGB", (800, 600))
        src = os.path.join(tmpdir, "test.jpg")
        img.save(src)
        dst = os.path.join(tmpdir, "out.jpg")
        result = add_watermark(src, dst)
        assert os.path.exists(result)
        out = Image.open(result)
        assert out.size[1] == 600 + max(40, 600 // 20)

def test_batch_watermark():
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(3):
            Image.new("RGB", (100, 100)).save(os.path.join(tmpdir, f"{i}.jpg"))
        paths = [os.path.join(tmpdir, f"{i}.jpg") for i in range(3)]
        out_dir = os.path.join(tmpdir, "output")
        result = batch_watermark(paths, out_dir)
        assert result["ok"] == 3
        assert result["failed"] == 0
