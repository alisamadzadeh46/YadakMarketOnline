"""User, role, KYC and address models.

Five roles exist in the marketplace:
  * ADMIN      — the site owner (superuser); approves accounts and sees everything.
  * SUPPLIER   — a vendor; sells their own products, fulfils their orders and
                 may extend credit to approved shops.
  * SHOPKEEPER — an auto-parts shop buying wholesale (needs approval + KYC).
  * CUSTOMER   — a regular retail buyer; can purchase immediately.
  * PARTNER    — a revenue-share partner who earns a commission on every sale.

A shopkeeper registers, uploads KYC documents, and can only buy wholesale once
the site owner has approved the account (User.is_approved).
"""

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel

from .managers import UserManager

# Iranian mobile numbers: 09 followed by 9 digits.
iranian_phone_validator = RegexValidator(
    regex=r"^09\d{9}$",
    message="شماره موبایل باید با ۰۹ شروع شده و ۱۱ رقم باشد.",
)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = "admin", _("مدیر سایت")
        SUPPLIER = "supplier", _("تامین‌کننده")
        SHOPKEEPER = "shopkeeper", _("فروشگاه لوازم یدکی")
        CUSTOMER = "customer", _("کاربر عادی")
        # Revenue-share partner: earns a percentage of every sale and manages
        # that percentage from their own panel (see apps.commissions).
        PARTNER = "partner", _("شریک درآمدی")

    phone = models.CharField(
        _("موبایل"),
        max_length=11,
        unique=True,
        validators=[iranian_phone_validator],
    )
    email = models.EmailField(_("ایمیل"), blank=True)
    full_name = models.CharField(_("نام و نام خانوادگی"), max_length=150, blank=True)

    role = models.CharField(
        _("نقش"),
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
        db_index=True,
    )
    # Approval gate. Customers are auto-approved; shopkeepers start unapproved
    # and cannot place wholesale/credit orders until the owner confirms them.
    is_approved = models.BooleanField(
        _("تایید شده"),
        default=False,
        help_text=_("فروشگاه‌ها تا زمان تایید امکان خرید عمده ندارند."),
    )

    is_active = models.BooleanField(_("فعال"), default=True)
    is_staff = models.BooleanField(_("دسترسی به پنل مدیریت"), default=False)
    phone_verified = models.BooleanField(_("موبایل تایید شده"), default=False)

    date_joined = models.DateTimeField(_("تاریخ عضویت"), default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []  # phone + password are the only required fields

    class Meta:
        verbose_name = _("کاربر")
        verbose_name_plural = _("کاربران")

    def __str__(self):
        return f"{self.full_name or self.phone} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        # Retail customers can buy right away; approval only matters for shops.
        if self.role in (self.Role.CUSTOMER, self.Role.PARTNER) and not self.is_approved:
            self.is_approved = True
        super().save(*args, **kwargs)

    # -- Convenience role checks used by permissions and views ---------------
    @property
    def is_supplier(self):
        return self.role == self.Role.SUPPLIER

    @property
    def is_shopkeeper(self):
        return self.role == self.Role.SHOPKEEPER

    @property
    def is_partner(self):
        return self.role == self.Role.PARTNER

    @property
    def can_buy_wholesale(self):
        """Only approved shopkeepers unlock wholesale pricing and credit."""
        return self.is_shopkeeper and self.is_approved


class ShopkeeperProfile(TimeStampedModel):
    """KYC + business details for an auto-parts shop.

    The owner reviews the uploaded documents and flips `status` to APPROVED,
    which also approves the underlying user account.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("در انتظار بررسی")
        APPROVED = "approved", _("تایید شده")
        REJECTED = "rejected", _("رد شده")

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="shop_profile",
        verbose_name=_("کاربر"),
    )
    shop_name = models.CharField(_("نام فروشگاه"), max_length=200)
    owner_national_id = models.CharField(_("کد ملی مالک"), max_length=10, blank=True)
    business_license_no = models.CharField(_("شماره جواز کسب"), max_length=50, blank=True)
    province = models.CharField(_("استان"), max_length=100, blank=True)
    city = models.CharField(_("شهر"), max_length=100, blank=True)
    address = models.TextField(_("آدرس فروشگاه"), blank=True)
    landline = models.CharField(_("تلفن ثابت"), max_length=20, blank=True)

    status = models.CharField(
        _("وضعیت احراز هویت"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    review_note = models.TextField(_("یادداشت بررسی"), blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_shops",
        verbose_name=_("بررسی‌کننده"),
    )
    reviewed_at = models.DateTimeField(_("تاریخ بررسی"), null=True, blank=True)

    class Meta:
        verbose_name = _("پروفایل فروشگاه")
        verbose_name_plural = _("پروفایل فروشگاه‌ها")

    def __str__(self):
        return f"{self.shop_name} — {self.get_status_display()}"

    def approve(self, reviewer):
        """Approve KYC and unlock wholesale buying for the linked user."""
        self.status = self.Status.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save()
        self.user.role = User.Role.SHOPKEEPER
        self.user.is_approved = True
        self.user.save(update_fields=["role", "is_approved"])


def kyc_upload_path(instance, filename):
    # Under private/ so nginx refuses to serve it directly: these are national
    # ID cards and business licences. Reaching one takes a signed URL from
    # apps.core.protected. The stored name is random because the old path was
    # guessable (sequential user id + the client's own filename).
    from apps.core.uploads import opaque_name

    return f"private/kyc/{instance.profile.user_id}/{opaque_name(filename)}"


class KYCDocument(TimeStampedModel):
    """A single uploaded identity/business document for a shop profile."""

    class DocType(models.TextChoices):
        NATIONAL_CARD = "national_card", _("کارت ملی")
        BUSINESS_LICENSE = "business_license", _("جواز کسب")
        SHOP_PHOTO = "shop_photo", _("تصویر فروشگاه")
        OTHER = "other", _("سایر")

    profile = models.ForeignKey(
        ShopkeeperProfile,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name=_("پروفایل"),
    )
    doc_type = models.CharField(_("نوع مدرک"), max_length=30, choices=DocType.choices)
    file = models.FileField(_("فایل"), upload_to=kyc_upload_path)

    class Meta:
        verbose_name = _("مدرک احراز هویت")
        verbose_name_plural = _("مدارک احراز هویت")

    def __str__(self):
        return f"{self.get_doc_type_display()} — {self.profile.shop_name}"


class PhoneOTP(TimeStampedModel):
    """A short-lived SMS code, currently used for password reset.

    Codes are single-use, expire quickly and are throttled by the view; the
    code itself is stored hashed-equivalent short so leaking the table is not
    catastrophic (codes die in minutes anyway).
    """

    class Purpose(models.TextChoices):
        PASSWORD_RESET = "password_reset", _("بازیابی رمز عبور")

    phone = models.CharField(_("موبایل"), max_length=11, validators=[iranian_phone_validator], db_index=True)
    code = models.CharField(_("کد"), max_length=6)
    purpose = models.CharField(_("کاربرد"), max_length=30, choices=Purpose.choices, default=Purpose.PASSWORD_RESET)
    expires_at = models.DateTimeField(_("انقضا"))
    is_used = models.BooleanField(_("استفاده شده"), default=False)

    class Meta:
        verbose_name = _("کد یکبارمصرف")
        verbose_name_plural = _("کدهای یکبارمصرف")

    def __str__(self):
        return f"{self.phone} ({self.get_purpose_display()})"

    @property
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at


class PasswordResetToken(TimeStampedModel):
    """A single-use, 30-minute link token for email-based password reset.

    Unlike the 6-digit SMS OTP above, this is a long random string delivered
    as a clickable link, so it must be unguessable rather than merely
    short-lived — hence 43+ chars of `secrets.token_urlsafe` entropy.
    """

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
        verbose_name=_("کاربر"),
    )
    token = models.CharField(_("توکن"), max_length=100, unique=True, db_index=True)
    expires_at = models.DateTimeField(_("انقضا"))
    is_used = models.BooleanField(_("استفاده شده"), default=False)

    class Meta:
        verbose_name = _("توکن بازیابی رمز")
        verbose_name_plural = _("توکن‌های بازیابی رمز")
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user} — {'مصرف‌شده' if self.is_used else 'فعال'}"

    @property
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at


class Address(TimeStampedModel):
    """A shipping address belonging to a buyer (customer or shop)."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="addresses",
        verbose_name=_("کاربر"),
    )
    title = models.CharField(_("عنوان"), max_length=100, help_text=_("مثلا: انبار مرکزی"))
    receiver_name = models.CharField(_("نام گیرنده"), max_length=150)
    receiver_phone = models.CharField(_("موبایل گیرنده"), max_length=11, validators=[iranian_phone_validator])
    province = models.CharField(_("استان"), max_length=100)
    city = models.CharField(_("شهر"), max_length=100)
    postal_code = models.CharField(_("کد پستی"), max_length=10, blank=True)
    line = models.TextField(_("نشانی کامل"))
    # Optional pin from the map picker; shown to the supplier for delivery.
    lat = models.DecimalField(_("عرض جغرافیایی"), max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(_("طول جغرافیایی"), max_digits=9, decimal_places=6, null=True, blank=True)
    is_default = models.BooleanField(_("آدرس پیش‌فرض"), default=False)

    class Meta:
        verbose_name = _("آدرس")
        verbose_name_plural = _("آدرس‌ها")
        ordering = ("-is_default", "-created_at")

    def __str__(self):
        return f"{self.title} — {self.city}"

    def save(self, *args, **kwargs):
        # Guarantee at most one default address per user.
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
