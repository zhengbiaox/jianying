import os
import shutil


def export_photos(photo_paths: list[str], raw_paths: dict[str, str],
                  output_dir: str, folder_name: str) -> dict:
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
    return {"copied": copied, "skipped": skipped, "output_dir": dest_dir}
