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
        jpg1 = os.path.join(tmpdir, "img001.jpg")
        raw1 = os.path.join(tmpdir, "img001.ARW")
        jpg2 = os.path.join(tmpdir, "img002.jpg")
        open(jpg1, "w").close()
        open(raw1, "w").close()
        open(jpg2, "w").close()
        pairs = pair_jpg_raw(tmpdir)
        assert jpg1 in pairs
        assert pairs[jpg1]["raw"] == raw1
        assert pairs[jpg1]["xmp"] is None
        assert jpg2 in pairs
        assert pairs[jpg2]["raw"] is None


def test_scan_recursive():
    with tempfile.TemporaryDirectory() as tmpdir:
        sub = os.path.join(tmpdir, "subdir")
        os.makedirs(sub)
        open(os.path.join(tmpdir, "a.jpg"), "w").close()
        open(os.path.join(sub, "b.jpg"), "w").close()
        results = scan_folder(tmpdir, recursive=True)
        assert len(results) == 2
