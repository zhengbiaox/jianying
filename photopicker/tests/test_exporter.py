import os
import tempfile
from photopicker.backend.exporter import export_photos, export_winners_losers


def test_export_copies_files():
    with tempfile.TemporaryDirectory() as srcdir:
        with tempfile.TemporaryDirectory() as dstdir:
            for name in ["a.jpg", "b.jpg"]:
                open(os.path.join(srcdir, name), "w").close()
            export_photos(
                photo_paths=[os.path.join(srcdir, "a.jpg")],
                raw_paths={},
                output_dir=dstdir,
                folder_name="selected"
            )
            assert os.path.exists(os.path.join(dstdir, "selected", "a.jpg"))
            assert not os.path.exists(os.path.join(dstdir, "selected", "b.jpg"))


def test_export_copies_raw():
    with tempfile.TemporaryDirectory() as srcdir:
        with tempfile.TemporaryDirectory() as dstdir:
            open(os.path.join(srcdir, "a.jpg"), "w").close()
            open(os.path.join(srcdir, "a.ARW"), "w").close()
            export_photos(
                photo_paths=[os.path.join(srcdir, "a.jpg")],
                raw_paths={os.path.join(srcdir, "a.jpg"): os.path.join(srcdir, "a.ARW")},
                output_dir=dstdir,
                folder_name="selected"
            )
            assert os.path.exists(os.path.join(dstdir, "selected", "a.ARW"))


def test_export_winners_losers_copy():
    with tempfile.TemporaryDirectory() as srcdir:
        open(os.path.join(srcdir, "a.jpg"), "w").close()
        open(os.path.join(srcdir, "b.jpg"), "w").close()
        result = export_winners_losers(
            folder=srcdir, winners=[os.path.join(srcdir, "a.jpg")],
            losers=[os.path.join(srcdir, "b.jpg")], mode="copy"
        )
        assert os.path.exists(os.path.join(srcdir, "winners", "a.jpg"))
        assert os.path.exists(os.path.join(srcdir, "losers", "b.jpg"))
        assert os.path.exists(os.path.join(srcdir, "a.jpg"))


def test_export_winners_losers_move():
    with tempfile.TemporaryDirectory() as srcdir:
        a = os.path.join(srcdir, "a.jpg")
        b = os.path.join(srcdir, "b.jpg")
        open(a, "w").close()
        open(b, "w").close()
        result = export_winners_losers(
            folder=srcdir, winners=[a], losers=[b], mode="move"
        )
        assert os.path.exists(os.path.join(srcdir, "winners", "a.jpg"))
        assert not os.path.exists(a)
