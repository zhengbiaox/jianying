import os
import tempfile
from photopicker.backend.scanner import scan_folder, pair_jpg_raw


def test_scan_folder_finds_images():
    with tempfile.TemporaryDirectory() as tmpdir:
        for name in ["a.jpg", "b.png", "c.txt", "d.JPG"]:
            open(os.path.join(tmpdir, name), "w").close()
        results = scan_folder(tmpdir)
        assert len(results) == 3


def test_pair_jpg_raw_by_name():
    with tempfile.TemporaryDirectory() as tmpdir:
        open(os.path.join(tmpdir, "img001.jpg"), "w").close()
        open(os.path.join(tmpdir, "img001.ARW"), "w").close()
        open(os.path.join(tmpdir, "img002.jpg"), "w").close()
        pairs = pair_jpg_raw(tmpdir)
        assert "img001.jpg" in pairs
        assert pairs["img001.jpg"] == "img001.ARW"
        assert "img002.jpg" in pairs
        assert pairs["img002.jpg"] is None


def test_scan_recursive():
    with tempfile.TemporaryDirectory() as tmpdir:
        sub = os.path.join(tmpdir, "subdir")
        os.makedirs(sub)
        open(os.path.join(tmpdir, "a.jpg"), "w").close()
        open(os.path.join(sub, "b.jpg"), "w").close()
        results = scan_folder(tmpdir, recursive=True)
        assert len(results) == 2
