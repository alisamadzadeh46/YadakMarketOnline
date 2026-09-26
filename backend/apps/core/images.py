"""Normalise uploaded images so the storefront never serves a 6 MB phone photo.

Suppliers upload straight from a camera roll: 4000×3000, several megabytes,
sometimes rotated only by EXIF. Those were stored as-is, which is why the
gallery blew out of its box on desktop and why product pages were slow on a
mobile connection.

``normalize_image`` returns a Django file ready to assign to an ImageField:
  * honours the EXIF orientation tag, then strips the EXIF block
  * caps the long edge at MAX_EDGE, never upscaling a smaller image
  * flattens transparency onto white and re-encodes as progressive JPEG,
    except for PNGs that genuinely need an alpha channel
"""

import io
import logging
import os

from django.core.files.uploadedfile import InMemoryUploadedFile

logger = logging.getLogger(__name__)

MAX_EDGE = 1600  # px on the longest side — plenty for a zoomed gallery
JPEG_QUALITY = 82
# Anything at or below this is already web-sized; re-encoding would only lose
# quality for no gain.
SKIP_UNDER_BYTES = 120 * 1024


def _has_transparency(img) -> bool:
    """True only when the image really uses its alpha channel."""
    if img.mode == "P":
        return "transparency" in img.info
    if img.mode not in ("RGBA", "LA"):
        return False
    alpha = img.getchannel("A")
    lo, hi = alpha.getextrema()
    return lo < 255


def normalize_image(uploaded, max_edge: int = MAX_EDGE, square: bool = False):
    """Return a resized/re-encoded copy of ``uploaded``.

    Never raises: an unreadable or exotic file is returned untouched rather
    than failing the whole upload. The caller keeps working with a normal
    Django file object either way.
    """
    try:
        from PIL import Image, ImageOps
    except ImportError:  # pragma: no cover - Pillow is a hard dependency
        return uploaded

    try:
        uploaded.seek(0)
        img = Image.open(uploaded)
        img.load()
    except Exception as exc:
        logger.warning("normalize_image: cannot read upload (%s); storing as-is", exc)
        uploaded.seek(0)
        return uploaded

    original_format = (img.format or "").upper()
    # Both conditions matter. Judging by dimensions alone let a 1600x1600 PNG
    # through at 3 MB; judging by bytes alone would keep a 4000px thumbnail.
    small_enough = max(img.size) <= max_edge
    light_enough = 0 < getattr(uploaded, "size", 0) <= SKIP_UNDER_BYTES
    # A non-square image still has to be padded even when it is small and light,
    # otherwise the gallery keeps mixing 4:3 and 3:4 shots.
    already_square = img.size[0] == img.size[1]
    if small_enough and light_enough and (already_square or not square):
        uploaded.seek(0)
        return uploaded

    try:
        # A photo taken sideways carries its rotation in EXIF only; bake it in
        # before we drop the EXIF block, or the image appears rotated on the site.
        img = ImageOps.exif_transpose(img)

        # Only keep PNG when the alpha channel is actually used. A photo saved
        # as RGBA PNG is opaque but re-encodes to a multi-megabyte PNG — that
        # is how five product photos came to weigh 10 MB on one page.
        keep_alpha = original_format == "PNG" and _has_transparency(img)
        if keep_alpha:
            img = img.convert("RGBA")
        else:
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
                flat = Image.new("RGB", img.size, (255, 255, 255))
                flat.paste(img, mask=img.split()[-1])
                img = flat
            else:
                img = img.convert("RGB")

        if max(img.size) > max_edge:
            img.thumbnail((max_edge, max_edge), Image.LANCZOS)

        if square and img.size[0] != img.size[1]:
            # Pad (never crop) onto a square canvas. Cropping would cut parts
            # off a part photo; padding keeps the whole item visible and makes
            # every image in the gallery exactly the same shape, so switching
            # between them no longer resizes the picture.
            side = max(img.size)
            canvas_mode = "RGBA" if keep_alpha else "RGB"
            bg = (255, 255, 255, 0) if keep_alpha else (255, 255, 255)
            canvas = Image.new(canvas_mode, (side, side), bg)
            canvas.paste(img, ((side - img.size[0]) // 2, (side - img.size[1]) // 2), img if keep_alpha else None)
            img = canvas

        buf = io.BytesIO()
        if keep_alpha:
            img.save(buf, format="PNG", optimize=True)
            ext, content_type = ".png", "image/png"
        else:
            img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
            ext, content_type = ".jpg", "image/jpeg"
        buf.seek(0)

        base = os.path.splitext(os.path.basename(getattr(uploaded, "name", "image")))[0]
        return InMemoryUploadedFile(buf, "ImageField", f"{base}{ext}", content_type, buf.getbuffer().nbytes, None)
    except Exception as exc:
        logger.warning("normalize_image: resize failed (%s); storing as-is", exc)
        uploaded.seek(0)
        return uploaded
