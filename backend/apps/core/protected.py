"""Private media: files that must never be readable by URL guessing.

KYC documents (national card, business licence) and card-to-card receipts are
uploaded by users and were previously written under MEDIA_ROOT and served by
nginx's public ``/media/`` alias — no authentication at all. Both paths were
guessable (``kyc/<sequential user id>/…``, ``receipts/YM<yymm><padded id>/…``),
so anyone could enumerate other shops' identity documents and bank slips.

These files now live under ``MEDIA_ROOT/private/`` which nginx refuses to serve
directly. Reaching one takes a signed, short-lived token that only an
authorised API response hands out.

Why a signed URL instead of an authenticated endpoint: the panels show these
files with plain ``<img src>`` / ``<a href>``, and the browser sends no
Authorization header on those. The token travels in the URL, is an HMAC over
the file path keyed by SECRET_KEY, and expires — so it cannot be forged, and a
leaked link stops working on its own.
"""

import os
import posixpath
from urllib.parse import quote

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.http import FileResponse, Http404, HttpResponse
from django.urls import reverse

# Everything under this prefix (relative to MEDIA_ROOT) is private.
PRIVATE_PREFIX = "private/"

_SALT = "yadakmart.protected-media"
# Long enough to open a panel and click through a few documents, short enough
# that a link pasted into a chat is dead by the time anyone else tries it.
TOKEN_TTL = 900  # seconds


def _signer():
    return TimestampSigner(salt=_SALT)


def sign_path(relative_path: str) -> str:
    """Sign a MEDIA_ROOT-relative path into an opaque token."""
    return _signer().sign(relative_path)


def unsign_path(token: str, ttl: int = TOKEN_TTL) -> str:
    """Reverse of :func:`sign_path`. Raises BadSignature when invalid/expired."""
    return _signer().unsign(token, max_age=ttl)


def is_private(relative_path: str) -> bool:
    return str(relative_path or "").startswith(PRIVATE_PREFIX)


def protected_url(request, relative_path: str) -> str:
    """A signed, absolute URL an authorised viewer can put in an <img src>.

    Non-private paths are returned as ordinary media URLs so callers can pass
    any file through without caring which kind it is.
    """
    if not relative_path:
        return ""
    if not is_private(relative_path):
        url = settings.MEDIA_URL + str(relative_path).lstrip("/")
        if not url.startswith("/"):
            url = "/" + url
        return request.build_absolute_uri(url) if request else url

    url = f"{reverse('protected_media')}?t={quote(sign_path(str(relative_path)))}"
    return request.build_absolute_uri(url) if request else url


def serve_private(relative_path: str) -> HttpResponse:
    """Hand the file to the client.

    In production nginx does the actual sending: we answer with an empty body
    plus ``X-Accel-Redirect`` pointing at an ``internal`` location, so Django
    never streams bytes and the file still cannot be fetched directly. Without
    that (runserver, tests) we fall back to serving it ourselves.
    """
    # Defence in depth: the token is signed, but never let a crafted path climb
    # out of the private directory even if signing were somehow bypassed.
    clean = posixpath.normpath("/" + str(relative_path).replace("\\", "/")).lstrip("/")
    if not is_private(clean):
        raise Http404

    if getattr(settings, "USE_X_ACCEL_REDIRECT", False):
        inner = clean[len(PRIVATE_PREFIX) :]
        response = HttpResponse(status=200)
        response["X-Accel-Redirect"] = f"{settings.X_ACCEL_MEDIA_PREFIX}{quote(inner)}"
        # Let nginx decide the type/length; clearing this avoids a wrong guess.
        del response["Content-Type"]
        response["Content-Disposition"] = f'inline; filename="{posixpath.basename(clean)}"'
        return response

    full = os.path.join(settings.MEDIA_ROOT, clean)
    if not os.path.exists(full):
        raise Http404
    return FileResponse(open(full, "rb"))


def serve_signed(token: str) -> HttpResponse:
    """Validate a token from the query string and serve what it points at."""
    if not token:
        raise Http404
    try:
        relative_path = unsign_path(token)
    except SignatureExpired:
        return HttpResponse("این لینک منقضی شده است. صفحه را تازه کنید.", status=410)
    except BadSignature:
        raise Http404 from None
    return serve_private(relative_path)
