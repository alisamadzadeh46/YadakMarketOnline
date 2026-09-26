"""Root URL configuration.

API routes live under /api/. The Django admin is the operations cockpit where
the site owner approves users, and suppliers manage catalog and credit terms.
"""

import environ
from apps.core import views as core_views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

api_patterns = [
    path("accounts/", include("apps.accounts.urls")),
    path("catalog/", include("apps.catalog.urls")),
    path("discounts/", include("apps.discounts.urls")),
    path("orders/", include("apps.orders.urls")),
    path("suppliers/", include("apps.suppliers.urls")),
    path("blog/", include("apps.blog.urls")),
    path("seo/", include("apps.seo.urls")),
    path("cms/", include("apps.cms.urls")),
    path("commissions/", include("apps.commissions.urls")),
    path("payments/", include("apps.payments.urls")),
]

env = environ.Env()

urlpatterns = [
    # The admin path is configurable and NOT the default "admin/": bots probe
    # /admin/ constantly, and every hit is a free credential-stuffing attempt.
    # Set ADMIN_URL in the environment; keep the trailing slash.
    path(env("ADMIN_URL", default="admin/"), admin.site.urls),
    path("api/", include((api_patterns, "api"))),
    # Private uploads (KYC, receipts) behind a signed token — see
    # apps.core.protected. It lives under /api/ because that is the prefix the
    # edge already routes to Django; anything else falls through to Next.js and
    # comes back as a redirect. Registered outside api_patterns so it keeps a
    # top-level reverse() name and stays a plain browser URL for <img src>.
    path("api/media-protected/", core_views.protected_media, name="protected_media"),
    # Self-hosted API docs (no external CDN assets).
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

# Custom error handlers (400/403/404/500) resolve to these views.
handler404 = "apps.core.views.not_found"
handler500 = "apps.core.views.server_error"

# Serve uploaded media through Django in development only.
if settings.DEBUG:
    # media/private/ holds KYC documents and payment receipts. In production
    # DEBUG is off and nginx refuses that prefix outright; this keeps the dev
    # server honest too, so a hole never shows up only in one environment.
    urlpatterns += [
        re_path(r"^media/private/", core_views.not_found, name="media_private_denied"),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Brand the admin site.
admin.site.site_header = f"{settings.SITE_SHORT_NAME} — پنل مدیریت"
admin.site.site_title = f"{settings.SITE_SHORT_NAME} Admin"
admin.site.index_title = "مدیریت فروشگاه عمده لوازم یدکی"
