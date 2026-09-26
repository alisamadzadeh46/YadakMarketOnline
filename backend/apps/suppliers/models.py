"""Supplier credit terms and settlement tracking.

The main supplier can extend credit to an approved shop: "take the goods now,
settle within N days". Each credit purchase becomes a CreditInvoice with a due
date. A few days before that date (configurable per account, falling back to the
supplier's default) an SMS reminder is sent automatically.
"""

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class _TemplateValues(dict):
    """Leaves unknown ``{placeholders}`` untouched instead of raising KeyError."""

    def __missing__(self, key):
        return "{" + key + "}"


def _render_template(template, **values):
    """Fill an SMS template written by the supplier.

    Templates are free text from the panel, so a typo such as ``{shpo}`` or a
    stray brace must never crash the reminder job; unknown placeholders and
    malformed templates are sent as written.
    """
    try:
        return template.format_map(_TemplateValues(values))
    except (ValueError, IndexError):
        return template


class SupplierSettings(TimeStampedModel):
    """Per-supplier configuration (there is normally one main supplier)."""

    supplier = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="supplier_settings",
        verbose_name=_("تامین‌کننده"),
    )
    # Default number of days before the due date to send the reminder SMS.
    default_reminder_days = models.PositiveSmallIntegerField(_("پیش‌فرض روزهای یادآوری قبل از سررسید"), default=2)
    sms_reminders_enabled = models.BooleanField(_("ارسال پیامک یادآوری"), default=True)
    # Card-to-card details shown to buyers on the payment page.
    card_number = models.CharField(_("شماره کارت"), max_length=20, blank=True)
    card_holder = models.CharField(_("به نام"), max_length=100, blank=True)
    account_number = models.CharField(_("شماره حساب"), max_length=30, blank=True)
    iban = models.CharField(_("شماره شبا"), max_length=26, blank=True, help_text=_("بدون IR یا با IR"))
    reminder_template = models.TextField(
        _("قالب پیامک یادآوری"),
        blank=True,
        help_text=_("متغیرها: {shop} {amount} {due} {days} {site}"),
    )

    # --- Which payment methods the storefront offers -------------------------
    # When receipt (card-to-card) is on, buyers may pay by uploading a bank
    # slip for THIS supplier's products; when off, only the online gateway is
    # offered. Off by default — the site owner (admin only, not the supplier
    # themselves) turns it on per supplier from their own panel.
    receipt_payment_enabled = models.BooleanField(_("پرداخت با فیش بانکی (کارت به کارت)"), default=False)
    online_payment_enabled = models.BooleanField(_("پرداخت آنلاین (درگاه بانکی)"), default=False)

    # --- New-order notifications to the supplier (procurement reminders) ------
    order_notify_enabled = models.BooleanField(_("پیامک سفارش جدید به تامین‌کننده"), default=True)
    order_notify_name = models.CharField(
        _("نام تامین‌کننده در پیامک"),
        max_length=100,
        blank=True,
        help_text=_("مثلا: محمدی — در پیامک «جناب آقای …» می‌آید."),
    )
    order_notify_phone = models.CharField(
        _("موبایل دریافت پیامک سفارش"),
        max_length=11,
        blank=True,
        help_text=_("خالی بماند، به موبایل حساب تامین‌کننده ارسال می‌شود."),
    )
    order_reminder_hours = models.PositiveSmallIntegerField(
        _("فاصله یادآوری تا تایید (ساعت)"),
        default=3,
        help_text=_("هر چند ساعت تا زمانی که سفارش تایید نشده، دوباره پیامک شود."),
    )
    order_notify_template = models.TextField(
        _("قالب پیامک سفارش جدید"),
        blank=True,
        help_text=_("متغیرها: {name} {items} {number} {site}"),
    )

    class Meta:
        verbose_name = _("تنظیمات تامین‌کننده")
        verbose_name_plural = _("تنظیمات تامین‌کننده")

    def __str__(self):
        return f"تنظیمات {self.supplier}"

    DEFAULT_REMINDER_TEMPLATE = (
        "فروشگاه {shop} عزیز، مبلغ {amount} تومان بابت خرید اعتباری شما تا "
        "تاریخ {due} (تا {days} روز دیگر) باید تسویه شود. {site}"
    )

    def render_reminder(self, *, shop, amount, due, days):
        template = self.reminder_template or self.DEFAULT_REMINDER_TEMPLATE
        return _render_template(template, shop=shop, amount=amount, due=due, days=days, site=settings.SITE_SHORT_NAME)

    # -- New-order notification helpers --------------------------------------

    DEFAULT_ORDER_TEMPLATE = (
        "تامین کننده محترم، جناب آقای {name}\n{items}\nثبت شد. لطفا هرچه زودتر به تامین اقدام فرمایید.\nبا تشکر\n{site}"
    )

    def render_order_notice(self, order):
        """Render the new-order SMS for an order, listing each part + quantity."""
        from apps.core.utils import to_fa  # local import to avoid cycles

        lines = []
        for item in order.items.all():
            lines.append(f"نام قطعه : {item.product_name}\nتعداد : {to_fa(item.quantity)}")
        template = self.order_notify_template or self.DEFAULT_ORDER_TEMPLATE
        return _render_template(
            template,
            name=self.order_notify_name or "",
            items="\n".join(lines),
            number=order.number,
            site=settings.SITE_NAME,
        )

    @property
    def notify_target_phone(self):
        return self.order_notify_phone or self.supplier.phone

    @classmethod
    def main(cls):
        """Settings row that drives supplier notifications. Anchored to the main
        supplier user if one exists, otherwise to the site owner (admin) so the
        panel still has a row to edit and `order_notify_phone` can target the
        real supplier's number even before a supplier account is created."""
        from apps.accounts.models import User

        anchor = (
            User.objects.filter(role=User.Role.SUPPLIER).order_by("id").first()
            or User.objects.filter(is_superuser=True).order_by("id").first()
            or User.objects.filter(role=User.Role.ADMIN).order_by("id").first()
        )
        if not anchor:
            return None
        return cls.objects.get_or_create(supplier=anchor)[0]

    @classmethod
    def bank_details(cls):
        """The settings row holding the card buyers transfer to, or None.

        The marketplace collects every payment and later pays each supplier
        their share (see apps.commissions), so card-to-card transfers go to the
        site owner's card, entered on the owner's settings page. A single-supplier
        install may still keep the card on that supplier's row, where it is
        unambiguous; with several suppliers, a supplier's card is never shown.
        """
        from django.db.models import Q

        from apps.accounts.models import User

        with_card = cls.objects.exclude(card_number="").order_by("id")
        owner_row = with_card.filter(Q(supplier__is_superuser=True) | Q(supplier__role=User.Role.ADMIN)).first()
        if owner_row:
            return owner_row
        suppliers = list(User.objects.filter(role=User.Role.SUPPLIER).values_list("id", flat=True)[:2])
        if len(suppliers) == 1:
            return with_card.filter(supplier_id=suppliers[0]).first()
        return None


class CreditAccount(TimeStampedModel):
    """Credit relationship between the supplier and one shop."""

    supplier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="granted_credit_accounts",
        verbose_name=_("تامین‌کننده"),
    )
    shop = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="credit_accounts",
        verbose_name=_("فروشگاه"),
    )
    credit_limit = models.PositiveBigIntegerField(_("سقف اعتبار (تومان)"), default=0)
    # How long the shop has to settle each credit purchase (e.g. 7 or 30 days).
    settlement_days = models.PositiveSmallIntegerField(_("مهلت تسویه (روز)"), default=7)
    # Optional override of the supplier's default reminder lead time.
    reminder_days = models.PositiveSmallIntegerField(
        _("روزهای یادآوری قبل از سررسید"),
        null=True,
        blank=True,
        help_text=_("خالی = استفاده از پیش‌فرض تامین‌کننده"),
    )
    is_active = models.BooleanField(_("فعال"), default=True)

    class Meta:
        verbose_name = _("حساب اعتباری")
        verbose_name_plural = _("حساب‌های اعتباری")
        unique_together = ("supplier", "shop")

    def __str__(self):
        return f"{self.shop} — سقف {self.credit_limit:,}"

    @property
    def effective_reminder_days(self):
        if self.reminder_days is not None:
            return self.reminder_days
        supplier_settings = getattr(self.supplier, "supplier_settings", None)
        if supplier_settings:
            return supplier_settings.default_reminder_days
        return settings.DEFAULT_SETTLEMENT_REMINDER_DAYS

    @property
    def outstanding(self):
        """Sum of unsettled credit invoices."""
        return self.invoices.filter(is_settled=False).aggregate(total=models.Sum("amount"))["total"] or 0

    @property
    def available_credit(self):
        return max(0, self.credit_limit - self.outstanding)

    @classmethod
    def active_for(cls, shop, *, lock=False):
        """The shop's active credit account (the oldest one if there are several)."""
        queryset = cls.objects.filter(shop=shop, is_active=True).order_by("id")
        if lock:
            queryset = queryset.select_for_update()
        return queryset.first()


class CreditInvoice(TimeStampedModel):
    """A single credit purchase that must be settled by `due_date`."""

    account = models.ForeignKey(
        CreditAccount, on_delete=models.CASCADE, related_name="invoices", verbose_name=_("حساب اعتباری")
    )
    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="credit_invoice",
        null=True,
        blank=True,
        verbose_name=_("سفارش"),
    )
    amount = models.PositiveBigIntegerField(_("مبلغ"))
    issued_at = models.DateTimeField(_("تاریخ صدور"), default=timezone.now)
    due_date = models.DateField(_("سررسید"), db_index=True)

    is_settled = models.BooleanField(_("تسویه شده"), default=False)
    settled_at = models.DateTimeField(_("تاریخ تسویه"), null=True, blank=True)
    reminder_sent_at = models.DateTimeField(_("زمان ارسال یادآوری"), null=True, blank=True)

    class Meta:
        verbose_name = _("فاکتور اعتباری")
        verbose_name_plural = _("فاکتورهای اعتباری")
        ordering = ("due_date",)

    def __str__(self):
        return f"فاکتور {self.amount:,} — سررسید {self.due_date}"

    @property
    def days_to_due(self):
        # Local (Tehran) date: a UTC date is still "yesterday" until 03:30.
        return (self.due_date - timezone.localdate()).days

    @property
    def is_overdue(self):
        return not self.is_settled and self.days_to_due < 0

    @property
    def shop_display_name(self):
        shop = self.account.shop
        return getattr(getattr(shop, "shop_profile", None), "shop_name", "") or shop.full_name

    def reminder_message(self):
        """Settlement reminder SMS, rendered with the supplier's own template."""
        from apps.core.utils import to_fa, to_jalali

        supplier_settings = getattr(self.account.supplier, "supplier_settings", None) or SupplierSettings()
        return supplier_settings.render_reminder(
            shop=self.shop_display_name,
            amount=to_fa(f"{self.amount:,}"),
            due=to_jalali(self.due_date),
            days=to_fa(max(0, self.days_to_due)),
        )

    def settle(self):
        self.is_settled = True
        self.settled_at = timezone.now()
        self.save(update_fields=["is_settled", "settled_at"])

    @classmethod
    def create_for_order(cls, order):
        """Create a credit invoice from a CREDIT order, if the shop has an
        active credit account. Returns the invoice or None."""
        account = CreditAccount.active_for(order.user)
        if not account:
            return None
        due = timezone.localdate() + timedelta(days=account.settlement_days)
        return cls.objects.create(account=account, order=order, amount=order.total, due_date=due)
