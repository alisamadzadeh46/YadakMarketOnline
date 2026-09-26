"""Cart, order, order items and card-to-card payment receipt.

Payment flow (no online gateway):
  1. Buyer checks out -> Order is PENDING_PAYMENT with a `receipt_deadline`
     of now + PAYMENT_RECEIPT_WINDOW_MINUTES (default 30).
  2. Buyer uploads a bank transfer receipt  -> RECEIPT_UPLOADED.
  3. Supplier verifies the receipt           -> CONFIRMED, then SHIPPED.
  4. If no receipt arrives before the deadline, a Celery sweep cancels the
     order and returns the reserved stock (see tasks.close_expired_orders).

Credit orders (settle later) are created as CREDIT and handled in apps.suppliers.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class CheckoutSettings(models.Model):
    """Singleton (pk=1) — VAT rate and flat shipping cost, owner-editable.

    Both are snapshotted onto each Order at checkout time (see Order.tax_amount
    / shipping_cost) so a later rate change never rewrites past orders' totals.
    """

    vat_percent = models.DecimalField(
        _("درصد مالیات بر ارزش‌افزوده"),
        max_digits=5,
        decimal_places=2,
        default=10,
    )
    shipping_cost = models.PositiveBigIntegerField(_("هزینه ارسال (تومان)"), default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("تنظیمات مالی سفارش")
        verbose_name_plural = _("تنظیمات مالی سفارش")

    def __str__(self):
        return f"مالیات {self.vat_percent}٪ / ارسال {self.shipping_cost:,} تومان"

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


class Cart(TimeStampedModel):
    """A persistent, server-side cart (one open cart per user)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")

    class Meta:
        verbose_name = _("سبد خرید")
        verbose_name_plural = _("سبدهای خرید")

    @property
    def subtotal(self):
        return sum(item.line_total for item in self.items.all())


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(_("تعداد"), default=1)
    # The colour the buyer picked on the product page (one of product.colors),
    # if any. Two different colours of the same product are separate lines —
    # hence colour is part of the uniqueness below, not just an extra field.
    color = models.ForeignKey(
        "catalog.Color",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("رنگ انتخابی"),
    )

    class Meta:
        unique_together = ("cart", "product", "color")

    @property
    def unit_price(self):
        # Volume tiers make bigger cart lines cheaper per unit.
        return self.product.price_for(self.quantity)

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", _("در انتظار پرداخت")
        RECEIPT_UPLOADED = "receipt_uploaded", _("فیش آپلود شد - در انتظار تایید")
        CONFIRMED = "confirmed", _("پرداخت تایید شد")
        PROCESSING = "processing", _("در حال پردازش")
        SHIPPED = "shipped", _("ارسال شد")
        DELIVERED = "delivered", _("تحویل شد")
        CANCELED = "canceled", _("لغو شد (عدم پرداخت)")
        CREDIT = "credit", _("خرید اعتباری")

    class PaymentMethod(models.TextChoices):
        CARD_TO_CARD = "card_to_card", _("کارت به کارت")
        ONLINE = "online", _("پرداخت آنلاین")
        CREDIT = "credit", _("اعتباری")

    number = models.CharField(_("شماره سفارش"), max_length=20, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    # Address snapshot (kept even if the source address is later edited/deleted).
    ship_to_name = models.CharField(_("گیرنده"), max_length=150)
    ship_to_phone = models.CharField(_("موبایل گیرنده"), max_length=11)
    ship_to_city = models.CharField(_("شهر"), max_length=100)
    ship_to_address = models.TextField(_("نشانی"))
    # Coordinate snapshot from the chosen address (for the supplier's map).
    ship_lat = models.DecimalField(_("عرض جغرافیایی"), max_digits=9, decimal_places=6, null=True, blank=True)
    ship_lng = models.DecimalField(_("طول جغرافیایی"), max_digits=9, decimal_places=6, null=True, blank=True)

    status = models.CharField(
        _("وضعیت"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
        db_index=True,
    )
    payment_method = models.CharField(
        _("روش پرداخت"),
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CARD_TO_CARD,
    )

    subtotal = models.PositiveBigIntegerField(_("جمع کل"), default=0)
    discount_amount = models.PositiveBigIntegerField(_("تخفیف"), default=0)
    tax_amount = models.PositiveBigIntegerField(_("مالیات بر ارزش‌افزوده"), default=0)
    shipping_cost = models.PositiveBigIntegerField(_("هزینه ارسال"), default=0)
    total = models.PositiveBigIntegerField(_("مبلغ نهایی"), default=0)
    coupon_code = models.CharField(_("کد تخفیف"), max_length=40, blank=True)
    # Snapshot of a supplier coupon's owner: its discount only reduced that
    # supplier's lines (commission and supplier shares depend on it).
    discount_supplier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("تامین‌کننده صاحب کد تخفیف"),
    )

    # Card-to-card timer.
    receipt_deadline = models.DateTimeField(_("مهلت آپلود فیش"), null=True, blank=True)
    paid_at = models.DateTimeField(_("زمان تایید پرداخت"), null=True, blank=True)
    note = models.TextField(_("توضیحات"), blank=True)

    # Supplier procurement reminders: when this order was last SMS'd to the
    # supplier, so the periodic sweep knows when the next reminder is due. Cleared
    # of meaning once the supplier confirms (reminders stop then).
    supplier_reminded_at = models.DateTimeField(_("آخرین یادآوری به تامین‌کننده"), null=True, blank=True)
    supplier_reminder_count = models.PositiveSmallIntegerField(_("تعداد یادآوری تامین"), default=0)

    class Meta:
        verbose_name = _("سفارش")
        verbose_name_plural = _("سفارش‌ها")
        ordering = ("-created_at",)

    def __str__(self):
        return self.number

    def save(self, *args, **kwargs):
        if not self.number:
            # Human-friendly order number: YM + zero-padded id assigned post-save.
            super().save(*args, **kwargs)
            self.number = f"YM{self.created_at:%y%m}{self.pk:05d}"
            return super().save(update_fields=["number"])
        super().save(*args, **kwargs)

    @property
    def is_awaiting_receipt(self):
        return self.status == self.Status.PENDING_PAYMENT

    @property
    def seconds_left(self):
        """Countdown the frontend shows; 0 once expired."""
        if not self.receipt_deadline or not self.is_awaiting_receipt:
            return 0
        delta = (self.receipt_deadline - timezone.now()).total_seconds()
        return max(0, int(delta))


class OrderItem(TimeStampedModel):
    """Line item; prices are snapshotted so later catalog edits don't change history."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT)
    product_name = models.CharField(_("نام محصول"), max_length=200)
    unit_price = models.PositiveBigIntegerField(_("قیمت واحد"))
    quantity = models.PositiveIntegerField(_("تعداد"))
    # Snapshotted like product_name: the colour must keep reading correctly on
    # an old invoice even if the colour is later renamed or removed from the
    # product, so the name is copied in alongside the (nullable) live FK.
    color = models.ForeignKey(
        "catalog.Color",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("رنگ انتخابی"),
    )
    color_name = models.CharField(_("نام رنگ"), max_length=50, blank=True)

    @property
    def line_total(self):
        return self.unit_price * self.quantity


def receipt_upload_path(instance, filename):
    # Private: a bank slip carries the payer's name, card digits and amount.
    # Order numbers are sequential (YM<yymm><padded id>), so the old public
    # path was trivially enumerable.
    from apps.core.uploads import opaque_name

    return f"private/receipts/{instance.order.number}/{opaque_name(filename)}"


class PaymentReceipt(TimeStampedModel):
    """A bank-transfer receipt the buyer uploads for a card-to-card order."""

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="receipt", verbose_name=_("سفارش"))
    image = models.ImageField(_("تصویر فیش"), upload_to=receipt_upload_path)
    reference_number = models.CharField(_("شماره پیگیری"), max_length=50, blank=True)
    paid_amount = models.PositiveBigIntegerField(_("مبلغ واریزی"), null=True, blank=True)
    is_confirmed = models.BooleanField(_("تایید شده"), default=False)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_receipts",
        verbose_name=_("تاییدکننده"),
    )
    confirmed_at = models.DateTimeField(_("زمان تایید"), null=True, blank=True)

    class Meta:
        verbose_name = _("فیش واریزی")
        verbose_name_plural = _("فیش‌های واریزی")

    def __str__(self):
        return f"فیش {self.order.number}"
