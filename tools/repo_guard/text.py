"""Text normalisation and report formatting helpers."""

from __future__ import annotations

# Persian and Arabic-Indic digits are mapped to ASCII so that a phone number
# typed as "۰۹۱۲..." is detected exactly like "0912...". Arabic letter
# variants are mapped to their Persian forms, and the zero-width non-joiner
# is treated as a regular space. Every replacement is one character for one
# character, so offsets found in the normalised text remain valid.
_NORMALISATION_TABLE = str.maketrans(
    {
        **{persian: str(index) for index, persian in enumerate("۰۱۲۳۴۵۶۷۸۹")},
        **{arabic: str(index) for index, arabic in enumerate("٠١٢٣٤٥٦٧٨٩")},
        "ي": "ی",
        "ك": "ک",
        "‌": " ",
    }
)

_MASK = "***"
_VISIBLE_PREFIX = 2


def normalize(text: str) -> str:
    """Return ``text`` with digits and letter variants in canonical form."""
    return text.translate(_NORMALISATION_TABLE)


def make_excerpt(text: str, start: int, end: int, width: int = 100) -> str:
    """Return a short excerpt of ``text`` with ``text[start:end]`` masked.

    Only the first characters of the sensitive value stay visible, so the
    report helps to locate the problem without printing the secret itself.
    """
    visible = text[start : min(end, start + _VISIBLE_PREFIX)]
    masked = f"{text[:start]}{visible}{_MASK}{text[end:]}"

    window_start = max(0, start - width // 2)
    window_end = window_start + width
    snippet = masked[window_start:window_end].strip()
    prefix = "..." if window_start > 0 else ""
    suffix = "..." if window_end < len(masked) else ""
    return f"{prefix}{snippet}{suffix}"
