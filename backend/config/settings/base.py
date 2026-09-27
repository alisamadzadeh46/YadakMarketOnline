"""Base settings shared by every environment.

Environment-specific values live in dev.py / prod.py. Secrets are read from the
environment (django-environ) so nothing sensitive is ever committed.
"""

from datetime import timedelta
from pathlib import Path

import environ

# BASE_DIR = .../backend
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    # The storefront in the development compose file is published on port 3010.
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:3010"]),
)

# Read a .env file if present (docker-compose also injects real env vars).
environ.Env.read_env(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key secret in production.
SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# ---- Applications -----------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "django_celery_beat",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.catalog",
    "apps.discounts",
    "apps.orders",
    "apps.notifications",
    "apps.suppliers",
    "apps.blog",
    "apps.seo",
    "apps.cms",
    "apps.commissions",
    "apps.payments",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---- Middleware -------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serve admin static files
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---- Database ---------------------------------------------------------------
# The credentials always come from DATABASE_URL; the default only suits a local
# PostgreSQL that trusts connections without a password.
DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://yadak@localhost:5432/yadakmart"),
}
# Reuse DB connections for 60s to cut per-request connection overhead.
DATABASES["default"]["CONN_MAX_AGE"] = 60

# ---- Custom user model ------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

# ---- Password hashing & validation ------------------------------------------
# Argon2 first: memory-hard hashing resists GPU cracking better than PBKDF2.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 9},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---- Internationalization (Persian, Tehran) ---------------------------------
LANGUAGE_CODE = "fa-ir"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

# ---- Static & media ---------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Private uploads (KYC documents, payment receipts) live under
# MEDIA_ROOT/private/ and are never served by the public /media/ alias. In
# production nginx streams them from an `internal` location after Django has
# checked the signed token; without nginx (runserver, tests) Django serves them
# itself. See apps.core.protected.
USE_X_ACCEL_REDIRECT = env.bool("USE_X_ACCEL_REDIRECT", default=False)
X_ACCEL_MEDIA_PREFIX = env("X_ACCEL_MEDIA_PREFIX", default="/protected-media/")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---- Django REST Framework --------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # Reads the Authorization header, then falls back to the HttpOnly
        # cookie (and enforces CSRF on cookie-authenticated writes).
        "apps.accounts.authentication.CookieJWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Throttling limits brute-force and scraping out of the box.
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min", "user": "600/min"},
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "PAGE_SIZE": 24,
}

# ---- JWT (SimpleJWT) --------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ---- Auth cookies -----------------------------------------------------------
# The access/refresh JWTs live in HttpOnly cookies so no script can read them.
# JWT_FLAG_COOKIE is readable and holds no secret: the SPA only needs to know
# *that* a session exists. See apps.accounts.views_auth.
JWT_ACCESS_COOKIE = env("JWT_ACCESS_COOKIE", default="ym_at")
JWT_REFRESH_COOKIE = env("JWT_REFRESH_COOKIE", default="ym_rt")
JWT_FLAG_COOKIE = env("JWT_FLAG_COOKIE", default="ym_auth")
JWT_COOKIE_DOMAIN = env("JWT_COOKIE_DOMAIN", default="")
# Lax, not Strict: the payment gateway returns the buyer by top-level
# navigation, and Strict would drop the cookie on that hop and look like a
# surprise logout. Lax still blocks cross-site POST, which is the CSRF vector.
JWT_COOKIE_SAMESITE = env("JWT_COOKIE_SAMESITE", default="Lax")
JWT_COOKIE_SECURE = env.bool("JWT_COOKIE_SECURE", default=not DEBUG)
# Returning the raw token in the response body would undo the whole point.
JWT_TOKENS_IN_BODY = env.bool("JWT_TOKENS_IN_BODY", default=False)

SPECTACULAR_SETTINGS = {
    "TITLE": "YadakMart API",
    "DESCRIPTION": "B2B auto-parts wholesale marketplace API.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ---- CORS -------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True

# Django checks the Origin header on every unsafe request, so the origins we
# let call us with credentials must also be trusted for CSRF — otherwise a
# cross-origin setup (the dev stack, where the site is on :3010 and the API on
# :8020) fails every write with a CSRF error. In production both live on one
# domain and prod.py sets this explicitly to the real hostnames.
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=CORS_ALLOWED_ORIGINS)

# ---- Celery -----------------------------------------------------------------
# Without credentials in the URL the client uses RabbitMQ's default account.
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="amqp://rabbitmq:5672//")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://redis:6379/1")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TASK_ACKS_LATE = True  # re-deliver tasks if a worker crashes mid-run

# SMS gets its own queue so a burst of reminders cannot starve order/invoice
# jobs, and so a provider outage only backs up texts. See apps.notifications.tasks.
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_ROUTES = {
    "notifications.send_sms": {"queue": "sms"},
    "notifications.send_bulk_sms": {"queue": "sms"},
}
# Messages per minute handed to the provider. Lower it if they complain.
SMS_RATE_LIMIT = env("SMS_RATE_LIMIT", default="30/m")
# One task at a time per worker process, so a slow provider response never
# multiplies into many parallel connections.
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# ---- Cache & sessions (Redis) ----------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://redis:6379/2"),
    },
}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# ---- Domain constants -------------------------------------------------------
# Minutes a buyer has to upload a card-to-card receipt before the order auto-closes.
PAYMENT_RECEIPT_WINDOW_MINUTES = env.int("PAYMENT_RECEIPT_WINDOW_MINUTES", default=30)

# ---- Site identity ----------------------------------------------------------
# Everything that identifies the business is configured per deployment, so the
# code base holds no real name, address or domain. The values appear in SMS
# texts, e-mails, gateway descriptions and the admin header.
SITE_NAME = env("SITE_NAME", default="یدک مارکت آنلاین")
SITE_SHORT_NAME = env("SITE_SHORT_NAME", default="یدک مارکت")
SITE_TAGLINE = env("SITE_TAGLINE", default="پخش عمده لوازم یدکی خودرو")
# Postal address printed in e-mail footers; leave empty to omit it.
SITE_ADDRESS = env("SITE_ADDRESS", default="")
# Seller shown for products that are not linked to a supplier account.
DEFAULT_SELLER_NAME = env("DEFAULT_SELLER_NAME", default="فروشگاه لوازم یدکی")

# Where the frontend lives — links in SMS/e-mails point here, and the payment
# gateway callback redirects the buyer's browser here after verification.
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3010").rstrip("/")

# ---- Email (SMTP; used for the password-reset link) -------------------------
# Credentials come from the environment — never committed. Without a host
# configured the console backend prints the message instead of sending it, so
# development never silently depends on real SMTP.
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=20)
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend" if EMAIL_HOST else "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    default=(f"{SITE_NAME} <{EMAIL_HOST_USER}>" if EMAIL_HOST_USER else "webmaster@localhost"),
)

# ---- SMS (pluggable; Niazpardaz in production) ------------------------------
SMS_PROVIDER = env("SMS_PROVIDER", default="console")
NIAZPARDAZ_USERNAME = env("NIAZPARDAZ_USERNAME", default="")
NIAZPARDAZ_PASSWORD = env("NIAZPARDAZ_PASSWORD", default="")
NIAZPARDAZ_LINE_NUMBER = env("NIAZPARDAZ_LINE_NUMBER", default="")

# Default lead time (days before due date) for settlement reminder SMS.
# Suppliers can override this per credit account from their panel/admin.
DEFAULT_SETTLEMENT_REMINDER_DAYS = env.int("DEFAULT_SETTLEMENT_REMINDER_DAYS", default=2)

# ---- Monitoring (Sentry) -----------------------------------------------------
# No-ops unless SENTRY_DSN is provided; guarded so environments without the
# sdk installed keep working.
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    try:
        import sentry_sdk

        sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=0.1, send_default_pii=False)
    except ImportError:
        pass
