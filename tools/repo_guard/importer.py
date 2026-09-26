"""Prepares an existing project for its first publication.

The work is split in two steps so the user can review it first:

1. ``build_plan`` inspects every file that is not committed yet and decides
   whether it is published as is, published with sensitive values redacted,
   or held back. Nothing is written in this step.
2. ``apply_plan`` rewrites the redacted files, stores the removed values in a
   git-ignored file and stages everything that is safe to publish.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from . import gitio
from .redact import Redaction, RedactionError, redact_text
from .scanner import Scanner, is_content_scanned

REDACTIONS_FILE = ".redactions.local"
MAX_SCANNED_BYTES = 5 * 1024 * 1024
# GitHub warns above 50 MB and rejects files above 100 MB.
MAX_PUBLISHED_BYTES = 50 * 1024 * 1024
_BINARY_SNIFF_BYTES = 8192

# Files that only exist inside the data directory of a database server. Such
# directories (usually Docker volumes) are held back as a whole, whatever
# their name, because they contain the complete production data.
_SERVICE_DATA_MARKERS = {
    "pg_version": "PostgreSQL",
    "ibdata1": "MySQL",
    "appendonly.aof": "Redis",
    "wiredtiger": "MongoDB",
    "mongod.lock": "MongoDB",
}

# Seed data is often exported from the production database, so it is held
# back until someone confirms it contains no real customer or seller records.
_REVIEW_DIRECTORIES = frozenset({"fixtures", "seeds"})
_REVIEW_SUFFIXES = (".csv", ".tsv")

_REDACTIONS_HEADER = (
    "# Values removed from the source code by `python -m tools.repo_guard prepare`.\n"
    "# Move each value into .env, then delete this file. It is git-ignored.\n"
)


@dataclass
class ImportPlan:
    """What ``apply_plan`` will do; built without touching any file."""

    to_stage: list[str] = field(default_factory=list)
    sizes: dict[str, int] = field(default_factory=dict)
    rewrites: dict[str, str] = field(default_factory=dict)
    redactions: list[Redaction] = field(default_factory=list)
    held_back: dict[str, str] = field(default_factory=dict)
    virtualenvs: list[str] = field(default_factory=list)


def build_plan(scanner: Scanner, root: Path) -> ImportPlan:
    plan = ImportPlan(virtualenvs=find_virtualenvs(root))
    pending = [
        path for path in gitio.pending_files() if not any(path.startswith(f"{venv}/") for venv in plan.virtualenvs)
    ]

    data_directories = find_service_data_directories(pending)
    held_counts = dict.fromkeys(data_directories, 0)
    for path in pending:
        directory = next((item for item in data_directories if path.startswith(f"{item}/")), None)
        if directory is None:
            _plan_file(scanner, root, path, plan)
        else:
            held_counts[directory] += 1
    for directory, service in data_directories.items():
        plan.held_back[f"{directory}/"] = f"{service} data directory ({held_counts[directory]} files)"
    return plan


def apply_plan(plan: ImportPlan, root: Path) -> None:
    for path, text in plan.rewrites.items():
        # newline="" writes the text back with its original line endings.
        (root / path).write_text(text, encoding="utf-8", newline="")
    if plan.redactions:
        _save_redactions(root / REDACTIONS_FILE, plan.redactions)
    if plan.virtualenvs:
        _exclude_locally(root, [f"/{venv}/" for venv in plan.virtualenvs])
    gitio.add_paths(plan.to_stage)


def size_by_top_level(plan: ImportPlan) -> dict[str, tuple[int, int]]:
    """Map each top-level directory (or root file) to ``(file_count, total_bytes)``."""
    totals: dict[str, tuple[int, int]] = {}
    for path in plan.to_stage:
        parts = PurePosixPath(path).parts
        key = f"{parts[0]}/" if len(parts) > 1 else parts[0]
        count, size = totals.get(key, (0, 0))
        totals[key] = (count + 1, size + plan.sizes.get(path, 0))
    return dict(sorted(totals.items()))


def largest_files(plan: ImportPlan, limit: int = 10) -> list[tuple[str, int]]:
    ranked = sorted(((path, plan.sizes.get(path, 0)) for path in plan.to_stage), key=lambda item: -item[1])
    return ranked[:limit]


def find_service_data_directories(paths: list[str]) -> dict[str, str]:
    """Return ``{directory: service}`` for database data directories in ``paths``.

    Only the outermost directory is kept when data directories are nested.
    """
    found: dict[str, str] = {}
    for path in sorted(paths, key=lambda item: item.count("/")):
        posix = PurePosixPath(path)
        service = _SERVICE_DATA_MARKERS.get(posix.name.lower())
        directory = str(posix.parent)
        if service and directory != "." and not any(directory.startswith(f"{known}/") for known in found):
            found.setdefault(directory, service)
    return found


def find_virtualenvs(root: Path) -> list[str]:
    """Top-level virtual environments that ``.gitignore`` does not cover."""
    return sorted(
        child.name
        for child in root.iterdir()
        if child.is_dir() and (child / "pyvenv.cfg").is_file() and not gitio.is_ignored(f"{child.name}/")
    )


def needs_review(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return path.lower().endswith(_REVIEW_SUFFIXES) or any(part.lower() in _REVIEW_DIRECTORIES for part in parts[:-1])


def _plan_file(scanner: Scanner, root: Path, path: str, plan: ImportPlan) -> None:
    path_findings = scanner.check_path(path)
    if path_findings:
        rule_ids = ", ".join(sorted({finding.rule_id for finding in path_findings}))
        plan.held_back[path] = f"not allowed in the repository ({rule_ids})"
        return
    if needs_review(path):
        plan.held_back[path] = "data file; publish it only after checking it holds no real records"
        return

    size = (root / path).stat().st_size
    if size > MAX_PUBLISHED_BYTES:
        plan.held_back[path] = f"too large to publish ({size / 1024 / 1024:.0f} MB)"
        return
    plan.sizes[path] = size

    data = (root / path).read_bytes()
    is_binary = b"\0" in data[:_BINARY_SNIFF_BYTES]
    if is_binary or len(data) > MAX_SCANNED_BYTES or not is_content_scanned(path):
        plan.to_stage.append(path)
        return

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        # Rewriting a file in an unknown encoding could corrupt it.
        if scanner.check_text(path, data.decode("utf-8", errors="replace")):
            plan.held_back[path] = "not UTF-8 encoded and contains sensitive data"
        else:
            plan.to_stage.append(path)
        return

    try:
        redacted, removed = redact_text(scanner, path, text)
    except RedactionError as error:
        plan.held_back[path] = f"cannot be redacted automatically ({error})"
        return
    if removed:
        plan.rewrites[path] = redacted
        plan.redactions.extend(removed)
    plan.to_stage.append(path)


def _save_redactions(target: Path, redactions: list[Redaction]) -> None:
    is_new = not target.exists()
    with target.open("a", encoding="utf-8") as handle:
        if is_new:
            handle.write(_REDACTIONS_HEADER)
        for item in redactions:
            handle.write(f"{item.path}:{item.line}  [{item.rule_id}]  {item.value}\n")


def _exclude_locally(root: Path, patterns: list[str]) -> None:
    exclude = gitio.exclude_file()
    exclude = exclude if exclude.is_absolute() else root / exclude
    exclude.parent.mkdir(parents=True, exist_ok=True)
    content = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    missing = [pattern for pattern in patterns if pattern not in content.splitlines()]
    if missing:
        separator = "\n" if content and not content.endswith("\n") else ""
        with exclude.open("a", encoding="utf-8") as handle:
            handle.write(separator + "".join(f"{pattern}\n" for pattern in missing))
