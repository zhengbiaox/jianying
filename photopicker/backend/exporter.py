import os
import shutil
from pathlib import Path


def _copy_xmp_companion(src_path: str, dst_dir: str, mode: str = "copy") -> bool:
    src = Path(src_path)
    xmp_path = src.with_suffix(".xmp")
    if xmp_path.exists():
        dst = os.path.join(dst_dir, xmp_path.name)
        if mode == "move":
            shutil.move(str(xmp_path), dst)
        else:
            shutil.copy2(str(xmp_path), dst)
        return True
    return False


def export_photos(photo_paths: list[str], raw_paths: dict[str, str],
                  output_dir: str, folder_name: str,
                  xmp_paths: dict[str, str | None] | None = None) -> dict:
    dest_dir = os.path.join(output_dir, folder_name)
    os.makedirs(dest_dir, exist_ok=True)
    copied = 0
    skipped = 0
    for photo_path in photo_paths:
        if not os.path.exists(photo_path):
            skipped += 1
            continue
        dest_path = os.path.join(dest_dir, os.path.basename(photo_path))
        shutil.copy2(photo_path, dest_path)
        copied += 1
        raw_path = raw_paths.get(photo_path)
        if raw_path and os.path.exists(raw_path):
            raw_dest = os.path.join(dest_dir, os.path.basename(raw_path))
            shutil.copy2(raw_path, raw_dest)
        if xmp_paths:
            xmp_path = xmp_paths.get(photo_path)
            if xmp_path and os.path.exists(xmp_path):
                xmp_dest = os.path.join(dest_dir, os.path.basename(xmp_path))
                shutil.copy2(xmp_path, xmp_dest)
        else:
            _copy_xmp_companion(photo_path, dest_dir)
    return {"copied": copied, "skipped": skipped, "output_dir": dest_dir}


def export_winners_losers(folder: str, winners: list[str], losers: list[str],
                          mode: str = "copy",
                          raw_paths: dict[str, str | None] | None = None) -> dict:
    winners_dir = os.path.join(folder, "入选")
    losers_dir = os.path.join(folder, "未入选")
    os.makedirs(winners_dir, exist_ok=True)
    os.makedirs(losers_dir, exist_ok=True)
    moved = 0
    for src in winners:
        if not os.path.exists(src):
            continue
        dst = os.path.join(winners_dir, os.path.basename(src))
        if mode == "move":
            shutil.move(src, dst)
        else:
            shutil.copy2(src, dst)
        _copy_xmp_companion(src, winners_dir, mode)
        # Copy/move RAW file if exists
        if raw_paths:
            raw = raw_paths.get(src)
            if raw and os.path.exists(raw):
                raw_dst = os.path.join(winners_dir, os.path.basename(raw))
                if mode == "move":
                    shutil.move(raw, raw_dst)
                else:
                    shutil.copy2(raw, raw_dst)
        moved += 1
    for src in losers:
        if not os.path.exists(src):
            continue
        dst = os.path.join(losers_dir, os.path.basename(src))
        if mode == "move":
            shutil.move(src, dst)
        else:
            shutil.copy2(src, dst)
        _copy_xmp_companion(src, losers_dir, mode)
        # Copy/move RAW file if exists
        if raw_paths:
            raw = raw_paths.get(src)
            if raw and os.path.exists(raw):
                raw_dst = os.path.join(losers_dir, os.path.basename(raw))
                if mode == "move":
                    shutil.move(raw, raw_dst)
                else:
                    shutil.copy2(raw, raw_dst)
        moved += 1
    return {
        "入选": len(winners),
        "未入选": len(losers),
        "mode": mode,
        "winners_dir": winners_dir,
        "losers_dir": losers_dir,
    }
