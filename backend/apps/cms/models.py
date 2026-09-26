"""Home-page slider slides, managed by the main supplier from their panel."""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class NewsletterSubscriber(TimeStampedModel):
    """An email that receives a notification whenever a post is published."""

    email = models.EmailField(_("ایمیل"), unique=True)
    is_active = models.BooleanField(_("فعال"), default=True)

    class Meta:
        verbose_name = _("مشترک خبرنامه")
        verbose_name_plural = _("مشترکین خبرنامه")

    def __str__(self):
        return self.email


class ContactMessage(TimeStampedModel):
    """A message submitted from the contact-us page."""

    name = models.CharField(_("نام"), max_length=150)
    phone = models.CharField(_("موبایل"), max_length=20, blank=True)
    email = models.EmailField(_("ایمیل"), blank=True)
    subject = models.CharField(_("موضوع"), max_length=200)
    message = models.TextField(_("پیام"))
    is_read = models.BooleanField(_("خوانده شده"), default=False)

    class Meta:
        verbose_name = _("پیام تماس")
        verbose_name_plural = _("پیام‌های تماس")

    def __str__(self):
        return f"{self.name} — {self.subject}"


class Slide(TimeStampedModel):
    badge = models.CharField(_("برچسب کوچک"), max_length=100, blank=True)
    title = models.CharField(_("عنوان"), max_length=200)
    highlight = models.CharField(
        _("بخش نارنجی عنوان"),
        max_length=200,
        blank=True,
        help_text=_("این بخش با رنگ نارنجی در خط دوم نمایش داده می‌شود."),
    )
    text = models.TextField(_("متن"), blank=True)
    image = models.ImageField(_("تصویر"), upload_to="slides/", blank=True, null=True)
    button_text = models.CharField(_("متن دکمه"), max_length=60, blank=True)
    button_link = models.CharField(_("لینک دکمه"), max_length=200, blank=True)
    order = models.PositiveSmallIntegerField(_("ترتیب"), default=0)
    is_active = models.BooleanField(_("فعال"), default=True)

    class Meta:
        verbose_name = _("اسلاید")
        verbose_name_plural = _("اسلایدر صفحه اصلی")
        ordering = ("order", "id")

    def __str__(self):
        return self.title
