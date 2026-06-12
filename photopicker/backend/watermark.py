import io
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from PIL.ExifTags import TAGS


def read_exif(img_path: str) -> dict:
    """Read EXIF data from image file."""
    try:
        img = Image.open(img_path)
        exif_data = img._getexif()
        if not exif_data:
            return {}
        result = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "Make":
                result["make"] = str(value).strip()
            elif tag == "Model":
                result["model"] = str(value).strip()
            elif tag == "FocalLength":
                result["focal_length"] = str(value)
            elif tag == "FNumber":
                result["aperture"] = f"f/{float(value)}"
            elif tag == "ExposureTime":
                if isinstance(value, tuple):
                    result["shutter"] = f"{value[0]}/{value[1]}s"
                else:
                    result["shutter"] = f"{value}s"
            elif tag == "ISOSpeedRatings":
                result["iso"] = f"ISO{value}"
            elif tag == "LensModel":
                result["lens"] = str(value).strip()
        return result
    except Exception:
        return {}


def add_watermark(img_path: str, output_path: str, style: str = "standard") -> str:
    """Add camera info watermark to image."""
    exif = read_exif(img_path)
    img = Image.open(img_path).convert("RGB")
    w, h = img.size

    bar_height = max(40, h // 20)
    new_img = Image.new("RGB", (w, h + bar_height), (255, 255, 255))
    new_img.paste(img, (0, 0))

    draw = ImageDraw.Draw(new_img)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", bar_height // 2)
    except Exception:
        font = ImageFont.load_default()

    left_text = f"{exif.get('make', '')} {exif.get('model', '')}".strip()
    right_parts = []
    for k in ["focal_length", "aperture", "shutter", "iso"]:
        if k in exif:
            right_parts.append(exif[k])
    right_text = " | ".join(right_parts)

    y = h + bar_height // 4
    draw.text((10, y), left_text, fill=(0, 0, 0), font=font)
    if right_text:
        bbox = draw.textbbox((0, 0), right_text, font=font)
        draw.text((w - bbox[2] - 10, y), right_text, fill=(0, 0, 0), font=font)

    new_img.save(output_path, "JPEG", quality=92)
    return output_path


def batch_watermark(photo_paths: list[str], output_dir: str, style: str = "standard") -> dict:
    """Batch add watermarks to photos."""
    os.makedirs(output_dir, exist_ok=True)
    ok = 0
    failed = 0
    for src in photo_paths:
        try:
            dst = os.path.join(output_dir, Path(src).stem + "_wm.jpg")
            add_watermark(src, dst, style)
            ok += 1
        except Exception:
            failed += 1
    return {"ok": ok, "failed": failed, "output_dir": output_dir}
