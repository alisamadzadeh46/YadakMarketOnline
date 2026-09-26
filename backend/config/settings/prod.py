"""Production settings — security hardened.

Everything sensitive comes from the environment. HTTPS is assumed to be
terminated by nginx/Caddy in front of gunicorn.
"""

from .base import *  # noqa: F401,F403

DEBUG = False

# HTTPS is terminated by nginx, which also does the 80->443 redirect, so
# Django's own redirect stays off by default to avoid a redirect loop.
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)  # noqa: F405
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # JS needs to read the CSRF token for the SPA

# HSTS pins browsers to HTTPS for the given period. Keep it at 0 while the
# site runs on a self-signed certificate (an IP-only deployment) — turn it on
# once a real domain + trusted certificate is in place, otherwise browsers
# would hard-fail on the untrusted cert with no way back.
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0

# nginx is in front, so let it stream private media (X-Accel-Redirect).
USE_X_ACCEL_REDIRECT = env.bool("USE_X_ACCEL_REDIRECT", default=True)  # noqa: F405

# Extra hardening headers.
SECURE_CONTENT_TYPE_NOSNIFF = True
# "same-origin" strips the Referer entirely on cross-origin navigation, which
# the payment gateways read as an "invalid referrer" and refuse. This variant
# sends the bare origin (no path, no query, no token) cross-origin over HTTPS
# and nothing at all on a downgrade to HTTP — see nginx/prod.conf.
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

# Trusted origins for CSRF must be the real domains in production; the site's
# own URL is trusted unless the list is set explicitly.
CSRF_TRUSTED_ORIGINS = env.list(  # noqa: F405
    "CSRF_TRUSTED_ORIGINS",
    default=[FRONTEND_URL],  # noqa: F405
)

# Structured logging to stdout for the container platform to collect.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.security": {"handlers": ["console"], "level": "WARNING"},
    },
}
