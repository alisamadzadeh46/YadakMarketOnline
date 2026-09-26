"""Shared abstract models reused across the project."""

from django.db import models
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    """Adds created/updated timestamps to any model that inherits it."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ("-created_at",)


class SeoModel(models.Model):
    """Reusable SEO fields for any content that needs them (products, posts).

    `focus_keyword` and `seo_score` feed the Yoast-like analysis in apps.seo.
    """

    meta_title = models.CharField(_("عنوان سئو"), max_length=70, blank=True)
    meta_description = models.CharField(_("توضیح متا"), max_length=160, blank=True)
    focus_keyword = models.CharField(_("کلمه کلیدی هدف"), max_length=100, blank=True)
    canonical_url = models.URLField(_("آدرس کنونیکال"), blank=True)
    seo_score = models.PositiveSmallIntegerField(_("امتیاز سئو"), default=0)

    class Meta:
        abstract = True
