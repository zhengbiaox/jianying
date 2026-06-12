from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".heic", ".heif"}
RAW_EXTENSIONS = {".arw", ".cr3", ".cr2", ".nef", ".raf", ".orf", ".rw2", ".dng", ".pef", ".srw"}
XMP_EXTENSIONS = {".xmp"}


ALL_EXTENSIONS = {ext.lower() for ext in IMAGE_EXTENSIONS | RAW_EXTENSIONS | XMP_EXTENSIONS}


def scan_folder(folder_path: str, recursive: bool = True) -> list[str]:
    results = []
    root_path = Path(folder_path)
    pattern_func = root_path.rglob if recursive else root_path.glob
    for match in pattern_func("*"):
        if match.is_file() and match.suffix.lower() in ALL_EXTENSIONS:
            results.append(str(match))
    return sorted(results)


def pair_jpg_raw(folder_path: str, recursive: bool = True) -> dict[str, dict[str, str | None]]:
    all_files = scan_folder(folder_path, recursive)
    stem_map: dict[str, dict[str, str]] = {}
    for fname in all_files:
        p = Path(fname)
        stem = p.stem.lower()
        ext = p.suffix.lower()
        if stem not in stem_map:
            stem_map[stem] = {}
        if ext in IMAGE_EXTENSIONS:
            stem_map[stem]["jpg"] = fname
        elif ext in RAW_EXTENSIONS:
            stem_map[stem]["raw"] = fname
        elif ext in XMP_EXTENSIONS:
            stem_map[stem]["xmp"] = fname
    pairs = {}
    for stem, files in stem_map.items():
        jpg_path = files.get("jpg")
        raw_path = files.get("raw")
        xmp_path = files.get("xmp")
        if jpg_path:
            pairs[jpg_path] = {"raw": raw_path, "xmp": xmp_path}
    return pairs
