"""Checks that confirm a pattern match really is sensitive data.

Regular expressions alone produce too many false positives (version numbers,
timestamps, form labels...). The helpers below verify checksums and filter
out obvious placeholders before a match is reported.
"""

from __future__ import annotations

import ipaddress
import re

# Substrings that mark a value as a documented placeholder rather than a
# real credential, e.g. "change-me", "<your-api-key>" or "{{ token }}".
_PLACEHOLDER_HINTS = (
    "change",
    "example",
    "your",
    "xxx",
    "placeholder",
    "dummy",
    "sample",
    "fake",
    "password",
    "secret",
    "<",
    ">",
    "{",
    "}",
    "***",
    "...",
)

_ASCENDING_DIGITS = "01234567890123456789"
_DESCENDING_DIGITS = _ASCENDING_DIGITS[::-1]

_EMAIL_ALLOWED_DOMAINS = frozenset(
    {
        "example.com",
        "example.org",
        "example.net",
        "localhost",
        "test",
        "invalid",
        "users.noreply.github.com",
    }
)
_EMAIL_LOOKALIKE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".css", ".js")

_NON_DIGITS = re.compile(r"\D")


def digits_only(value: str) -> str:
    """Strip everything except ASCII digits from ``value``."""
    return _NON_DIGITS.sub("", value)


def is_placeholder(value: str) -> bool:
    """Return ``True`` when ``value`` is clearly not a real secret."""
    lowered = value.lower()
    if any(hint in lowered for hint in _PLACEHOLDER_HINTS):
        return True
    # Values made of a single repeated character ("xxxxxx", "000000").
    return len(set(lowered)) <= 1


def is_dummy_number(digits: str) -> bool:
    """Return ``True`` for obviously fake numbers such as 09120000000."""
    tail = digits[-7:]
    return len(set(tail)) == 1 or tail in _ASCENDING_DIGITS or tail in _DESCENDING_DIGITS


def is_valid_national_id(value: str) -> bool:
    """Validate the checksum of an Iranian national identification number."""
    if len(value) != 10 or not value.isdigit() or len(set(value)) == 1:
        return False
    total = sum(int(value[index]) * (10 - index) for index in range(9))
    remainder = total % 11
    expected = remainder if remainder < 2 else 11 - remainder
    return expected == int(value[9])


def passes_luhn(number: str) -> bool:
    """Validate a payment card number with the Luhn algorithm."""
    if not number.isdigit() or len(set(number)) <= 2:
        return False
    checksum = 0
    for index, char in enumerate(reversed(number)):
        digit = int(char)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def is_valid_iban(value: str) -> bool:
    """Validate an IBAN (such as an Iranian Sheba number) with ISO 7064 mod 97."""
    compact = value.replace(" ", "").upper()
    if len(compact) < 15 or not compact.isalnum():
        return False
    rearranged = compact[4:] + compact[:4]
    numeric = "".join(str(int(char, 36)) for char in rearranged)
    return int(numeric) % 97 == 1


def is_public_ip(value: str) -> bool:
    """Return ``True`` for globally routable IP addresses (real servers)."""
    try:
        return ipaddress.ip_address(value).is_global
    except ValueError:
        return False


def is_real_email(address: str) -> bool:
    """Return ``True`` for addresses that are not documentation examples."""
    local_part, _, domain = address.rpartition("@")
    domain = domain.lower()
    if domain.endswith(_EMAIL_LOOKALIKE_SUFFIXES):
        # Asset names such as "logo@2x.png" look like e-mail addresses.
        return False
    if any(domain == allowed or domain.endswith(f".{allowed}") for allowed in _EMAIL_ALLOWED_DOMAINS):
        return False
    if local_part.lower() == "git":
        # SSH remotes such as git@github.com
        return False
    return not is_placeholder(local_part)
