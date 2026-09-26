"""Validation for user-supplied uploads.

``normalize_image`` deliberately never raises — it hands an unreadable file
back untouched so a weird camera photo cannot fail a whole upload. That makes
it a fine *normaliser* and a useless *gatekeeper*: a file it cannot parse is
stored as-is.

Uploaded files are served from the site's own origin, so anything the browser
will execute there (``.svg`` carries script, ``.html`` obviously does) becomes
stored XSS against every logged-in user — and the JWT lives in localStorage,
within reach of that script. So the type has to be checked explicitly, by
content and not by the filename the client chose.
"""

import contextlib
import uuid

from rest_framework import serializers

# Raster formats only. SVG is excluded on purpose: it is a script container.
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
DOCUMENT_EXTENSIONS = IMAGE_EXTENSIONS | {".pdf"}

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024

_PDF_MAGIC = b"%PDF-"


def _extension(uploaded) -> str:
    name = getattr(uploaded, "name", "") or ""
    return ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""


def _looks_like_image(uploaded) -> bool:
    """True only when Pillow can actually decode it as a raster image."""
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover - Pillow is a hard dependency
        return True
    try:
        uploaded.seek(0)
        Image.open(uploaded).verify()
        return True
    except Exception:
        return False
    finally:
        with contextlib.suppress(Exception):
            uploaded.seek(0)


def _looks_like_pdf(uploaded) -> bool:
    try:
        uploaded.seek(0)
        head = uploaded.read(5)
        return head == _PDF_MAGIC
    except Exception:
        return False
    finally:
        with contextlib.suppress(Exception):
            uploaded.seek(0)


def validate_image_upload(uploaded, max_bytes: int = MAX_IMAGE_BYTES):
    """Raise ValidationError unless this really is a web-safe raster image."""
    if uploaded is None:
        return uploaded
    if uploaded.size > max_bytes:
        raise serializers.ValidationError(f"حجم فایل نباید بیش از {max_bytes // (1024 * 1024)} مگابایت باشد.")
    if _extension(uploaded) not in IMAGE_EXTENSIONS:
        raise serializers.ValidationError("فقط تصویر با فرمت JPG، PNG یا WEBP مجاز است.")
    if not _looks_like_image(uploaded):
        raise serializers.ValidationError("فایل ارسالی یک تصویر معتبر نیست.")
    return uploaded


def validate_document_upload(uploaded, max_bytes: int = MAX_DOCUMENT_BYTES):
    """Same, but a PDF is also acceptable (scanned licences usually are)."""
    if uploaded is None:
        return uploaded
    if uploaded.size > max_bytes:
        raise serializers.ValidationError(f"حجم فایل نباید بیش از {max_bytes // (1024 * 1024)} مگابایت باشد.")
    ext = _extension(uploaded)
    if ext not in DOCUMENT_EXTENSIONS:
        raise serializers.ValidationError("فقط فایل JPG، PNG، WEBP یا PDF مجاز است.")
    if ext == ".pdf":
        if not _looks_like_pdf(uploaded):
            raise serializers.ValidationError("فایل ارسالی یک PDF معتبر نیست.")
    elif not _looks_like_image(uploaded):
        raise serializers.ValidationError("فایل ارسالی یک تصویر معتبر نیست.")
    return uploaded


def opaque_name(original_name: str) -> str:
    """A random filename that keeps only the (already validated) extension.

    The client's filename never reaches the filesystem: it could carry path
    separators, be unreasonably long, or leak the uploader's own naming.
    """
    ext = ("." + original_name.rsplit(".", 1)[-1].lower()) if "." in (original_name or "") else ""
    if ext not in DOCUMENT_EXTENSIONS:
        ext = ""
    return f"{uuid.uuid4().hex}{ext}"
