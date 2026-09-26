"""Revenue-share (commission) engine.

The marketplace owner takes a percentage of every sale. The percentage is not
hard-coded: the beneficiary edits it from their own panel, within a min/max
band they also control (5–20% by default).

Rate resolution for a single order line, most specific wins:
  1. a per-category rate           (CategoryCommissionRate)
  2. a per-buyer-role rate         (rate_for_shopkeeper / rate_for_customer)
  3. the global default rate       (CommissionSetting.default_rate)

Every confirmed order snapshots the resolved numbers into a CommissionEntry, so
later rate changes never rewrite history — exactly like order line prices.
"""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


def fa_digits(value):
    """Persian digits (e.g. for 12.5) — error messages should read like the rest of the UI."""
    table = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return f"{value:g}".translate(table) if isinstance(value, Decimal) else str(value).translate(table)


RATE_FIELD = dict(
    max_digits=5,
    decimal_places=2,
    validators=[
        MinValueValidator(Decimal("0")),
        MaxValueValidator(Decimal("100")),
    ],
)


class CommissionSetting(models.Model):
    """Singleton (pk=1) holding the whole revenue-share configuration."""

    beneficiary = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="commission_settings",
        verbose_name=_("حساب دریافت‌کننده پورسانت"),
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(
        _("فعال"),
        default=True,
        help_text=_("غیرفعال شود، برای سفارش‌های جدید پورسانتی ثبت نمی‌شود."),
    )

    default_rate = models.DecimalField(_("درصد پیش‌فرض"), default=Decimal("10.00"), **RATE_FIELD)
    # Optional per-buyer-type rates; blank means "use the default".
    rate_for_shopkeeper = models.DecimalField(_("درصد برای فروشگاه‌ها"), null=True, blank=True, **RATE_FIELD)
    rate_for_customer = models.DecimalField(_("درصد برای کاربران عادی"), null=True, blank=True, **RATE_FIELD)

    # The band every rate above must stay inside. The owner can widen it.
    min_rate = models.DecimalField(_("حداقل مجاز"), default=Decimal("5.00"), **RATE_FIELD)
    max_rate = models.DecimalField(_("حداکثر مجاز"), default=Decimal("20.00"), **RATE_FIELD)

    # Should a commission be recognised the moment a credit order is placed, or
    # only once the shop actually settles its invoice?
    accrue_on_credit_order = models.BooleanField(
        _("ثبت پورسانت خرید اعتباری هنگام ثبت سفارش"),
        default=True,
        help_text=_("خاموش باشد، پورسانت خرید اعتباری فقط پس از تسویه ثبت می‌شود."),
    )
    notify_on_new_commission = models.BooleanField(_("اطلاع‌رسانی پیامکی پورسانت جدید"), default=False)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("تنظیمات پورسانت")
        verbose_name_plural = _("تنظیمات پورسانت")

    def __str__(self):
        return f"پورسانت {self.default_rate}٪"

    @classmethod
    def load(cls):
        """Always work with row 1; create it with sane defaults on first use."""
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def clean(self):
        if self.min_rate > self.max_rate:
            raise ValidationError({"min_rate": _("حداقل نمی‌تواند از حداکثر بیشتر باشد.")})
        for field in ("default_rate", "rate_for_shopkeeper", "rate_for_customer"):
            value = getattr(self, field)
            if value is None:
                continue
            if not (self.min_rate <= value <= self.max_rate):
                raise ValidationError(
                    {
                        field: _("درصد باید بین %(a)s و %(b)s باشد.")
                        % {"a": fa_digits(self.min_rate), "b": fa_digits(self.max_rate)}
                    }
                )

    def rate_for_user(self, user):
        """Buyer-role rate, falling back to the global default."""
        from apps.accounts.models import User

        if user and user.role == User.Role.SHOPKEEPER and self.rate_for_shopkeeper is not None:
            return self.rate_for_shopkeeper
        if user and user.role == User.Role.CUSTOMER and self.rate_for_customer is not None:
            return self.rate_for_customer
        return self.default_rate


class CategoryCommissionRate(TimeStampedModel):
    """Per-category override — e.g. 20% on filters, 6% on tyres."""

    category = models.OneToOneField(
        "catalog.Category",
        on_delete=models.CASCADE,
        related_name="commission_rate",
        verbose_name=_("دسته‌بندی"),
    )
    rate = models.DecimalField(_("درصد"), **RATE_FIELD)

    class Meta:
        verbose_name = _("درصد پورسانت دسته‌بندی")
        verbose_name_plural = _("درصد پورسانت دسته‌بندی‌ها")

    def __str__(self):
        return f"{self.category} — {self.rate}٪"


class CommissionEntry(TimeStampedModel):
    """One settled-or-pending revenue-share row per order."""

    class Status(models.TextChoices):
        PENDING = "pending", _("در انتظار تسویه سفارش")
        EARNED = "earned", _("قطعی‌شده")
        PAID = "paid", _("پرداخت شد")
        VOID = "void", _("باطل (سفارش لغو شد)")

    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="commission",
        verbose_name=_("سفارش"),
    )
    beneficiary = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="commission_entries",
        verbose_name=_("دریافت‌کننده"),
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="generated_commissions",
        verbose_name=_("خریدار"),
    )
    buyer_role = models.CharField(_("نوع خریدار"), max_length=20, db_index=True)

    # Snapshots — immune to later rate edits.
    base_amount = models.PositiveBigIntegerField(_("مبلغ مبنا"), default=0)
    effective_rate = models.DecimalField(_("درصد اعمال‌شده"), **RATE_FIELD)
    amount = models.PositiveBigIntegerField(_("مبلغ پورسانت"), default=0)

    status = models.CharField(
        _("وضعیت"),
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    paid_at = models.DateTimeField(_("زمان پرداخت"), null=True, blank=True)
    note = models.CharField(_("یادداشت"), max_length=200, blank=True)

    class Meta:
        verbose_name = _("پورسانت")
        verbose_name_plural = _("پورسانت‌ها")
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self):
        return f"{self.order.number} — {self.amount:,} تومان"


class OrderSupplierShare(TimeStampedModel):
    """Per-order, per-supplier split — snapshotted the moment an order succeeds.

    ``CommissionEntry`` is the owner's total on the whole order; this breaks the
    same order down by supplier so each panel can answer, for every sale, «how
    much did the site owner take and how much is mine». One row per
    (order, supplier); prices are snapshots, immune to later rate/price edits.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("در انتظار تسویه سفارش")
        EARNED = "earned", _("قطعی‌شده")
        PAID = "paid", _("پرداخت شد")
        VOID = "void", _("باطل (سفارش لغو شد)")

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="supplier_shares",
        verbose_name=_("سفارش"),
    )
    supplier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sale_shares",
        verbose_name=_("تامین‌کننده"),
    )

    # Snapshots for this supplier's lines within the order.
    gross_amount = models.PositiveBigIntegerField(_("مبلغ فروش"), default=0)
    owner_commission = models.PositiveBigIntegerField(_("پورسانت مدیر سایت"), default=0)
    supplier_net = models.PositiveBigIntegerField(_("سهم تامین‌کننده"), default=0)
    effective_rate = models.DecimalField(_("درصد پورسانت"), **RATE_FIELD)

    status = models.CharField(
        _("وضعیت"),
        max_length=12,
        choices=Status.choices,
        default=Status.EARNED,
        db_index=True,
    )
    note = models.CharField(_("یادداشت"), max_length=200, blank=True)

    class Meta:
        verbose_name = _("سهم فروش تامین‌کننده")
        verbose_name_plural = _("سهم فروش تامین‌کنندگان")
        ordering = ("-created_at",)
        unique_together = ("order", "supplier")
        indexes = [models.Index(fields=["supplier", "-created_at"])]

    def __str__(self):
        return f"{self.order.number} / {self.supplier_id} — سهم {self.supplier_net:,}"
