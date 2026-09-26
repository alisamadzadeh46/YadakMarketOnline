"""Blog: categories and posts with built-in SEO fields."""

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.core.models import SeoModel, TimeStampedModel


class BlogCategory(TimeStampedModel):
    name = models.CharField(_("نام دسته"), max_length=100)
    slug = models.SlugField(_("اسلاگ"), max_length=120, unique=True, allow_unicode=True)

    class Meta:
        verbose_name = _("دسته‌بندی بلاگ")
        verbose_name_plural = _("دسته‌بندی‌های بلاگ")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class Post(SeoModel, TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", _("پیش‌نویس")
        PUBLISHED = "published", _("منتشر شده")

    title = models.CharField(_("عنوان"), max_length=200)
    slug = models.SlugField(_("اسلاگ"), max_length=220, unique=True, allow_unicode=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="posts",
        verbose_name=_("نویسنده"),
    )
    category = models.ForeignKey(
        BlogCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
        verbose_name=_("دسته‌بندی"),
    )
    cover = models.ImageField(_("تصویر شاخص"), upload_to="blog/", blank=True, null=True)
    excerpt = models.CharField(_("خلاصه"), max_length=300, blank=True)
    body = models.TextField(_("متن مقاله"))

    status = models.CharField(_("وضعیت"), max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True)
    published_at = models.DateTimeField(_("تاریخ انتشار"), null=True, blank=True)
    views = models.PositiveIntegerField(_("بازدید"), default=0)

    class Meta:
        verbose_name = _("مقاله")
        verbose_name_plural = _("مقالات")
        ordering = ("-published_at", "-created_at")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    @property
    def reading_time(self):
        # ~200 words/minute; at least 1 minute.
        words = len(self.body.split())
        return max(1, round(words / 200))


class PostView(models.Model):
    """One row per unique visitor IP per post — the source of truth for the
    view counter, so refreshes and double-fired requests never inflate it."""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="view_hits", verbose_name=_("مقاله"))
    ip = models.GenericIPAddressField(_("آی‌پی"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("بازدید مقاله")
        verbose_name_plural = _("بازدیدهای مقاله")
        unique_together = ("post", "ip")

    def __str__(self):
        return f"{self.post_id} ← {self.ip}"
