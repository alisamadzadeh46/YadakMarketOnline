"""SMS dispatch, isolated on its own rate-limited queue.

Why a dedicated queue
---------------------
Settlement reminders and campaigns fire in bursts — a few hundred messages in
one second. Sent all at once that would (a) hammer the provider until it starts
rejecting us, and (b) starve every other background job, because the SMS calls
would occupy every worker slot waiting on the network.

So SMS lives on its own `sms` queue with a per-task rate limit. Messages line up
and drain at a steady pace; orders, invoices and image processing keep flowing
on the default queue no matter how big the SMS backlog grows. A provider outage
now delays texts instead of taking the whole background system down with it.

Failures retry with exponential backoff rather than vanishing.
"""

import logging

from celery import shared_task
from django.conf import settings

from .backends import get_sms_backend
from .models import SmsLog, mask_codes

logger = logging.getLogger(__name__)


@shared_task(
    name="notifications.send_sms",
    queue="sms",
    # Steady drain rate keeps us inside the provider's limits.
    rate_limit=getattr(settings, "SMS_RATE_LIMIT", "30/m"),
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=10,  # 10s, 20s, 40s, ...
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
    acks_late=True,
)
def send_sms(self, recipient, message, kind=SmsLog.Kind.OTHER):
    """Send one SMS and record the attempt.

    Always call via `.delay(...)` — running it inline would put a network
    round-trip in the middle of a web request.
    """
    backend = get_sms_backend()
    result = backend.send(recipient, message)
    SmsLog.objects.create(
        recipient=recipient,
        message=mask_codes(message) if kind == SmsLog.Kind.VERIFICATION else message,
        kind=kind,
        provider=getattr(settings, "SMS_PROVIDER", "console"),
        is_sent=result.get("ok", False),
        provider_ref=result.get("provider_ref", ""),
    )
    if not result.get("ok", False):
        # Raising hands the task to the retry policy above; the log row already
        # records the failed attempt for the supplier's SMS report.
        logger.warning("SMS to %s rejected by provider: %s", recipient, result.get("raw"))
        raise RuntimeError("SMS provider rejected the message")
    return result


@shared_task(name="notifications.send_bulk_sms", queue="sms")
def send_bulk_sms(recipients, message, kind=SmsLog.Kind.OTHER):
    """Fan a campaign out into one queued task per recipient.

    Enqueueing individually (rather than looping inside a single task) means the
    rate limit applies per message and one bad number cannot abort the batch.
    """
    for phone in recipients:
        send_sms.apply_async(args=[phone, message, kind], queue="sms")
    return len(recipients)


@shared_task(name="notifications.send_password_reset_email", queue="sms", max_retries=2)
def send_password_reset_email_task(to_email, name, reset_url, minutes=30):
    """Deliver the branded reset email off the request thread.

    Runs on the `sms` queue for the same reason SMS does: it is a slow external
    call and must never block an ordinary web worker.
    """
    from .emails import send_password_reset_email

    ok = send_password_reset_email(to_email=to_email, name=name, reset_url=reset_url, minutes=minutes)
    if not ok:
        logger.warning("Password reset email to %s failed", to_email)
    return ok
