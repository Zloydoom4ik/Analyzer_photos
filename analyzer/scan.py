"""Find the picture files under a folder and fingerprint the new ones."""
import hashlib
import io
from concurrent.futures import ThreadPoolExecutor

import imagehash
from PIL import Image, ImageOps, UnidentifiedImageError

from . import config, db


def find_pictures(root, subfolder):
    """Yield (place, name, path) for every picture file under root/<place>/[subfolder/]."""
    for place_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        base = place_dir / subfolder if subfolder else place_dir
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix.lower() in config.IMAGE_EXTENSIONS:
                yield place_dir.name, path.relative_to(place_dir).as_posix(), path


def preview_path(sha256):
    return config.THUMBS_DIR / f"{sha256[:20]}.jpg"


def fingerprint(path):
    """Read one file: its size, sha256, perceptual hash and dimensions. Saves a small preview for the report."""
    data = path.read_bytes()
    sha256 = hashlib.sha256(data).hexdigest()
    try:
        with Image.open(io.BytesIO(data)) as picture:
            width, height = picture.size
            # For JPEG this decodes straight to a reduced size, which is many times faster on large photos.
            picture.draft("RGB", (config.THUMB_SIZE * 2, config.THUMB_SIZE * 2))
            picture = ImageOps.exif_transpose(picture).convert("RGB")
            phash = str(imagehash.phash(picture))
            picture.thumbnail((config.THUMB_SIZE, config.THUMB_SIZE))
            picture.save(preview_path(sha256), "JPEG", quality=80)
    except (UnidentifiedImageError, OSError):
        width = height = phash = None
    return {"bytes": len(data), "width": width, "height": height, "sha256": sha256, "phash": phash}


def scan(conn, root, subfolder):
    """Bring the images table in line with the folder.

    New and changed files are fingerprinted, files no longer in the folder are forgotten.
    Returns (files found, files fingerprinted now, rows forgotten).
    """
    config.THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    known = db.known_files(conn)
    found = list(find_pictures(root, subfolder))
    todo = []
    for place, name, path in found:
        stat, before = path.stat(), known.get(str(path))
        unchanged = (before and before["bytes"] == stat.st_size and before["modified_at"] == stat.st_mtime
                     and preview_path(before["sha256"]).exists())
        if not unchanged:
            todo.append((place, name, path, stat.st_mtime))

    with ThreadPoolExecutor(config.WORKERS) as pool:
        results = pool.map(lambda job: fingerprint(job[2]), todo)
        for number, ((place, name, path, modified_at), result) in enumerate(zip(todo, results), 1):
            db.upsert_image(conn, str(path), place, name, modified_at, result)
            if number % 100 == 0 or number == len(todo):
                print(f"  обработано {number} из {len(todo)}", flush=True)

    forgotten = db.delete_images_except(conn, [str(path) for _, _, path in found])
    return len(found), len(todo), forgotten
