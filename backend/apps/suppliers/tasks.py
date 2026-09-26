"""Supplier SMS sweeps.

  * ``send_settlement_reminders`` — daily nudge on unsettled credit invoices.
  * ``notify_supplier_new_order`` — fires the moment an order is placed.
  * ``remind_pending_orders`` — every 15 min, re-sends the new-order SMS every
    ``order_reminder_hours`` until the supplier confirms the order.

All SMS go through the rate-limited ``sms`` queue, so a burst of orders can
never flood the provider.
"""

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.notifications.models import SmsLog
from apps.notifications.tasks import send_sms
from apps.orders.models import Order

from .models import CreditInvoice, SupplierSettings

# Statuses where the money is real and the supplier genuinely has to act.
# PENDING_PAYMENT / RECEIPT_UPLOADED are deliberately NOT here: the buyer has
# not paid yet, so telling the supplier "sold" would announce a sale that
# may never complete.
ACTIVE_ORDER_STATUSES = (
    Order.Status.CONFIRMED,
    Order.Status.PROCESSING,
    Order.Status.CREDIT,
)


@shared_task(name="suppliers.send_settlement_reminders")
def send_settlement_reminders():
    today = timezone.localdate()
    sent = 0
    invoices = CreditInvoice.objects.filter(is_settled=False, reminder_sent_at__isnull=True).select_related(
        "account__supplier__supplier_settings", "account__shop"
    )
    for invoice in invoices:
        account = invoice.account
        supplier_settings = getattr(account.supplier, "supplier_settings", None)
        if supplier_settings and not supplier_settings.sms_reminders_enabled:
            continue

        days_left = (invoice.due_date - today).days
        # Fire once we are within the (inclusive) reminder window before due.
        if 0 <= days_left <= account.effective_reminder_days:
            shop = account.shop
            message = invoice.reminder_message()
            send_sms.delay(shop.phone, message, kind=SmsLog.Kind.SETTLEMENT_REMINDER)
            invoice.reminder_sent_at = timezone.now()
            invoice.save(update_fields=["reminder_sent_at"])
            sent += 1
    return f"sent {sent} settlement reminders"


def _render_sold_sms(order, supplier, items, row):
    """The «your part just sold» SMS, one clean block per line item."""
    from apps.core.utils import to_fa

    display = (row.order_notify_name if row else "") or supplier.full_name or ""
    total = sum(i.unit_price * i.quantity for i in items)

    lines = [
        settings.SITE_NAME,
        "",
        f"تامین‌کننده محترم {display}".strip(),
        f"سفارش {to_fa(order.number)} پرداخت شد.",
        "",
    ]
    for n, item in enumerate(items, 1):
        prefix = f"{to_fa(n)}) " if len(items) > 1 else ""
        lines.append(f"{prefix}{item.product_name}")
        lines.append(
            f"   تعداد {to_fa(item.quantity)} × "
            f"{to_fa(f'{item.unit_price:,}')} = {to_fa(f'{item.unit_price * item.quantity:,}')} تومان"
        )
    if len(items) > 1:
        lines.append(f"جمع سهم شما: {to_fa(f'{total:,}')} تومان")
    lines += ["", "لطفاً سفارش را در پنل خود بررسی و آماده کنید."]
    return "\n".join(lines)


@shared_task(name="suppliers.notify_supplier_new_order")
def notify_supplier_new_order(order_id):
    """Tell each supplier in the order which of THEIR parts just sold.

    An order can span several suppliers, so the lines are grouped by
    ``product.supplier`` and every supplier gets one SMS covering only their
    own items — nobody sees another supplier's sales.
    """

    order = Order.objects.filter(pk=order_id).prefetch_related("items__product__supplier").first()
    if not order or order.status not in ACTIVE_ORDER_STATUSES:
        return "order not eligible"

    # supplier -> [order items]
    by_supplier = {}
    for item in order.items.all():
        supplier = item.product.supplier
        if supplier:
            by_supplier.setdefault(supplier, []).append(item)

    if not by_supplier:
        # Ownerless products — fall back to the single main-supplier number.
        settings_row = SupplierSettings.main()
        if settings_row and settings_row.order_notify_enabled and settings_row.notify_target_phone:
            send_sms.delay(
                settings_row.notify_target_phone,
                settings_row.render_order_notice(order),
                kind=SmsLog.Kind.ORDER,
            )
        return "no per-product supplier; used main settings"

    sent = 0
    for supplier, items in by_supplier.items():
        row = SupplierSettings.objects.filter(supplier=supplier).first()
        if row and not row.order_notify_enabled:
            continue
        phone = (row.order_notify_phone if row else "") or supplier.phone
        if not phone:
            continue

        send_sms.delay(phone, _render_sold_sms(order, supplier, items, row), kind=SmsLog.Kind.ORDER)
        sent += 1

    order.supplier_reminded_at = timezone.now()
    order.supplier_reminder_count = (order.supplier_reminder_count or 0) + 1
    order.save(update_fields=["supplier_reminded_at", "supplier_reminder_count"])
    return f"notified {sent} supplier(s) for order {order.number}"


@shared_task(name="suppliers.remind_pending_orders")
def remind_pending_orders():
    """Re-send the new-order SMS for every still-unconfirmed order whose
    reminder interval has elapsed. Scheduled every 15 minutes; the per-order
    cadence is governed by ``order_reminder_hours``."""
    settings_row = SupplierSettings.main()
    if not settings_row or not settings_row.order_notify_enabled:
        return "disabled"

    hours = max(1, settings_row.order_reminder_hours or 3)
    cutoff = timezone.now() - timedelta(hours=hours)
    due = list(
        Order.objects.filter(status__in=ACTIVE_ORDER_STATUSES)
        .filter(supplier_reminded_at__isnull=False, supplier_reminded_at__lte=cutoff)
        .values_list("pk", flat=True)
    )
    for order_id in due:
        # Reuse the single-order task so each SMS is queued individually and the
        # per-order timestamp is updated atomically.
        notify_supplier_new_order.delay(order_id)
    return f"queued {len(due)} reminders"


@shared_task(name="suppliers.notify_suppliers_rare_part")
def notify_suppliers_rare_part(request_id):
    """Broadcast a new rare-part request to EVERY supplier.

    Unlike an order (which only concerns the suppliers who stock the item),
    a rare-part hunt goes out to all of them — whoever can source it replies.
    Each SMS is queued individually on the rate-limited `sms` queue.
    """
    from apps.accounts.models import User
    from apps.catalog.models import RarePartRequest
    from apps.core.utils import to_fa

    req = RarePartRequest.objects.filter(pk=request_id).first()
    if not req:
        return "request not found"

    suppliers = User.objects.filter(role=User.Role.SUPPLIER, is_active=True)
    sent = 0
    for supplier in suppliers:
        row = SupplierSettings.objects.filter(supplier=supplier).first()
        if row and not row.order_notify_enabled:
            continue
        phone = (row.order_notify_phone if row else "") or supplier.phone
        if not phone:
            continue

        display = (row.order_notify_name if row else "") or supplier.full_name or ""
        car = " ".join(x for x in (req.car_name, req.car_model) if x)
        message = (
            f"{settings.SITE_NAME}\n"
            "تامین‌کننده محترم\n"
            f"{display}\n"
            f"قطعه نایاب با نام : {req.part_name}\n"
            f"تعداد : {to_fa(req.quantity)}\n"
            f"مناسب برای : {car}\n"
            f"برند : {req.brand}\n"
            "توسط کاربری ثبت شد. لطفاً پنل خود را بررسی کنید."
        )
        send_sms.delay(phone, message, kind=SmsLog.Kind.ORDER)
        sent += 1
    return f"broadcast rare-part #{request_id} to {sent} supplier(s)"
