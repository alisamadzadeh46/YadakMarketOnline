"""Account routes mounted under /api/accounts/."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenVerifyView

from . import views, views_auth, views_extra

router = DefaultRouter()
router.register("addresses", views.AddressViewSet, basename="address")
router.register("supplier/shops", views_extra.ShopApprovalViewSet, basename="shop-approval")

urlpatterns = [
    # Registration & JWT auth
    path("register/", views.RegisterView.as_view(), name="register"),
    # The JWT travels in HttpOnly cookies, not the response body — see
    # apps.accounts.views_auth for why.
    path("token/", views_auth.CookieTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", views_auth.CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", views_auth.LogoutView.as_view(), name="logout"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # Profile
    path("me/", views.MeView.as_view(), name="me"),
    # Password reset via SMS OTP
    path("password-reset/request/", views_extra.PasswordResetRequestView.as_view(), name="pw_reset_request"),
    path("password-reset/confirm/", views_extra.PasswordResetConfirmView.as_view(), name="pw_reset_confirm"),
    # Password reset via emailed link (30-minute, single-use)
    path(
        "password-reset/email/request/",
        views_extra.EmailPasswordResetRequestView.as_view(),
        name="pw_reset_email_request",
    ),
    path(
        "password-reset/email/verify/", views_extra.EmailPasswordResetVerifyView.as_view(), name="pw_reset_email_verify"
    ),
    path(
        "password-reset/email/confirm/",
        views_extra.EmailPasswordResetConfirmView.as_view(),
        name="pw_reset_email_confirm",
    ),
    path("shop-profile/", views.ShopkeeperProfileView.as_view(), name="shop_profile"),
    path("kyc/upload/", views.KYCDocumentUploadView.as_view(), name="kyc_upload"),
    # Addresses (router)
    path("", include(router.urls)),
]
