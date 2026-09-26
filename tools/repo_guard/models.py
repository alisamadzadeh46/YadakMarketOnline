"""Data structures shared by the guard modules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Line:
    """A single line of text and the location it was read from."""

    path: str
    number: int
    text: str


@dataclass(frozen=True)
class Finding:
    """A problem reported by one of the rules.

    ``line`` is ``0`` when the finding concerns a whole file (for example a
    forbidden file name) rather than a specific line of its content.
    """

    path: str
    line: int
    rule_id: str
    excerpt: str = ""

    @property
    def location(self) -> str:
        """Human readable ``path:line`` reference."""
        return f"{self.path}:{self.line}" if self.line else self.path
