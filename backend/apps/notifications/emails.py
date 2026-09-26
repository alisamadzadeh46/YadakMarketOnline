"""Branded transactional emails (RTL, on-brand purple/orange, inline CSS).

Email clients strip <style> blocks and ignore webfonts, so everything here is
inline-styled and falls back to Tahoma — the safest Persian-capable font that
ships with Windows/macOS mail clients.
"""

import logging
from html import escape

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from apps.core.utils import to_fa

logger = logging.getLogger(__name__)

PURPLE = "#5B2E9E"
PURPLE_DEEP = "#3A1C6E"
ORANGE = "#F26A1B"
INK = "#211A33"
MUTED = "#8B85A0"
LINE = "#EBE6F4"
PAPER = "#F5F1FB"

FONT = "Tahoma, 'Segoe UI', Arial, sans-serif"


def password_reset_html(*, name: str, reset_url: str, minutes: int = 30) -> str:
    """Full HTML body for the «forgot password» email.

    ``name`` is chosen by the user, so every interpolated value is escaped.
    """
    greeting = f"سلام {escape(name)} عزیز،" if name else "سلام،"
    site_name = escape(settings.SITE_NAME)
    tagline = escape(settings.SITE_TAGLINE)
    footer_address = f"{site_name} — {escape(settings.SITE_ADDRESS)}" if settings.SITE_ADDRESS else site_name
    reset_url = escape(reset_url, quote=True)
    return f"""\
<!doctype html>
<html dir="rtl" lang="fa">
<body style="margin:0;padding:0;background:{PAPER};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         style="background:{PAPER};padding:28px 12px;font-family:{FONT};">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
             style="max-width:560px;background:#ffffff;border-radius:18px;overflow:hidden;
                    border:1px solid {LINE};box-shadow:0 8px 28px -18px rgba(58,28,110,.4);">

        <!-- header -->
        <tr><td style="background:linear-gradient(130deg,{PURPLE_DEEP},{PURPLE});padding:28px 26px;text-align:center;">
          <div style="font-size:22px;font-weight:bold;color:#ffffff;letter-spacing:-.3px;">{site_name}</div>
          <div style="font-size:12px;color:#D9CDF2;margin-top:6px;">{tagline}</div>
        </td></tr>

        <!-- lock badge -->
        <tr><td style="padding:30px 26px 0;text-align:center;">
          <div style="width:64px;height:64px;line-height:64px;border-radius:18px;margin:0 auto;
                      background:{PAPER};border:1px solid {LINE};font-size:30px;">&#128273;</div>
        </td></tr>

        <!-- body -->
        <tr><td style="padding:18px 30px 8px;text-align:right;">
          <div style="font-size:17px;font-weight:bold;color:{INK};margin-bottom:12px;">{greeting}</div>
          <div style="font-size:14px;color:{INK};line-height:2;">
            درخواست بازیابی رمز عبور برای حساب شما در <b>{site_name}</b> ثبت شد.
            برای انتخاب رمز عبور جدید، روی دکمه زیر بزنید:
          </div>
        </td></tr>

        <!-- CTA -->
        <tr><td style="padding:22px 30px;text-align:center;">
          <a href="{reset_url}"
             style="display:inline-block;background:{ORANGE};color:#ffffff;text-decoration:none;
                    font-size:15px;font-weight:bold;padding:15px 38px;border-radius:12px;">
            تغییر رمز عبور
          </a>
        </td></tr>

        <!-- expiry note -->
        <tr><td style="padding:0 30px 6px;text-align:right;">
          <div style="background:{PAPER};border:1px solid {LINE};border-radius:12px;padding:13px 16px;
                      font-size:12.5px;color:{INK};line-height:1.9;">
            &#9200; این لینک تا <b>{to_fa(minutes)} دقیقه</b> معتبر است و فقط <b>یک بار</b> قابل استفاده است.
          </div>
        </td></tr>

        <!-- fallback link -->
        <tr><td style="padding:16px 30px 6px;text-align:right;">
          <div style="font-size:12px;color:{MUTED};line-height:1.9;">
            اگر دکمه کار نکرد، این آدرس را در مرورگر کپی کنید:
          </div>
          <div style="font-size:11.5px;color:{PURPLE};word-break:break-all;
                      direction:ltr;text-align:left;margin-top:6px;">
            {reset_url}
          </div>
        </td></tr>

        <!-- security note -->
        <tr><td style="padding:16px 30px 26px;text-align:right;">
          <div style="border-top:1px solid {LINE};padding-top:14px;font-size:12px;color:{MUTED};line-height:1.9;">
            اگر شما این درخواست را ثبت نکرده‌اید، این ایمیل را نادیده بگیرید —
            رمز عبور فعلی شما بدون تغییر باقی می‌ماند.
          </div>
        </td></tr>

        <!-- footer -->
        <tr><td style="background:{PAPER};padding:16px 26px;text-align:center;border-top:1px solid {LINE};">
          <div style="font-size:11.5px;color:{MUTED};line-height:1.9;">
            {footer_address}<br>
            این یک ایمیل خودکار است؛ لطفاً به آن پاسخ ندهید.
          </div>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def password_reset_text(*, name: str, reset_url: str, minutes: int = 30) -> str:
    """Plain-text alternative for clients that refuse HTML."""
    greeting = f"سلام {name} عزیز،" if name else "سلام،"
    return (
        f"{greeting}\n\n"
        f"درخواست بازیابی رمز عبور برای حساب شما در {settings.SITE_NAME} ثبت شد.\n"
        "برای انتخاب رمز عبور جدید، آدرس زیر را باز کنید:\n\n"
        f"{reset_url}\n\n"
        f"این لینک تا {to_fa(minutes)} دقیقه معتبر است و فقط یک بار قابل استفاده است.\n\n"
        "اگر شما این درخواست را ثبت نکرده‌اید، این ایمیل را نادیده بگیرید.\n\n"
        f"— {settings.SITE_NAME}"
    )


def send_password_reset_email(*, to_email: str, name: str, reset_url: str, minutes: int = 30) -> bool:
    """Send the reset email. Returns True on success; never raises."""
    try:
        msg = EmailMultiAlternatives(
            subject=f"بازیابی رمز عبور — {settings.SITE_NAME}",
            body=password_reset_text(name=name, reset_url=reset_url, minutes=minutes),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        msg.attach_alternative(password_reset_html(name=name, reset_url=reset_url, minutes=minutes), "text/html")
        msg.send(fail_silently=False)
        return True
    except Exception:
        logger.exception("Password reset email to %s failed", to_email)
        return False
