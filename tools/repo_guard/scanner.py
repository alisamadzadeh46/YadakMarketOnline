"""Applies path rules, content rules and restricted terms to repository data."""

from __future__ import annotations

from collections.abc import Iterable
from fnmatch import fnmatchcase
from pathlib import PurePosixPath

from .models import Finding, Line
from .rules import CONTENT_RULES, PATH_RULES, RESTRICTED_TERM_RULE_ID, ContentRule, PathRule
from .terms import TermMatcher
from .text import make_excerpt, normalize

# Adding this marker to a line suppresses content findings for that line.
# Use it only for verified false positives (test fixtures, documentation).
ALLOW_MARKER = "repo-guard: allow"

# Third-party or generated files whose content is not scanned. Their paths
# are still checked against the path rules and restricted terms.
_UNSCANNED_FILE_PATTERNS = ("*.min.js", "*.min.css", "*.map")
_UNSCANNED_DIRECTORIES = frozenset({"node_modules", "vendor", "vendors"})

# Everything below this line of a commit message template is discarded by git.
_SCISSORS_LINE = "# ------------------------ >8 ------------------------"


def is_content_scanned(path: str) -> bool:
    """Return ``False`` for vendored or minified files."""
    parts = PurePosixPath(path.replace("\\", "/")).parts
    if not parts:
        return False
    name = parts[-1].lower()
    if any(fnmatchcase(name, pattern) for pattern in _UNSCANNED_FILE_PATTERNS):
        return False
    return not any(part.lower() in _UNSCANNED_DIRECTORIES for part in parts[:-1])


class Scanner:
    """Runs every configured check and collects the findings."""

    def __init__(
        self,
        terms: TermMatcher,
        path_rules: Iterable[PathRule] = PATH_RULES,
        content_rules: Iterable[ContentRule] = CONTENT_RULES,
    ) -> None:
        self.terms = terms
        self.path_rules = tuple(path_rules)
        self.content_rules = tuple(content_rules)

    def check_path(self, path: str) -> list[Finding]:
        """Check a file path against the path rules and restricted terms."""
        findings = [Finding(path, 0, rule.rule_id) for rule in self.path_rules if rule.matches(path)]
        span = self.terms.search(path)
        if span:
            findings.append(Finding(path, 0, RESTRICTED_TERM_RULE_ID, make_excerpt(path, *span)))
        return findings

    def check_line(self, line: Line) -> list[Finding]:
        """Check a single line of content."""
        if ALLOW_MARKER in line.text:
            return []
        text = normalize(line.text)
        findings = []
        for rule in self.content_rules:
            if not rule.applies_to(line.path):
                continue
            match = rule.find(text)
            if match:
                excerpt = make_excerpt(text, *match.span(rule.group))
                findings.append(Finding(line.path, line.number, rule.rule_id, excerpt))
        span = self.terms.search(text)
        if span:
            findings.append(Finding(line.path, line.number, RESTRICTED_TERM_RULE_ID, make_excerpt(text, *span)))
        return findings

    def check_lines(self, lines: Iterable[Line]) -> list[Finding]:
        """Check many lines, skipping files whose content is not scanned."""
        findings = []
        for line in lines:
            if is_content_scanned(line.path):
                findings.extend(self.check_line(line))
        return findings

    def check_text(self, path: str, text: str) -> list[Finding]:
        """Check the full text of a file."""
        lines = (Line(path, number, content) for number, content in enumerate(text.splitlines(), start=1))
        return self.check_lines(lines)

    def check_commit_message(self, source: str, message: str) -> list[Finding]:
        """Check a commit message, ignoring git's comment lines."""
        findings = []
        for number, content in enumerate(message.splitlines(), start=1):
            if content.startswith(_SCISSORS_LINE):
                break
            if content.startswith("#"):
                continue
            findings.extend(self.check_line(Line(source, number, content)))
        return findings

    def check_identity(self, source: str, identity: str) -> list[Finding]:
        """Check an author or committer identity for restricted terms."""
        span = self.terms.search(identity)
        if not span:
            return []
        return [Finding(source, 0, RESTRICTED_TERM_RULE_ID, make_excerpt(identity, *span))]
