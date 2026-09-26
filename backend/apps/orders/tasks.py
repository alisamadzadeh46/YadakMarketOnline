"""Celery tasks for the payment timer."""

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.utils import to_fa

from .models import Order
from .services import cancel_order


@shared_task(name="orders.close_expired_orders")
def close_expired_orders():
    """Cancel orders (card-to-card OR online) whose payment window elapsed
    with no confirmed payment. Runs every minute (periodic task registered in
    signals.py). Reserved stock is returned so it becomes buyable again.
    """
    from apps.notifications.models import SmsLog
    from apps.notifications.tasks import send_sms

    expired_ids = Order.objects.filter(
        status=Order.Status.PENDING_PAYMENT,
        receipt_deadline__lt=timezone.now(),
    ).values_list("pk", flat=True)
    count = 0
    for order_id in expired_ids:
        with transaction.atomic():
            # Lock the row and re-check it: a gateway callback may be confirming
            # this very order right now (it holds the same lock), and must win.
            order = (
                Order.objects.select_for_update(skip_locked=True, of=("self",))
                .select_related("user")
                .filter(pk=order_id, status=Order.Status.PENDING_PAYMENT)
                .first()
            )
            if order is None:
                continue
            cancel_order(order, restock=True)
            message = (
                f"{settings.SITE_SHORT_NAME}\nسفارش {order.number} به دلیل عدم پرداخت در مهلت "
                f"{to_fa(settings.PAYMENT_RECEIPT_WINDOW_MINUTES)} دقیقه‌ای لغو شد. "
                "در صورت تمایل می‌توانید دوباره از فروشگاه خرید کنید."
            )
            phone = order.user.phone
            transaction.on_commit(
                lambda phone=phone, message=message: send_sms.delay(phone, message, kind=SmsLog.Kind.ORDER)
            )
        count += 1
    return f"canceled {count} expired orders"
