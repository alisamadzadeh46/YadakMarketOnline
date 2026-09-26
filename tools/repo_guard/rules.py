"""Rule definitions.

Two kinds of rules exist:

* ``PathRule`` rejects a file by its name or location (databases, backups,
  keys, uploaded media...), regardless of its content.
* ``ContentRule`` rejects a single line of text that contains sensitive data
  (phone numbers, credentials, payment gateway keys...).

To add a rule, append an instance to ``PATH_RULES`` or ``CONTENT_RULES``; the
scanner picks it up automatically and its message appears in reports.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import PurePosixPath

from . import validators

# A validator receives the regex match and the whole (normalised) line and
# decides whether the match is a real finding.
Validator = Callable[[re.Match, str], bool]

# Value written in place of sensitive data by ``redact.py``. Matches whose
# sensitive part already holds this placeholder are never reported again.
REDACTION_PLACEHOLDER = "__REDACTED__"


@dataclass(frozen=True)
class PathRule:
    """Blocks files by name pattern or by the directories they live in."""

    rule_id: str
    message: str
    file_patterns: tuple[str, ...] = ()
    directories: frozenset[str] = field(default_factory=frozenset)
    exceptions: tuple[str, ...] = ()

    def matches(self, path: str) -> bool:
        parts = PurePosixPath(path.replace("\\", "/")).parts
        if not parts:
            return False
        name = parts[-1].lower()
        if any(fnmatchcase(name, pattern) for pattern in self.exceptions):
            return False
        if any(fnmatchcase(name, pattern) for pattern in self.file_patterns):
            return True
        return any(part.lower() in self.directories for part in parts[:-1])


@dataclass(frozen=True)
class ContentRule:
    """Blocks lines matching ``pattern`` that also pass ``validator``.

    ``group`` selects the part of the match that holds the sensitive value; it
    is the part masked in reports. ``file_patterns`` optionally restricts the
    rule to matching file names (for example configuration files only).
    """

    rule_id: str
    message: str
    pattern: re.Pattern[str]
    validator: Validator | None = None
    group: int = 0
    file_patterns: tuple[str, ...] = ()

    def applies_to(self, path: str) -> bool:
        if not self.file_patterns:
            return True
        name = PurePosixPath(path.replace("\\", "/")).name.lower()
        return any(fnmatchcase(name, pattern) for pattern in self.file_patterns)

    def find(self, text: str) -> re.Match[str] | None:
        """Return the first confirmed match in ``text``, if any."""
        for match in self.pattern.finditer(text):
            if REDACTION_PLACEHOLDER in match.group(self.group):
                continue
            if self.validator is None or self.validator(match, text):
                return match
        return None


# ---------------------------------------------------------------------------
# Path rules
# ---------------------------------------------------------------------------

PATH_RULES: tuple[PathRule, ...] = (
    PathRule(
        rule_id="env-file",
        message="Environment files hold real credentials. Commit only .env.example with empty values.",
        file_patterns=(".env", ".env.*", "*.env"),
        exceptions=(".env.example", ".env.sample", ".env.template"),
    ),
    PathRule(
        rule_id="database-file",
        message="Database files and dumps contain real customer and seller records.",
        file_patterns=(
            "*.sqlite",
            "*.sqlite3",
            "*.sqlite3-journal",
            "*.db",
            "*.sql",
            "*.sql.gz",
            "*.dump",
            "*.psql",
            "*.rdb",
            "*.mdb",
            "*.accdb",
        ),
    ),
    PathRule(
        rule_id="backup-file",
        message="Backups and archives must be stored outside the repository.",
        file_patterns=(
            "*.bak",
            "*.backup",
            "*.old",
            "*.orig",
            "*~",
            "*.zip",
            "*.rar",
            "*.7z",
            "*.tar",
            "*.gz",
            "*.tgz",
        ),
        directories=frozenset({"backup", "backups"}),
    ),
    PathRule(
        rule_id="key-file",
        message="Private keys, certificates and credential stores must never be committed.",
        file_patterns=(
            "*.pem",
            "*.key",
            "*.p12",
            "*.pfx",
            "*.jks",
            "*.kdbx",
            "*.ovpn",
            "id_rsa*",
            "id_dsa*",
            "id_ecdsa*",
            "id_ed25519*",
            "credentials.json",
            "secrets.json",
            "service-account*.json",
        ),
    ),
    PathRule(
        rule_id="local-settings",
        message="Machine or server specific settings belong in .env, not in the repository.",
        file_patterns=("local_settings.py", "settings_local.py", "*.local"),
        directories=frozenset({"secrets"}),
    ),
    PathRule(
        rule_id="uploaded-media",
        message="User uploads (product photos, seller documents) are runtime data, not source code.",
        directories=frozenset({"media", "uploads"}),
    ),
    PathRule(
        rule_id="data-export",
        message="Data exports may contain real customer or seller information.",
        file_patterns=("*dumpdata*.json", "*export*.csv", "*export*.xlsx", "*.xls", "*.xlsx"),
    ),
)


# ---------------------------------------------------------------------------
# Content rule validators
# ---------------------------------------------------------------------------

_NATIONAL_ID_CONTEXT = re.compile(r"national|mell?i|کد\s*ملی|شماره\s*ملی", re.IGNORECASE)
_PAYMENT_CONTEXT = re.compile(r"merchant|zarin", re.IGNORECASE)
_NON_SECRET_VALUES = frozenset({"bearer", "basic", "token", "true", "false", "none", "null", "required", "hidden"})
_SECRET_KEYWORDS = re.compile(r"pass|pwd|secret|key|token|merchant", re.IGNORECASE)


def _is_real_phone(match: re.Match[str], _line: str) -> bool:
    return not validators.is_dummy_number(validators.digits_only(match.group(0)))


def _is_national_id(match: re.Match[str], line: str) -> bool:
    return bool(_NATIONAL_ID_CONTEXT.search(line)) and validators.is_valid_national_id(match.group(0))


def _is_card_number(match: re.Match[str], _line: str) -> bool:
    return validators.passes_luhn(validators.digits_only(match.group(0)))


def _is_sheba(match: re.Match[str], _line: str) -> bool:
    return validators.is_valid_iban(match.group(0))


def _is_public_ip(match: re.Match[str], _line: str) -> bool:
    return validators.is_public_ip(match.group(0))


def _is_real_email(match: re.Match[str], _line: str) -> bool:
    return validators.is_real_email(match.group(0))


def _is_merchant_id(match: re.Match[str], line: str) -> bool:
    return bool(_PAYMENT_CONTEXT.search(line)) and len(set(validators.digits_only(match.group(0)))) > 1


def _is_real_query_value(match: re.Match[str], _line: str) -> bool:
    return not validators.is_placeholder(match.group(1))


def _is_real_secret_value(match: re.Match[str], _line: str) -> bool:
    """Accept a captured value unless it is a label, URL, path or placeholder."""
    value = match.group(1)
    if not value.isascii():
        # Persian form labels such as 'گذرواژه' are not credentials.
        return False
    if "://" in value or value.startswith(("/", ".")):
        return False
    if value.lower() in _NON_SECRET_VALUES:
        return False
    if re.fullmatch(r"[A-Za-z_]+", value) and _SECRET_KEYWORDS.search(value):
        # Identifiers like 'new_password' or 'api_key' are field names.
        return False
    return not validators.is_placeholder(value)


def _is_real_config_value(match: re.Match[str], line: str) -> bool:
    """Like ``_is_real_secret_value`` but also accepts variable references.

    Shell, batch and compose files legitimately reference secrets with
    ``$DB_PASSWORD``, ``%DB_PASSWORD%`` or ``$(cat /run/secrets/db)``.
    """
    value = match.group(1)
    if value.startswith(("$", "%")) or "(" in value or "[" in value:
        return False
    return _is_real_secret_value(match, line)


# File names treated as configuration files by the ``config-secret`` rule.
_CONFIG_FILE_PATTERNS = (
    ".env*",
    "*.env",
    "*.ini",
    "*.cfg",
    "*.conf",
    "*.toml",
    "*.yml",
    "*.yaml",
    "*.properties",
    "*.service",
    "*.sh",
    "*.bash",
    "*.bat",
    "*.cmd",
    "*.ps1",
    "dockerfile*",
    "makefile",
    "procfile",
)


# ---------------------------------------------------------------------------
# Content rules
# ---------------------------------------------------------------------------

_TRUST_SEAL_MESSAGE = "eNamad / Samandehi seal IDs and codes belong in .env and must be rendered from settings."

CONTENT_RULES: tuple[ContentRule, ...] = (
    ContentRule(
        rule_id="private-key",
        message="Private key material must never be committed.",
        pattern=re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ),
    ContentRule(
        rule_id="mobile-number",
        message="Real mobile numbers must come from settings or the database, not from code.",
        pattern=re.compile(r"(?<![\d+])(?:\+98|0098|0)[ -]?9\d{2}[ -]?\d{3}[ -]?\d{4}(?!\d)"),
        validator=_is_real_phone,
    ),
    ContentRule(
        rule_id="landline-number",
        message="Real landline numbers must come from settings or the database, not from code.",
        pattern=re.compile(r"(?<![\d+])(?:(?:\+98|0098)[ -]?|0)[1-8]\d[ -]?\d{8}(?!\d)"),
        validator=_is_real_phone,
    ),
    ContentRule(
        rule_id="national-id",
        message="Iranian national ID numbers are personal data and must not be committed.",
        pattern=re.compile(r"(?<!\d)\d{10}(?!\d)"),
        validator=_is_national_id,
    ),
    ContentRule(
        rule_id="bank-card",
        message="Bank card numbers are personal financial data and must not be committed.",
        pattern=re.compile(r"(?<!\d)(?:\d{4}[ -]?){3}\d{4}(?!\d)"),
        validator=_is_card_number,
    ),
    ContentRule(
        rule_id="sheba-number",
        message="Sheba (IBAN) numbers are personal financial data and must not be committed.",
        pattern=re.compile(r"(?<![A-Za-z0-9])IR(?: ?\d){24}(?!\d)", re.IGNORECASE),
        validator=_is_sheba,
    ),
    ContentRule(
        rule_id="server-address",
        message="Public server IP addresses belong in .env or deployment secrets.",
        pattern=re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?!\.?\d)"),
        validator=_is_public_ip,
    ),
    ContentRule(
        rule_id="email-address",
        message="Real e-mail addresses must come from settings or the database, not from code.",
        pattern=re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"),
        validator=_is_real_email,
    ),
    ContentRule(
        rule_id="payment-merchant-id",
        message="Payment gateway merchant IDs belong in .env (ZARINPAL_MERCHANT_ID).",
        pattern=re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE),
        validator=_is_merchant_id,
    ),
    ContentRule(
        rule_id="trust-seal",
        message=_TRUST_SEAL_MESSAGE,
        # The whole query string is the sensitive part: it carries both the ID and the code.
        pattern=re.compile(r"(?:enamad|samandehi)\.ir[^\s'\"?]*\?([^\s'\"<>]*=[^\s'\"<>]+)", re.IGNORECASE),
        validator=_is_real_query_value,
        group=1,
    ),
    ContentRule(
        rule_id="trust-seal",
        message=_TRUST_SEAL_MESSAGE,
        # Domain verification tag, e.g. <meta name="enamad" content="...">, in any attribute order.
        pattern=re.compile(r"<meta\b(?=[^>]*[\"']enamad[\"'])[^>]*?content\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE),
        validator=_is_real_query_value,
        group=1,
    ),
    ContentRule(
        rule_id="sms-api-key",
        message="SMS panel API keys belong in .env (SMS_API_KEY).",
        pattern=re.compile(r"api\.kavenegar\.com/v\d+/([A-Za-z0-9%+=-]{16,})", re.IGNORECASE),
        group=1,
    ),
    ContentRule(
        rule_id="credential-url",
        message="Connection URLs must not embed passwords; build them from environment variables.",
        pattern=re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s/:@'\"]*:([^\s/@'\"]+)@", re.IGNORECASE),
        validator=lambda match, _line: not validators.is_placeholder(match.group(1)),
        group=1,
    ),
    ContentRule(
        rule_id="credential-query",
        message="Credentials must not be passed as literal URL query parameters.",
        pattern=re.compile(
            r"[?&](?:password|pass|pwd|secret|token|api_?key)=([^&\s'\"]{4,})",
            re.IGNORECASE,
        ),
        validator=lambda match, _line: not validators.is_placeholder(match.group(1)),
        group=1,
    ),
    ContentRule(
        rule_id="cli-password",
        message="Command line passwords (sshpass, mysql -p...) must come from environment variables.",
        pattern=re.compile(r"(?:sshpass\s+-p\s*|\bmysql(?:dump)?\b.*?\s-p)[\"']?([^\s\"']{3,})"),
        validator=lambda match, _line: not validators.is_placeholder(match.group(1)),
        group=1,
    ),
    ContentRule(
        rule_id="hardcoded-secret",
        message="Credential assigned a literal value; load it from the environment (.env) instead.",
        pattern=re.compile(
            r"\b\w*(?:password|passwd|pwd|secret|api[_-]?key|apikey|access[_-]?key|auth[_-]?key|token)\w*"
            r"[\"']?\s*(?:=|:|=>)\s*[rbuf]?[\"']([^\"'\s]{4,})[\"']",
            re.IGNORECASE,
        ),
        validator=_is_real_secret_value,
        group=1,
    ),
    ContentRule(
        rule_id="env-default-secret",
        message="Environment lookups must not fall back to a real credential; use an empty default.",
        pattern=re.compile(
            r"\(\s*[\"'][^\"']*(?:password|passwd|secret|api_?key|token|merchant)[^\"']*[\"']\s*,"
            r"\s*(?:default\s*=\s*)?[\"']([^\"'\s]{4,})[\"']",
            re.IGNORECASE,
        ),
        validator=_is_real_secret_value,
        group=1,
    ),
    ContentRule(
        rule_id="config-secret",
        message="Configuration files must not contain real credentials; keep them in .env.",
        pattern=re.compile(
            r"^\s*(?:export\s+|set\s+)?[\"']?[\w.-]*"
            r"(?:password|passwd|pwd|secret|api[_-]?key|token|merchant[_-]?id)[\w.-]*"
            r"[\"']?\s*[:=]\s*[\"']?([^\s\"'#]{4,})",
            re.IGNORECASE,
        ),
        validator=_is_real_config_value,
        group=1,
        file_patterns=_CONFIG_FILE_PATTERNS,
    ),
)


# Rules implemented outside the tables above (see ``terms.py``).
RESTRICTED_TERM_RULE_ID = "restricted-term"
RESTRICTED_TERM_MESSAGE = (
    "Restricted term found. It is either a project secret listed in "
    ".repo-guard.local or a term that must not appear in the repository."
)

RULE_MESSAGES = {
    **{rule.rule_id: rule.message for rule in PATH_RULES},
    **{rule.rule_id: rule.message for rule in CONTENT_RULES},
    RESTRICTED_TERM_RULE_ID: RESTRICTED_TERM_MESSAGE,
}
