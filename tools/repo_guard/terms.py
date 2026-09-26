"""Restricted term matching.

Two sources of restricted terms are combined:

* Built-in terms, stored as SHA-256 digests of lowercase word sequences, so
  the list itself never places those words in the repository. A line is
  split into words (camelCase identifiers included) and every sequence of up
  to ``MAX_PHRASE_WORDS`` words is hashed and compared against the list.
* Project specific literals listed one per line in the git-ignored
  ``.repo-guard.local`` file: real phone numbers, addresses, seller and shop
  names, server addresses, merchant IDs, API keys and so on. The values are
  real secrets, which is why they live only on the developer's machine.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Iterator
from pathlib import Path

from .text import normalize

LOCAL_TERMS_FILE = ".repo-guard.local"
MAX_PHRASE_WORDS = 3
MIN_LITERAL_LENGTH = 3

BUILTIN_TERM_DIGESTS = frozenset(
    {
        "c857d09db23e6822e3600bc06ad8d58f92ed62bc8efd81c753f77048662cb97d",
        "c70eca6b0f88f44d81a41311647e50fda1ac454ec04ffd442b0eb4743a993131",
        "7d3194f79e645c42e4396dda38be04766810ec6a00d00aced3ffc2a0a1f1a9ef",
        "f3ed9ee201ce50b5961e91b689cad0460a7c48848f7954f6dc96be2d1e435816",
        "60965168ce762e949600281ba6d01fee136e5b6e8257b1f216f9025ed324474c",
        "053ea4804ef1bb33d4a3d6fb024a614b6d257cebc2bc7cd915da9c9522f37ffc",
        "3ea125d0bff386e6754b3782b300016fc79a9cf8f8669c0a5c3db64467ddb681",
        "487b91042c7cf27a19e23ea8699f5f354b1a0c3af9e418138dc6150d830f970d",
        "5d72436256ada53828b51895a94bb8489e9f1ac4fe937a8024ef1594e7045ff6",
        "ebde709e306badca2f843f1ef91c7fb216a99aa4417b32fe911e15acfff8bedd",
        "cdcbb68a3444fdd629ab0af770af3fc99e4d5dde43b576d5f855691e155283ec",
        "9760d607e65eafcf2cef66bf6b6d00e2c2707e9d4bebe4ab2752bfd16233adb6",
        "0677069fdf937bd1e36cb0f16701b00ee98436d5638157bae9d36f602ad62aba",
        "7086a5e04b87f69a2af70092fc9f8205243f75d4bb1afe5f26b102f73b9eff09",
        "c5f9d8f01eaaecc599699fbc9ada0dd9c4da6a59258bc55d6e464373afc049d5",
        "5eff592cc497fccb48ebfffaca38a83f9167bc1661b4477e1fc1b66b658cd5a0",
        "5e10fc66488f0eff44d26af5f34a8c39fb7cdd288b35caf807c807d5b28dd409",
    }
)

# Letters only: digits and underscores split words, so "foo_bar2" -> foo, bar.
_WORD = re.compile(r"[^\W\d_]+")
# Split "camelCase" and "HTTPServer" style identifiers into separate words.
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_NUMERIC_LITERAL = re.compile(r"\+?[\d\s\-().]+")
_DIGIT_SEPARATOR = r"[\s\-().]*"


def phrase_digest(phrase: str) -> str:
    """Return the digest used to store a restricted phrase.

    ``phrase`` must be lowercase words separated by single spaces.
    """
    return hashlib.sha256(phrase.encode("utf-8")).hexdigest()


def iter_words(text: str) -> Iterator[tuple[str, int, int]]:
    """Yield ``(lowercase_word, start, end)`` for every word in ``text``."""
    for match in _WORD.finditer(text):
        word, offset = match.group(), match.start()
        cuts = [0, *(boundary.start() for boundary in _CAMEL_BOUNDARY.finditer(word)), len(word)]
        for index in range(len(cuts) - 1):
            start, end = cuts[index], cuts[index + 1]
            yield word[start:end].lower(), offset + start, offset + end


# Hashes, keys and base64 data (e.g. lock-file "integrity" values) are long runs
# of letters and digits; any word found inside them is a coincidence.
_ENCODED_BLOB = re.compile(r"[A-Za-z0-9+/=_-]{32,}")


def _blank_encoded_blobs(text: str) -> str:
    """Replace encoded blobs with spaces, keeping every other offset intact."""

    def blank(match: re.Match[str]) -> str:
        blob = match.group()
        is_encoded = any(char.isdigit() for char in blob) and any(char.isalpha() for char in blob)
        return " " * len(blob) if is_encoded else blob

    return _ENCODED_BLOB.sub(blank, text)


def _literal_pattern(literal: str) -> re.Pattern[str] | None:
    """Compile a tolerant search pattern for a project specific literal.

    Numbers match regardless of spacing or dashes, and a leading ``0`` also
    matches the international ``+98`` / ``0098`` prefixes. Text matches case
    insensitively and with flexible whitespace.
    """
    literal = normalize(literal).strip()
    if len(literal) < MIN_LITERAL_LENGTH:
        return None

    if _NUMERIC_LITERAL.fullmatch(literal):
        digits = re.sub(r"\D", "", literal)
        if len(digits) < MIN_LITERAL_LENGTH:
            return None
        prefix = ""
        if digits.startswith("0") and not digits.startswith("00"):
            prefix, digits = r"(?:0|\+98|0098)" + _DIGIT_SEPARATOR, digits[1:]
        body = _DIGIT_SEPARATOR.join(re.escape(digit) for digit in digits)
        return re.compile(rf"(?<!\d){prefix}{body}(?!\d)")

    words = [re.escape(part) for part in literal.split()]
    return re.compile(r"\s+".join(words), re.IGNORECASE)


class TermMatcher:
    """Finds built-in restricted phrases and project specific literals."""

    def __init__(
        self,
        digests: Iterable[str] = BUILTIN_TERM_DIGESTS,
        literals: Iterable[str] = (),
    ) -> None:
        self._digests = frozenset(digests)
        patterns = (_literal_pattern(literal) for literal in literals)
        self._literal_patterns = tuple(pattern for pattern in patterns if pattern is not None)

    @classmethod
    def for_repository(cls, root: Path) -> TermMatcher:
        """Create a matcher using the local terms file of ``root``, if any."""
        return cls(literals=load_local_terms(root / LOCAL_TERMS_FILE))

    @property
    def literal_count(self) -> int:
        return len(self._literal_patterns)

    def search(self, text: str) -> tuple[int, int] | None:
        """Return the ``(start, end)`` span of the first restricted term."""
        text = normalize(text)
        for pattern in self._literal_patterns:
            match = pattern.search(text)
            if match:
                return match.span()
        return self._search_phrases(text)

    def _search_phrases(self, text: str) -> tuple[int, int] | None:
        words = list(iter_words(_blank_encoded_blobs(text)))
        for index in range(len(words)):
            window = words[index : index + MAX_PHRASE_WORDS]
            for size in range(1, len(window) + 1):
                phrase = " ".join(word for word, _, _ in window[:size])
                if phrase_digest(phrase) in self._digests:
                    return _widen_to_words(text, window[0][1], window[size - 1][2])
        return None


def _widen_to_words(text: str, start: int, end: int) -> tuple[int, int]:
    """Extend a span to whole words, e.g. from the "Case" part to all of "camelCase"."""
    while start > 0 and _WORD.match(text[start - 1]):
        start -= 1
    while end < len(text) and _WORD.match(text[end]):
        end += 1
    return start, end


def load_local_terms(path: Path) -> list[str]:
    """Read project specific literals, one per line; ``#`` starts a comment."""
    if not path.is_file():
        return []
    # "utf-8-sig" accepts files saved with a BOM by Windows editors.
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]
