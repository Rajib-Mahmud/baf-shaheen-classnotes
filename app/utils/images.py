"""Upload image validation and processing.

Security posture:
- Extension allowlist AND content validation with Pillow.
- Every accepted image is re-encoded from decoded pixel data, which strips
  EXIF and any bytes appended/embedded in the original file. Raw uploaded
  bytes are never written to disk or served.
- Stored filenames are uuid4-based; the client filename is kept only as a
  display label.
"""

import io
import os
import uuid

from PIL import Image, ImageOps, UnidentifiedImageError

# Decompression-bomb guard: refuse images that would decode to more than
# 64 megapixels (a 40 KB PNG can otherwise expand to gigabytes of RAM).
Image.MAX_IMAGE_PIXELS = 64_000_000

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

# Re-encode target per detected source format.
_SAVE_FORMAT = {
    "JPEG": ("jpg", "JPEG"),
    "PNG": ("png", "PNG"),
    "WEBP": ("webp", "WEBP"),
}

MIME_BY_EXT = {
    "jpg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


class InvalidImageError(ValueError):
    pass


def _extension_ok(filename):
    if "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def process_upload(
    file_storage, upload_folder, thumb_max=400, max_bytes=8 * 1024 * 1024
):
    """Validate one uploaded file and write a re-encoded image + thumbnail.

    Returns (stored_name, thumb_name, original_name).
    Raises InvalidImageError on anything that is not a valid allowed image.
    """
    original_name = file_storage.filename or ""
    if not _extension_ok(original_name):
        raise InvalidImageError(
            "Only .jpg, .jpeg, .png and .webp images are allowed."
        )
    # Display label only; strip control characters so it can never smuggle
    # CR/LF into a Content-Disposition header.
    original_name = "".join(
        ch for ch in original_name if ch.isprintable()
    ).strip()[:256] or "photo"

    raw = file_storage.read(max_bytes + 1)
    if not raw:
        raise InvalidImageError("Empty file.")
    if len(raw) > max_bytes:
        raise InvalidImageError(
            f"Each photo must be under {max_bytes // (1024 * 1024)} MB."
        )

    # Pass 1: verify() checks structural integrity without full decode.
    try:
        probe = Image.open(io.BytesIO(raw))
        probe.verify()
        detected = probe.format
    except (UnidentifiedImageError, OSError, ValueError):
        raise InvalidImageError("File is not a valid image.")
    except Image.DecompressionBombError:
        raise InvalidImageError("Image dimensions are too large.")

    if detected not in _SAVE_FORMAT:
        raise InvalidImageError("Unsupported image format.")

    # Pass 2: full decode (verify() leaves the parser unusable, so reopen).
    try:
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img)  # honour orientation before EXIF is lost
        img.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise InvalidImageError("File is not a valid image.")
    except Image.DecompressionBombError:
        raise InvalidImageError("Image dimensions are too large.")

    ext, save_format = _SAVE_FORMAT[detected]
    if save_format == "JPEG" and img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    uid = uuid.uuid4().hex
    stored_name = f"{uid}.{ext}"
    thumb_name = f"{uid}_thumb.{ext}"

    save_kwargs = {"quality": 85} if save_format in ("JPEG", "WEBP") else {}
    img.save(os.path.join(upload_folder, stored_name), save_format, **save_kwargs)

    thumb = img.copy()
    thumb.thumbnail((thumb_max, thumb_max))
    thumb.save(os.path.join(upload_folder, thumb_name), save_format, **save_kwargs)

    return stored_name, thumb_name, original_name


def delete_note_files(note, upload_folder):
    """Remove all image files belonging to a note from disk."""
    for image in note.images:
        for name in (image.file_path, image.thumb_path):
            path = os.path.join(upload_folder, name)
            try:
                os.remove(path)
            except OSError:
                pass
