"""JWT carried in an HttpOnly cookie instead of localStorage.

localStorage is readable by any script running on the page, so a single stored
XSS anywhere on the site hands an attacker a bearer token that stays valid for
its whole lifetime — and refresh tokens live for a week. An HttpOnly cookie is
not reachable from JavaScript at all, so the same XSS can at most act as the
user while the page is open; it cannot walk away with the credential.

The Authorization header is still accepted. Nothing stores a token in the
browser any more, but API clients and scripts use it, and dropping it would
break them for no security gain — the risk was the storage, not the header.

Because a cookie rides along automatically, cookie-authenticated writes need
CSRF protection; header-authenticated ones do not (an attacker's page cannot
set that header). SameSite=Lax already blocks cross-site POSTs, and the CSRF
check below is the second lock.
"""

from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework import exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication

SAFE_METHODS = ("GET", "HEAD", "OPTIONS", "TRACE")


class _CSRFCheck(CsrfViewMiddleware):
    def _reject(self, request, reason):
        return reason


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate from the Authorization header, falling back to the cookie."""

    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            # Header path: unchanged behaviour, and no CSRF concern.
            raw_token = self.get_raw_token(header)
            if raw_token is None:
                return None
            validated = self.get_validated_token(raw_token)
            return self.get_user(validated), validated

        raw_token = request.COOKIES.get(settings.JWT_ACCESS_COOKIE)
        if not raw_token:
            return None

        validated = self.get_validated_token(raw_token)
        user = self.get_user(validated)
        self._enforce_csrf(request)
        return user, validated

    def _enforce_csrf(self, request):
        """Django's own CSRF check, applied only to cookie-authenticated writes."""
        if request.method in SAFE_METHODS:
            return
        check = _CSRFCheck(lambda req: None)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise exceptions.PermissionDenied(f"CSRF Failed: {reason}")
