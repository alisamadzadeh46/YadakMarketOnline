"""Online payment gateway (BitPay / ZarinPal) configuration and transaction log.

Design mirrors ``apps.commissions.CommissionSetting``: a singleton settings row
the owner edits from their own panel, holding the merchant credentials, plus a
per-attempt log row so every redirect-and-callback round trip is auditable and
replay-safe (a gateway may hit the callback more than once).
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class PaymentGatewaySettings(models.Model):
    """Singleton (pk=1) — which gateway is live and its merchant credentials."""

    class Gateway(models.TextChoices):
        NONE = "none", _("غیرفعال")
        BITPAY = "bitpay", _("بیت‌پی")
        ZARINPAL = "zarinpal", _("زرین‌پال")

    active_gateway = models.CharField(
        _("درگاه پیش‌فرض"),
        max_length=10,
        choices=Gateway.choices,
        default=Gateway.NONE,
        help_text=_("درگاهی که هنگام پرداخت از قبل انتخاب شده است."),
    )

    bitpay_api_key = models.CharField(_("کد API بیت‌پی"), max_length=100, blank=True)
    bitpay_sandbox = models.BooleanField(
        _("حالت آزمایشی بیت‌پی"),
        default=False,
        help_text=_("فعال باشد، تراکنش‌ها واقعی نیستند (محیط تست بیت‌پی)."),
    )
    bitpay_enabled = models.BooleanField(
        _("نمایش بیت‌پی به خریدار"),
        default=True,
        help_text=_("اگر خاموش باشد، بیت‌پی در صفحه پرداخت به خریدار پیشنهاد نمی‌شود."),
    )

    zarinpal_merchant_id = models.CharField(_("مرچنت کد زرین‌پال"), max_length=100, blank=True)
    zarinpal_sandbox = models.BooleanField(
        _("حالت آزمایشی زرین‌پال"),
        default=False,
        help_text=_("فعال باشد، درگاه sandbox زرین‌پال استفاده می‌شود."),
    )
    zarinpal_enabled = models.BooleanField(
        _("نمایش زرین‌پال به خریدار"),
        default=True,
        help_text=_("اگر خاموش باشد، زرین‌پال در صفحه پرداخت به خریدار پیشنهاد نمی‌شود."),
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("تنظیمات درگاه پرداخت")
        verbose_name_plural = _("تنظیمات درگاه پرداخت")

    def __str__(self):
        return f"درگاه: {self.get_active_gateway_display()}"

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def has_credentials(self, gateway):
        if gateway == self.Gateway.BITPAY:
            return bool(self.bitpay_api_key)
        if gateway == self.Gateway.ZARINPAL:
            return bool(self.zarinpal_merchant_id)
        return False

    @property
    def available_gateways(self):
        """Gateways the buyer may actually pick: switched on AND holding creds.

        The owner can keep credentials on file for a gateway they've toggled
        off, so both conditions have to be checked — never just the flag.
        """
        out = []
        for gateway, enabled in (
            (self.Gateway.BITPAY, self.bitpay_enabled),
            (self.Gateway.ZARINPAL, self.zarinpal_enabled),
        ):
            if enabled and self.has_credentials(gateway):
                out.append(gateway)
        return out

    @property
    def default_gateway(self):
        """Which option is preselected — the owner's pick when it's usable."""
        available = self.available_gateways
        if self.active_gateway in available:
            return self.active_gateway
        return available[0] if available else self.Gateway.NONE

    @property
    def is_configured(self):
        return bool(self.available_gateways)


class PaymentTransaction(TimeStampedModel):
    """One redirect-to-gateway attempt for an order (an order may retry)."""

    class Status(models.TextChoices):
        PENDING = "pending", _("در انتظار پرداخت")
        SUCCESS = "success", _("موفق")
        FAILED = "failed", _("ناموفق")

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="payment_transactions",
        verbose_name=_("سفارش"),
    )
    gateway = models.CharField(_("درگاه"), max_length=10, choices=PaymentGatewaySettings.Gateway.choices)
    amount = models.PositiveBigIntegerField(_("مبلغ (تومان)"))

    # bitpay: id_get (returned at request time) + trans_id (returned at callback)
    # zarinpal: Authority (both request & callback)
    authority = models.CharField(_("شناسه پرداخت درگاه"), max_length=100, db_index=True, blank=True)
    trans_id = models.CharField(_("شماره تراکنش بیت‌پی"), max_length=100, blank=True)
    ref_id = models.CharField(_("شماره پیگیری بانک"), max_length=100, blank=True)
    card_number = models.CharField(_("شماره کارت پرداخت‌کننده"), max_length=30, blank=True)

    status = models.CharField(
        _("وضعیت"),
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    raw_response = models.JSONField(_("پاسخ خام درگاه"), null=True, blank=True)

    class Meta:
        verbose_name = _("تراکنش پرداخت")
        verbose_name_plural = _("تراکنش‌های پرداخت")
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["order", "-created_at"])]

    def __str__(self):
        return f"{self.order.number} — {self.get_gateway_display()} — {self.get_status_display()}"
