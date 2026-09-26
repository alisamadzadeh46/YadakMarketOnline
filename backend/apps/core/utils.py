"""Small shared helpers."""

from django.conf import settings

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def to_fa(value) -> str:
    """Render Latin digits as Persian ones (for SMS text and the like)."""
    return str(value).translate(_FA)


def gregorian_to_jalali(year: int, month: int, day: int) -> tuple[int, int, int]:
    """Convert a Gregorian date to the Solar Hijri (Jalali) calendar.

    Arithmetic algorithm valid for the whole supported range of ``datetime``;
    used for dates shown to Iranian users in SMS texts.
    """
    days_before_month = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
    leap_year = year + 1 if month > 2 else year
    days = (
        355666
        + 365 * year
        + (leap_year + 3) // 4
        - (leap_year + 99) // 100
        + (leap_year + 399) // 400
        + day
        + days_before_month[month - 1]
    )
    jalali_year = -1595 + 33 * (days // 12053)
    days %= 12053
    jalali_year += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jalali_year += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        return jalali_year, 1 + days // 31, 1 + days % 31
    return jalali_year, 7 + (days - 186) // 30, 1 + (days - 186) % 30


def to_jalali(value) -> str:
    """Format a date as ``1405/07/04`` in the Jalali calendar, with Persian digits."""
    year, month, day = gregorian_to_jalali(value.year, value.month, value.day)
    return to_fa(f"{year}/{month:02d}/{day:02d}")


def jalali_month_start(value):
    """The Gregorian date on which the Jalali month containing ``value`` began."""
    from datetime import timedelta

    day = value
    while gregorian_to_jalali(day.year, day.month, day.day)[2] != 1:
        day -= timedelta(days=1)
    return day


def site_host() -> str:
    """The public site address without its scheme, e.g. for SMS footers."""
    return settings.FRONTEND_URL.split("://", 1)[-1]


def site_url(path: str = "") -> str:
    """Absolute URL of a page on the public site."""
    return f"{settings.FRONTEND_URL}/{path.lstrip('/')}" if path else settings.FRONTEND_URL
