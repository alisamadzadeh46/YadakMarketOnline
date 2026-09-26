"""Login / refresh / logout that put the JWT in cookies rather than the body.

Three cookies are involved:

  * access  (HttpOnly) — the bearer token, unreadable by JavaScript
  * refresh (HttpOnly) — only ever sent back to the refresh endpoint
  * ym_auth (readable) — a flag, not a credential. The UI needs a synchronous
    "is someone signed in?" answer to decide whether to show the guest cart;
    it used to read the token itself for that. This carries no secret.

The CSRF cookie is issued alongside so the SPA can echo it back on writes.
"""

import contextlib

from django.conf import settings
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import UserSerializer


def _cookie_kwargs():
    return {
        "domain": settings.JWT_COOKIE_DOMAIN or None,
        "path": "/",
        "secure": settings.JWT_COOKIE_SECURE,
        "samesite": settings.JWT_COOKIE_SAMESITE,
    }


def set_auth_cookies(response, access, refresh=None):
    """Attach the session to the response."""
    common = _cookie_kwargs()
    response.set_cookie(
        settings.JWT_ACCESS_COOKIE,
        str(access),
        max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        **common,
    )
    if refresh is not None:
        response.set_cookie(
            settings.JWT_REFRESH_COOKIE,
            str(refresh),
            max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
            httponly=True,
            **common,
        )
    # Readable on purpose: it says a session exists, nothing more. Its lifetime
    # tracks the refresh token, since that is what decides how long the user
    # can stay signed in without typing a password again.
    response.set_cookie(
        settings.JWT_FLAG_COOKIE,
        "1",
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=False,
        **common,
    )
    return response


def clear_auth_cookies(response):
    common = _cookie_kwargs()
    for name in (
        settings.JWT_ACCESS_COOKIE,
        settings.JWT_REFRESH_COOKIE,
        settings.JWT_FLAG_COOKIE,
    ):
        response.delete_cookie(name, path=common["path"], domain=common["domain"], samesite=common["samesite"])
    return response


def _body_tokens(access, refresh=None):
    """Legacy escape hatch.

    Off by default: putting the token back in the response body would let a
    script read it again, which is the whole thing this change removes. Flip
    JWT_TOKENS_IN_BODY on only to unblock a client that cannot use cookies.
    """
    if not settings.JWT_TOKENS_IN_BODY:
        return {}
    data = {"access": str(access)}
    if refresh is not None:
        data["refresh"] = str(refresh)
    return data


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CookieTokenObtainPairView(APIView):
    """Sign in. Credentials in, cookies out — no token in the response body."""

    permission_classes = [permissions.AllowAny]
    # No authentication_classes override: with an empty list DRF turns a failed
    # login into 403 instead of 401, and the SPA keys off that status.

    def post(self, request):
        serializer = TokenObtainPairSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        refresh = serializer.validated_data.get("refresh")
        access = serializer.validated_data.get("access")
        user = serializer.user

        payload = {
            "user": UserSerializer(user, context={"request": request}).data,
            "csrf_token": get_token(request),
        }
        payload.update(_body_tokens(access, refresh))
        return set_auth_cookies(Response(payload), access, refresh)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CookieTokenRefreshView(APIView):
    """Swap the refresh cookie for a fresh access cookie.

    Deliberately reads the refresh token from the cookie rather than the body,
    so a script cannot mint a new access token from a token it scraped.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        raw = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
        if not raw:
            # Nothing to refresh: make sure a stale flag cookie does not keep
            # the UI pretending the visitor is signed in.
            response = Response({"detail": "نشست شما منقضی شده است."}, status=status.HTTP_401_UNAUTHORIZED)
            return clear_auth_cookies(response)

        try:
            token = RefreshToken(raw)
            access = token.access_token
            rotated = None
            if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS"):
                if settings.SIMPLE_JWT.get("BLACKLIST_AFTER_ROTATION"):
                    # AttributeError: the blacklist app is not installed.
                    with contextlib.suppress(AttributeError):
                        token.blacklist()
                rotated = RefreshToken.for_user(self.get_user(token))
                access = rotated.access_token
        except TokenError:
            response = Response({"detail": "نشست شما منقضی شده است."}, status=status.HTTP_401_UNAUTHORIZED)
            return clear_auth_cookies(response)

        payload = {"detail": "ok", "csrf_token": get_token(request)}
        payload.update(_body_tokens(access, rotated))
        return set_auth_cookies(Response(payload), access, rotated)

    @staticmethod
    def get_user(token):
        from django.contrib.auth import get_user_model

        return get_user_model().objects.get(pk=token["user_id"])


class LogoutView(APIView):
    """Sign out: blacklist the refresh token and drop every auth cookie."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        raw = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
        if raw:
            # Already expired, already blacklisted, or the app is not
            # installed — the cookies still go, which is what matters.
            with contextlib.suppress(TokenError, AttributeError):
                RefreshToken(raw).blacklist()
        return clear_auth_cookies(Response({"detail": "خروج انجام شد."}))
