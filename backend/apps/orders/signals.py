"""Register the recurring 'close expired orders' schedule after migrations.

Using django-celery-beat's DatabaseScheduler means the schedule lives in the DB
and can be tuned from the admin without a redeploy.
"""

from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def ensure_periodic_tasks(sender, **kwargs):
    # Only react to this app's own migrate to avoid running for every app.
    if getattr(sender, "name", "") != "apps.orders":
        return
    try:
        from django_celery_beat.models import IntervalSchedule, PeriodicTask
    except Exception:
        return

    schedule, _ = IntervalSchedule.objects.get_or_create(every=1, period=IntervalSchedule.MINUTES)
    PeriodicTask.objects.get_or_create(
        name="Close expired unpaid orders",
        defaults={"interval": schedule, "task": "orders.close_expired_orders"},
    )
