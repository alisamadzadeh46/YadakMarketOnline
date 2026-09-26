"""Thin wrappers around the git command line."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterator, Sequence
from pathlib import Path

from .models import Line

# Options applied to every git call so that user configuration (colours,
# external diff tools, custom prefixes, quoted paths) cannot change the output
# format the parser relies on.
_GIT = ("git", "-c", "core.quotepath=off", "-c", "color.ui=never")
_PATCH_OPTIONS = (
    "--no-color",
    "--no-ext-diff",
    "--unified=0",
    "--src-prefix=a/",
    "--dst-prefix=b/",
    "--diff-filter=ACMR",
)

_HUNK_HEADER = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_C_ESCAPES = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}


class GitError(RuntimeError):
    """Raised when a git command fails."""


def run_git(*args: str, cwd: Path | None = None) -> str:
    """Run git and return its standard output decoded as UTF-8."""
    result = subprocess.run([*_GIT, *args], cwd=cwd, capture_output=True, check=False)
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise GitError(message or f"git {' '.join(args)} failed")
    return result.stdout.decode("utf-8", errors="replace")


def _split_null(output: str) -> list[str]:
    return [item for item in output.split("\0") if item]


def repository_root() -> Path:
    return Path(run_git("rev-parse", "--show-toplevel").strip())


def is_zero_revision(revision: str) -> bool:
    """Git reports missing refs in push hooks as a string of zeros."""
    return set(revision) == {"0"}


# ---------------------------------------------------------------------------
# Staged changes
# ---------------------------------------------------------------------------


def staged_paths() -> list[str]:
    return _split_null(run_git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"))


def staged_added_lines() -> Iterator[Line]:
    return parse_added_lines(run_git("diff", "--cached", *_PATCH_OPTIONS))


def current_identities() -> dict[str, str]:
    """Author and committer identities (``Name <email>``) of the next commit."""
    identities = {}
    for role, variable in (("author", "GIT_AUTHOR_IDENT"), ("committer", "GIT_COMMITTER_IDENT")):
        # The value ends with "<timestamp> <timezone>", which is not needed.
        identities[role] = run_git("var", variable).strip().rsplit(" ", 2)[0]
    return identities


# ---------------------------------------------------------------------------
# Commits
# ---------------------------------------------------------------------------


def revisions(revision_args: Sequence[str]) -> list[str]:
    """List commits selected by ``git rev-list`` arguments, oldest first."""
    return run_git("rev-list", "--reverse", *revision_args).split()


def commit_paths(revision: str) -> list[str]:
    return _split_null(
        run_git("diff-tree", "--no-commit-id", "--root", "-r", "--name-only", "--diff-filter=ACMR", "-z", revision)
    )


def commit_added_lines(revision: str) -> Iterator[Line]:
    return parse_added_lines(run_git("diff-tree", "--no-commit-id", "--root", "-r", "-p", *_PATCH_OPTIONS, revision))


def commit_message(revision: str) -> str:
    return run_git("log", "-1", "--format=%B", revision)


def commit_identities(revision: str) -> dict[str, str]:
    """Author and committer identities (``Name <email>``) of a commit."""
    author, _, committer = run_git("log", "-1", "--format=%an <%ae>%n%cn <%ce>", revision).strip().partition("\n")
    return {"author": author, "committer": committer}


# ---------------------------------------------------------------------------
# Working tree
# ---------------------------------------------------------------------------


def working_tree_files() -> list[str]:
    """Tracked files plus untracked files that are not ignored."""
    return _split_null(run_git("ls-files", "-z", "--cached", "--others", "--exclude-standard"))


def set_hooks_path(path: str) -> None:
    run_git("config", "core.hooksPath", path)


# ---------------------------------------------------------------------------
# Patch parsing
# ---------------------------------------------------------------------------


def parse_added_lines(patch: str) -> Iterator[Line]:
    """Yield every added line of a unified diff with its new line number.

    Hunk line counts are tracked so that an added line whose content starts
    with "++" is never mistaken for a file header.
    """
    path: str | None = None
    number = old_left = new_left = 0

    for raw in patch.split("\n"):
        if old_left > 0 or new_left > 0:
            if raw.startswith("+"):
                if path is not None:
                    yield Line(path, number, raw[1:])
                number += 1
                new_left -= 1
            elif raw.startswith("-"):
                old_left -= 1
            elif not raw.startswith("\\"):
                # Context line (only present when --unified is above zero).
                number += 1
                old_left -= 1
                new_left -= 1
            continue

        if raw.startswith("diff --git "):
            path = None
        elif raw.startswith("+++ "):
            target = _unquote(raw[4:].rstrip("\t"))
            path = None if target == "/dev/null" else target[2:] if target.startswith("b/") else target
        elif raw.startswith("@@"):
            header = _HUNK_HEADER.match(raw)
            if header:
                old_left = int(header.group(1) or 1)
                number = int(header.group(2))
                new_left = int(header.group(3) or 1)


def _unquote(value: str) -> str:
    """Decode a C-style quoted path as printed by git for unusual names."""
    if len(value) < 2 or not (value.startswith('"') and value.endswith('"')):
        return value
    body, decoded, index = value[1:-1], bytearray(), 0
    while index < len(body):
        char = body[index]
        if char == "\\" and index + 1 < len(body):
            following = body[index + 1]
            octal = body[index + 1 : index + 4]
            if len(octal) == 3 and all(digit in "01234567" for digit in octal):
                decoded.append(int(octal, 8))
                index += 4
                continue
            if following in _C_ESCAPES:
                decoded.append(_C_ESCAPES[following])
            else:
                decoded.extend(following.encode("utf-8"))
            index += 2
            continue
        decoded.extend(char.encode("utf-8"))
        index += 1
    return decoded.decode("utf-8", errors="replace")
