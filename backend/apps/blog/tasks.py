"""Async notifications for the blog."""

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from apps.core.utils import site_url


@shared_task(name="blog.notify_subscribers")
def notify_subscribers(post_id):
    """Email every active newsletter subscriber about a newly published post."""
    from apps.cms.models import NewsletterSubscriber

    from .models import Post

    post = Post.objects.filter(id=post_id, status=Post.Status.PUBLISHED).first()
    if not post:
        return "post not found or not published"

    emails = list(NewsletterSubscriber.objects.filter(is_active=True).values_list("email", flat=True))
    if not emails:
        return "no subscribers"

    subject = f"مقاله جدید {settings.SITE_SHORT_NAME}: {post.title}"
    body = (
        f"{post.title}\n\n{post.excerpt or ''}\n\n"
        f"مطالعه مقاله: {site_url(f'blog/{post.slug}')}\n\n"
        "برای لغو عضویت به سایت مراجعه کنید."
    )
    # One email per recipient keeps addresses private (no exposed CC list).
    for email in emails:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=True)
    return f"notified {len(emails)} subscribers"
