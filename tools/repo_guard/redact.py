"""In-place redaction used when importing an existing project.

Every sensitive value the scanner reports is replaced with
``REDACTION_PLACEHOLDER`` so the source code can be published. The removed
values are returned to the caller, which stores them in a git-ignored file so
they can be moved into ``.env``.
"""

from __future__ import annotations

from dataclasses import dataclass

from .rules import REDACTION_PLACEHOLDER
from .scanner import Hit, Scanner

# Findings that cannot be fixed by replacing a single value on one line:
# a private key spans many lines, so such files are held back instead.
UNREDACTABLE_RULES = frozenset({"private-key"})

# A line is re-scanned after each pass because rules report only their first
# match per line. The limit guards against rules that never converge.
_MAX_PASSES = 10


@dataclass(frozen=True)
class Redaction:
    """A value removed from the source code."""

    path: str
    line: int
    rule_id: str
    value: str


class RedactionError(Exception):
    """Raised when a file cannot be made safe by replacing values."""


def redact_text(scanner: Scanner, path: str, text: str) -> tuple[str, list[Redaction]]:
    """Return ``text`` with every sensitive value replaced, and the removed values.

    Line endings are preserved exactly, so Windows files keep their CRLF endings.
    """
    output: list[str] = []
    redactions: list[Redaction] = []
    for number, raw_line in enumerate(text.splitlines(keepends=True), start=1):
        body = raw_line.rstrip("\r\n")
        ending = raw_line[len(body) :]
        for _ in range(_MAX_PASSES):
            hits = scanner.find_hits(path, body)
            if not hits:
                break
            blocking = sorted({hit.rule_id for hit in hits} & UNREDACTABLE_RULES)
            if blocking:
                raise RedactionError(f"line {number}: {', '.join(blocking)}")
            body, removed = _replace_hits(body, hits)
            redactions.extend(Redaction(path, number, rule_id, value) for rule_id, value in removed)
        else:
            raise RedactionError(f"line {number}: could not remove every sensitive value")
        output.append(body + ending)
    return "".join(output), redactions


def _replace_hits(text: str, hits: list[Hit]) -> tuple[str, list[tuple[str, str]]]:
    """Replace the (possibly overlapping) hit spans with the placeholder."""
    merged: list[list] = []
    for hit in sorted(hits, key=lambda item: (item.start, item.end)):
        if merged and hit.start < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], hit.end)
            merged[-1][2].add(hit.rule_id)
        else:
            merged.append([hit.start, hit.end, {hit.rule_id}])

    removed = []
    # Replace from the end so earlier offsets stay valid.
    for start, end, rule_ids in reversed(merged):
        removed.append(("+".join(sorted(rule_ids)), text[start:end]))
        text = f"{text[:start]}{REDACTION_PLACEHOLDER}{text[end:]}"
    removed.reverse()
    return text, removed
