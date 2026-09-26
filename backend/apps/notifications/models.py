"""Audit log of every SMS the platform sends."""

import re

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel

# Runs of four or more digits: the verification codes inside an SMS text.
_CODE_PATTERN = re.compile(r"\d{4,}")


def mask_codes(text: str) -> str:
    """Replace verification codes with asterisks so the log never reveals them."""
    return _CODE_PATTERN.sub(lambda match: "*" * len(match.group()), text)


class SmsLog(TimeStampedModel):
    class Kind(models.TextChoices):
        SETTLEMENT_REMINDER = "settlement_reminder", _("یادآوری تسویه")
        ORDER = "order", _("سفارش")
        # One-time codes: stored masked, since anyone who can read the log
        # could otherwise use them to take over the account.
        VERIFICATION = "verification", _("کد تایید")
        OTHER = "other", _("سایر")

    recipient = models.CharField(_("گیرنده"), max_length=11)
    message = models.TextField(_("متن"))
    kind = models.CharField(_("نوع"), max_length=30, choices=Kind.choices, default=Kind.OTHER)
    provider = models.CharField(_("ارائه‌دهنده"), max_length=30, blank=True)
    is_sent = models.BooleanField(_("ارسال شد"), default=False)
    provider_ref = models.CharField(_("کد پیگیری"), max_length=100, blank=True)

    class Meta:
        verbose_name = _("لاگ پیامک")
        verbose_name_plural = _("لاگ پیامک‌ها")

    def __str__(self):
        return f"{self.recipient} — {self.get_kind_display()}"
