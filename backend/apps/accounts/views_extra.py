"""Password reset via SMS OTP + supplier-side shop approval endpoints."""

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle
from rest_framework.views import APIView

from apps.accounts.permissions import IsSiteAdmin
from apps.notifications.models import SmsLog
from apps.notifications.tasks import send_sms

from .models import PasswordResetToken, PhoneOTP, ShopkeeperProfile, User
from .serializers import ShopkeeperProfileSerializer

# How long an emailed reset link stays usable.
EMAIL_RESET_MINUTES = 30


class PhonePerMinuteThrottle(SimpleRateThrottle):
    """At most one OTP per phone per minute (stops rapid resends)."""

    rate = "1/min"
    scope = "pw_reset_min"

    def get_cache_key(self, request, view):
        phone = str(request.data.get("phone", "")).strip()
        return f"throttle_{self.scope}_{phone}" if phone else None


class PhonePerHourThrottle(SimpleRateThrottle):
    """At most 8 OTPs per phone per hour (stops SMS bombing a victim)."""

    rate = "8/hour"
    scope = "pw_reset_hour"

    def get_cache_key(self, request, view):
        phone = str(request.data.get("phone", "")).strip()
        return f"throttle_{self.scope}_{phone}" if phone else None


class PhoneConfirmThrottle(SimpleRateThrottle):
    """At most 10 code guesses per phone per hour.

    The per-IP limit alone lets an attacker spread guesses over many
    addresses; bounding attempts per phone keeps a 6-digit code unguessable.
    """

    rate = "10/hour"
    scope = "pw_reset_confirm"

    def get_cache_key(self, request, view):
        phone = str(request.data.get("phone", "")).strip()
        return f"throttle_{self.scope}_{phone}" if phone else None


class ResetRequestIpThrottle(AnonRateThrottle):
    # Generous per-IP ceiling: keyed per phone above does the real work, this
    # only blocks mass abuse from a single machine.
    rate = "30/hour"


def _fa(n) -> str:
    """Latin -> Persian digits for user-facing messages."""
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


class PasswordResetRequestView(APIView):
    """POST {phone} -> sends a 6-digit code by SMS (valid 5 minutes)."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [PhonePerMinuteThrottle, PhonePerHourThrottle, ResetRequestIpThrottle]

    def throttled(self, request, wait):
        """Replace DRF's generic 429 with a message the user can act on."""
        from rest_framework.exceptions import Throttled

        wait = int(wait or 0)
        if wait <= 90:
            detail = f"کد به‌تازگی برای این شماره ارسال شده است. لطفاً {_fa(wait)} ثانیه دیگر دوباره تلاش کنید."
        else:
            detail = (
                f"سقف ارسال کد برای این شماره پر شده است. لطفاً حدود {_fa(max(1, wait // 60))} دقیقه دیگر تلاش کنید."
            )
        raise Throttled(detail=detail)

    def post(self, request):
        phone = str(request.data.get("phone", "")).strip()
        # Product decision: tell the user plainly when the phone isn't registered
        # (the strict 5/hour throttle keeps enumeration abuse in check).
        if not User.objects.filter(phone=phone, is_active=True).exists():
            return Response(
                {"detail": "این شماره موبایل در سیستم ثبت نشده است."},
                status=status.HTTP_404_NOT_FOUND,
            )

        code = f"{secrets.randbelow(1_000_000):06d}"
        # Validity matches the 2-minute countdown shown in the UI.
        PhoneOTP.objects.create(
            phone=phone,
            code=code,
            purpose=PhoneOTP.Purpose.PASSWORD_RESET,
            expires_at=timezone.now() + timedelta(minutes=2),
        )
        send_sms.delay(
            phone,
            f"{settings.SITE_SHORT_NAME}\nکد بازیابی رمز عبور: {code}",
            kind=SmsLog.Kind.VERIFICATION,
        )
        return Response({"detail": "کد بازیابی پیامک شد."})


class PasswordResetConfirmView(APIView):
    """POST {phone, code, new_password} -> verifies the OTP and sets the password."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle, PhoneConfirmThrottle]

    def throttled(self, request, wait):
        from rest_framework.exceptions import Throttled

        raise Throttled(detail=(f"تلاش بیش از حد. لطفاً {_fa(int(wait or 60))} ثانیه دیگر دوباره تلاش کنید."))

    def post(self, request):
        phone = str(request.data.get("phone", "")).strip()
        code = str(request.data.get("code", "")).strip()
        new_password = request.data.get("new_password", "")

        otp = (
            PhoneOTP.objects.filter(phone=phone, code=code, purpose=PhoneOTP.Purpose.PASSWORD_RESET)
            .order_by("-created_at")
            .first()
        )
        if not otp or not otp.is_valid:
            return Response(
                {"detail": "کد نامعتبر یا منقضی شده است."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = User.objects.filter(phone=phone, is_active=True).first()
        if not user:
            return Response(
                {"detail": "کد نامعتبر یا منقضی شده است."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            return Response({"detail": " ".join(exc.messages)}, status=400)

        user.set_password(new_password)
        user.save(update_fields=["password"])
        otp.is_used = True
        otp.save(update_fields=["is_used"])
        return Response({"detail": "رمز عبور با موفقیت تغییر کرد."})


class EmailPerHourThrottle(SimpleRateThrottle):
    """At most 5 reset emails per address per hour (stops mailbox bombing)."""

    rate = "5/hour"
    scope = "pw_reset_email"

    def get_cache_key(self, request, view):
        email = str(request.data.get("email", "")).strip().lower()
        return f"throttle_{self.scope}_{email}" if email else None


class EmailPasswordResetRequestView(APIView):
    """POST {email} -> emails a one-time reset link valid for 30 minutes.

    Deliberately checks the address exists first (so the user is told plainly
    when they typed the wrong one), matching the phone flow's product decision;
    the per-address throttle above is what keeps enumeration abuse in check.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [EmailPerHourThrottle, ResetRequestIpThrottle]

    def throttled(self, request, wait):
        from rest_framework.exceptions import Throttled

        raise Throttled(
            detail=(
                "سقف ارسال ایمیل بازیابی برای این آدرس پر شده است. "
                f"لطفاً حدود {_fa(max(1, int(wait or 60) // 60))} دقیقه دیگر تلاش کنید."
            )
        )

    def post(self, request):
        from django.conf import settings as dj_settings

        from apps.notifications.tasks import send_password_reset_email_task

        email = str(request.data.get("email", "")).strip().lower()
        if not email or "@" not in email:
            return Response({"detail": "ایمیل معتبر نیست."}, status=400)

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            return Response(
                {"detail": "حسابی با این ایمیل ثبت نشده است."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Any older link becomes dead the moment a new one is issued.
        PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)

        token = secrets.token_urlsafe(48)
        PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=timezone.now() + timedelta(minutes=EMAIL_RESET_MINUTES),
        )
        reset_url = f"{dj_settings.FRONTEND_URL}/reset-password?token={token}"
        send_password_reset_email_task.delay(user.email, user.full_name or "", reset_url, EMAIL_RESET_MINUTES)
        return Response(
            {
                "detail": f"لینک بازیابی به {user.email} ارسال شد. "
                f"این لینک تا {_fa(EMAIL_RESET_MINUTES)} دقیقه معتبر است.",
            }
        )


class EmailPasswordResetVerifyView(APIView):
    """GET ?token=… -> is this link still usable?

    The reset page calls this on load so an expired/used link shows "expired"
    immediately, instead of presenting a password form that only fails
    once the user has already typed a new password.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def get(self, request):
        token = str(request.query_params.get("token", "")).strip()
        row = PasswordResetToken.objects.filter(token=token).first()
        if not row:
            return Response({"valid": False, "reason": "invalid"}, status=200)
        if row.is_used:
            return Response({"valid": False, "reason": "used"}, status=200)
        if timezone.now() >= row.expires_at:
            return Response({"valid": False, "reason": "expired"}, status=200)
        remaining = int((row.expires_at - timezone.now()).total_seconds())
        return Response({"valid": True, "seconds_left": max(0, remaining)})


class EmailPasswordResetConfirmView(APIView):
    """POST {token, new_password} -> validates the link and sets the password."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        token = str(request.data.get("token", "")).strip()
        new_password = request.data.get("new_password", "")

        row = PasswordResetToken.objects.filter(token=token).select_related("user").first()
        if not row or not row.is_valid:
            return Response(
                {"detail": "این لینک نامعتبر یا منقضی شده است. لطفاً دوباره درخواست دهید."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = row.user
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            return Response({"detail": " ".join(exc.messages)}, status=400)

        user.set_password(new_password)
        user.save(update_fields=["password"])
        row.is_used = True
        row.save(update_fields=["is_used"])
        return Response({"detail": "رمز عبور با موفقیت تغییر کرد."})


class ShopApprovalViewSet(viewsets.ReadOnlyModelViewSet):
    """Supplier reviews shopkeeper KYC profiles and approves/rejects them."""

    serializer_class = ShopkeeperProfileSerializer
    permission_classes = [IsSiteAdmin]

    def get_queryset(self):
        qs = ShopkeeperProfile.objects.select_related("user").prefetch_related("documents")
        state = self.request.query_params.get("status")
        if state:
            qs = qs.filter(status=state)
        return qs

    def get_serializer_class(self):
        # Expose the shop's phone alongside the profile for the panel list.
        base = ShopkeeperProfileSerializer

        class WithUser(base):  # type: ignore[misc, valid-type]
            user_id = serializers.IntegerField(source="user.id", read_only=True)
            phone = serializers.CharField(source="user.phone", read_only=True)
            full_name = serializers.CharField(source="user.full_name", read_only=True)
            user_is_approved = serializers.BooleanField(source="user.is_approved", read_only=True)

            class Meta(base.Meta):  # type: ignore[misc]
                fields = base.Meta.fields + ("user_id", "phone", "full_name", "user_is_approved")

        return WithUser

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        profile = self.get_object()
        profile.approve(reviewer=request.user)
        return Response(self.get_serializer(profile).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        profile = self.get_object()
        profile.status = ShopkeeperProfile.Status.REJECTED
        profile.review_note = request.data.get("note", "")
        profile.reviewed_by = request.user
        profile.reviewed_at = timezone.now()
        profile.save()
        return Response(self.get_serializer(profile).data)
