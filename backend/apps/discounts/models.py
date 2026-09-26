"""Discount codes applied at checkout.

A coupon created by the site owner is site-wide. A coupon created by a
supplier only discounts that supplier's own products, so no supplier can give
away another supplier's goods.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class Coupon(TimeStampedModel):
    class Kind(models.TextChoices):
        PERCENT = "percent", _("درصدی")
        FIXED = "fixed", _("مبلغ ثابت")

    code = models.CharField(_("کد تخفیف"), max_length=40, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="coupons",
        verbose_name=_("تامین‌کننده"),
        help_text=_("خالی = کل سایت؛ در غیر این صورت فقط روی کالاهای همین تامین‌کننده اعمال می‌شود."),
    )
    kind = models.CharField(_("نوع"), max_length=10, choices=Kind.choices, default=Kind.PERCENT)
    value = models.PositiveBigIntegerField(_("مقدار"), help_text=_("درصد یا تومان"))
    max_discount = models.PositiveBigIntegerField(
        _("سقف تخفیف (تومان)"), null=True, blank=True, help_text=_("فقط برای نوع درصدی")
    )
    min_order_amount = models.PositiveBigIntegerField(_("حداقل مبلغ سفارش"), default=0)

    usage_limit = models.PositiveIntegerField(_("سقف کل استفاده"), null=True, blank=True)
    used_count = models.PositiveIntegerField(_("تعداد استفاده‌شده"), default=0)
    per_user_limit = models.PositiveIntegerField(_("سقف استفاده هر کاربر"), default=1)

    valid_from = models.DateTimeField(_("معتبر از"), default=timezone.now)
    valid_to = models.DateTimeField(_("معتبر تا"))
    is_active = models.BooleanField(_("فعال"), default=True)

    class Meta:
        verbose_name = _("کد تخفیف")
        verbose_name_plural = _("کدهای تخفیف")

    def __str__(self):
        return self.code

    def eligible_amount(self, lines):
        """The part of an order this coupon applies to.

        ``lines`` yields ``(supplier_id, line_total)`` pairs.
        """
        return sum(total for supplier_id, total in lines if self.owner_id is None or supplier_id == self.owner_id)

    def discount_for(self, amount):
        """Money discount this coupon yields for the given order amount."""
        if self.kind == self.Kind.PERCENT:
            raw = amount * self.value // 100
            return min(raw, self.max_discount) if self.max_discount else raw
        return min(self.value, amount)

    def validate_for(self, user, amount):
        """Raise ValueError with a Persian reason if the coupon can't be used."""
        now = timezone.now()
        if not self.is_active:
            raise ValueError("این کد تخفیف غیرفعال است.")
        if not (self.valid_from <= now <= self.valid_to):
            raise ValueError("این کد تخفیف منقضی شده است.")
        if amount <= 0:
            raise ValueError("این کد تخفیف برای کالاهای سبد خرید شما معتبر نیست.")
        if amount < self.min_order_amount:
            raise ValueError("مبلغ سفارش برای این کد کافی نیست.")
        if self.usage_limit and self.used_count >= self.usage_limit:
            raise ValueError("ظرفیت استفاده از این کد پر شده است.")
        used_by_user = self.redemptions.filter(user=user).count()
        if used_by_user >= self.per_user_limit:
            raise ValueError("شما قبلا از این کد استفاده کرده‌اید.")
        return True


class CouponRedemption(TimeStampedModel):
    """Records each successful use so per-user limits can be enforced."""

    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="redemptions", verbose_name=_("کد تخفیف"))
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="coupon_uses", verbose_name=_("کاربر")
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="coupon_redemptions",
        null=True,
        blank=True,
        verbose_name=_("سفارش"),
    )
    amount = models.PositiveBigIntegerField(_("مبلغ تخفیف"))

    class Meta:
        verbose_name = _("استفاده از کد")
        verbose_name_plural = _("استفاده‌ها از کد")
