"""Create credit invoices for credit orders, and register the daily reminder."""

from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from apps.orders.models import Order

from .models import CreditInvoice


@receiver(post_save, sender=Order)
def create_credit_invoice(sender, instance, created, **kwargs):
    # When a credit order is placed, open an invoice with a due date derived
    # from the shop's credit account (no-op if the shop has no active account).
    if instance.status == Order.Status.CREDIT and not hasattr(instance, "credit_invoice"):
        CreditInvoice.create_for_order(instance)


@receiver(post_migrate)
def ensure_reminder_schedule(sender, **kwargs):
    if getattr(sender, "name", "") != "apps.suppliers":
        return
    try:
        from django_celery_beat.models import (
            CrontabSchedule,
            IntervalSchedule,
            PeriodicTask,
        )
    except Exception:
        return
    # Run every day at 10:00 (Tehran time, per CELERY_TIMEZONE).
    schedule, _ = CrontabSchedule.objects.get_or_create(minute="0", hour="10")
    PeriodicTask.objects.get_or_create(
        name="Send settlement reminders",
        defaults={"crontab": schedule, "task": "suppliers.send_settlement_reminders"},
    )

    # Re-check unconfirmed orders every 15 minutes; the task itself decides which
    # are actually due based on the configured order_reminder_hours.
    every_15, _ = IntervalSchedule.objects.get_or_create(every=15, period=IntervalSchedule.MINUTES)
    PeriodicTask.objects.get_or_create(
        name="Remind supplier of pending orders",
        defaults={"interval": every_15, "task": "suppliers.remind_pending_orders"},
    )
