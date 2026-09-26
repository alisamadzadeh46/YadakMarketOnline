"""Development settings — convenient, noisy, never for production."""

from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Print emails (e.g. verification links) to the console during development.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Allow the Next.js dev server to talk to the API without friction.
CORS_ALLOW_ALL_ORIGINS = True
