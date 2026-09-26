"""Command line interface used by the git hooks, CI and developers."""

from __future__ import annotations

import argparse
import dataclasses
import os
import stat
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

from . import gitio, importer
from .models import Finding
from .rules import RULE_MESSAGES
from .scanner import ALLOW_MARKER, Scanner, is_content_scanned
from .terms import LOCAL_TERMS_FILE, TermMatcher

HOOKS_DIRECTORY = ".githooks"
MAX_FILE_BYTES = 5 * 1024 * 1024
_BINARY_SNIFF_BYTES = 8192

_MAX_LISTED_HELD_BACK = 40

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2


# ---------------------------------------------------------------------------
# Scanning helpers
# ---------------------------------------------------------------------------


def _read_text_file(path: Path) -> str | None:
    """Return the file content, or ``None`` for binary, huge or missing files."""
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:_BINARY_SNIFF_BYTES]:
        return None
    return data.decode("utf-8", errors="replace")


def _prefixed(findings: Iterable[Finding], prefix: str) -> list[Finding]:
    return [dataclasses.replace(finding, path=f"{prefix}:{finding.path}") for finding in findings]


def _scan_commits(scanner: Scanner, commits: Sequence[str]) -> list[Finding]:
    findings: list[Finding] = []
    for commit in commits:
        label = commit[:10]
        commit_findings: list[Finding] = []
        for path in gitio.commit_paths(commit):
            commit_findings.extend(scanner.check_path(path))
        commit_findings.extend(scanner.check_lines(gitio.commit_added_lines(commit)))
        commit_findings.extend(scanner.check_commit_message("<message>", gitio.commit_message(commit)))
        for role, identity in gitio.commit_identities(commit).items():
            commit_findings.extend(scanner.check_identity(f"<{role}>", identity))
        findings.extend(_prefixed(commit_findings, label))
    return findings


def _pushed_commits(push_refs: str) -> list[str]:
    """Resolve the commits being pushed from the pre-push hook input.

    Each input line is ``<local ref> <local sha> <remote ref> <remote sha>``.
    """
    commits: list[str] = []
    for line in push_refs.splitlines():
        fields = line.split()
        if len(fields) != 4:
            continue
        _, local_sha, _, remote_sha = fields
        if gitio.is_zero_revision(local_sha):
            continue  # Branch deletion: nothing is uploaded.
        new_branch_range = [local_sha, "--not", "--remotes"]
        if gitio.is_zero_revision(remote_sha):
            selected = gitio.revisions(new_branch_range)
        else:
            try:
                selected = gitio.revisions([f"{remote_sha}..{local_sha}"])
            except gitio.GitError:
                # The remote commit is unknown locally (e.g. a force push).
                selected = gitio.revisions(new_branch_range)
        commits.extend(commit for commit in selected if commit not in commits)
    return commits


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _report(findings: Sequence[Finding], subject: str, outcome: str) -> int:
    if not findings:
        return EXIT_OK

    write = sys.stderr.write
    write(f"\nrepo-guard: sensitive data detected in {subject}.\n\n")
    for finding in findings:
        write(f"  {finding.location}  [{finding.rule_id}]\n")
        if finding.excerpt:
            write(f"      > {finding.excerpt}\n")

    write("\nWhy it was blocked:\n")
    for rule_id in sorted({finding.rule_id for finding in findings}):
        write(f"  [{rule_id}] {RULE_MESSAGES[rule_id]}\n")

    write(f"\n{len(findings)} problem(s) found. {outcome}\n")
    write(
        "Move real values to .env or the database. For a verified false positive, "
        f'append a comment containing "{ALLOW_MARKER}" to the line.\n\n'
    )
    return EXIT_FINDINGS


def _local_terms_tip(root: Path, matcher: TermMatcher) -> None:
    if matcher.literal_count == 0:
        sys.stderr.write(
            f"Tip: list your real phone numbers, address, server IP, merchant ID, API keys and seller "
            f"names in {root / LOCAL_TERMS_FILE} (one per line) so they can never be committed.\n"
        )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def _command_staged(scanner: Scanner, _args: argparse.Namespace) -> int:
    findings: list[Finding] = []
    for path in gitio.staged_paths():
        findings.extend(scanner.check_path(path))
    findings.extend(scanner.check_lines(gitio.staged_added_lines()))
    for role, identity in gitio.current_identities().items():
        findings.extend(scanner.check_identity(f"<{role}>", identity))
    return _report(findings, "the staged changes", "The commit was blocked.")


def _command_commit_msg(scanner: Scanner, args: argparse.Namespace) -> int:
    message = Path(args.message_file).read_text(encoding="utf-8", errors="replace")
    findings = scanner.check_commit_message("<message>", message)
    return _report(findings, "the commit message", "The commit was blocked.")


def _command_pre_push(scanner: Scanner, _args: argparse.Namespace) -> int:
    findings = _scan_commits(scanner, _pushed_commits(sys.stdin.read()))
    return _report(findings, "the commits being pushed", "The push was blocked.")


def _command_range(scanner: Scanner, args: argparse.Namespace) -> int:
    findings = _scan_commits(scanner, gitio.revisions(args.revisions))
    return _report(findings, "the selected commits", "Rewrite or drop these commits before pushing.")


def _command_history(scanner: Scanner, _args: argparse.Namespace) -> int:
    findings = _scan_commits(scanner, gitio.revisions(["--all"]))
    return _report(findings, "the repository history", "Rewrite or drop these commits before pushing.")


def _command_all(scanner: Scanner, args: argparse.Namespace) -> int:
    root: Path = args.root
    findings: list[Finding] = []
    for path in gitio.working_tree_files():
        findings.extend(scanner.check_path(path))
        if not is_content_scanned(path):
            continue
        text = _read_text_file(root / path)
        if text is not None:
            findings.extend(scanner.check_text(path, text))
    _local_terms_tip(root, scanner.terms)
    if not findings:
        print("repo-guard: no sensitive data found in the working tree.")
    return _report(findings, "the working tree", "Fix these before committing.")


def _command_install_hooks(scanner: Scanner, args: argparse.Namespace) -> int:
    hooks = args.root / HOOKS_DIRECTORY
    if os.name != "nt":
        for hook in hooks.iterdir():
            if hook.is_file():
                hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    gitio.set_hooks_path(HOOKS_DIRECTORY)
    print(f"repo-guard: git hooks enabled from {HOOKS_DIRECTORY}/ (pre-commit, commit-msg, pre-push).")
    _local_terms_tip(args.root, scanner.terms)
    return EXIT_OK


def _command_prepare(scanner: Scanner, args: argparse.Namespace) -> int:
    root: Path = args.root
    # Fail early, before any file is changed, if git has no identity to commit with.
    gitio.current_identities()
    gitio.set_hooks_path(HOOKS_DIRECTORY)

    plan = importer.build_plan(scanner, root)
    if not plan.to_stage and not plan.held_back:
        print("repo-guard: there are no new files to prepare.")
        return EXIT_OK
    _print_plan(plan)
    if not args.yes and not _confirm("Apply these changes? [y/N] "):
        print("Nothing was changed.")
        return EXIT_OK

    importer.apply_plan(plan, root)
    exit_code = _command_staged(scanner, args)
    if exit_code == EXIT_OK:
        print(f"\nDone: {len(plan.to_stage)} file(s) are staged. Publish them with:\n")
        print('    git commit -m "Add project source code"')
        print("    git push\n")
    return exit_code


def _print_plan(plan: importer.ImportPlan) -> None:
    print("\nPublication plan\n")
    print(f"  Files to publish: {len(plan.to_stage)}")
    for name, (count, size) in importer.size_by_top_level(plan).items():
        print(f"      {name:<40} {count:>6} file(s) {_format_size(size):>10}")
    print("  Largest files:")
    for path, size in importer.largest_files(plan):
        print(f"      {_format_size(size):>10}  {path}")

    if plan.rewrites:
        print(
            f"  Sensitive values to replace with __REDACTED__: {len(plan.redactions)} in {len(plan.rewrites)} file(s)"
        )
        for path in plan.rewrites:
            counts: dict[str, int] = {}
            for item in plan.redactions:
                if item.path == path:
                    counts[item.rule_id] = counts.get(item.rule_id, 0) + 1
            summary = ", ".join(f"{rule_id} x{count}" for rule_id, count in sorted(counts.items()))
            print(f"      {path}  ({summary})")

    if plan.held_back:
        print(f"  Held back (not published): {len(plan.held_back)}")
        for path, reason in list(plan.held_back.items())[:_MAX_LISTED_HELD_BACK]:
            print(f"      {path}  - {reason}")
        if len(plan.held_back) > _MAX_LISTED_HELD_BACK:
            print(f"      ... and {len(plan.held_back) - _MAX_LISTED_HELD_BACK} more")

    if plan.virtualenvs:
        print(f"  Virtual environments ignored: {', '.join(plan.virtualenvs)}")

    if plan.redactions:
        print(
            f"\nThe original values are saved to {importer.REDACTIONS_FILE} (git-ignored) so they can be moved to .env."
        )
    print()


def _format_size(size: float) -> str:
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def _confirm(question: str) -> bool:
    try:
        return input(question).strip().lower() in {"y", "yes"}
    except EOFError:
        return False


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.repo_guard",
        description="Prevent sensitive data from being committed or pushed.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("staged", help="scan staged changes (pre-commit hook)").set_defaults(handler=_command_staged)

    commit_msg = commands.add_parser("commit-msg", help="scan a commit message file (commit-msg hook)")
    commit_msg.add_argument("message_file")
    commit_msg.set_defaults(handler=_command_commit_msg)

    pre_push = commands.add_parser("pre-push", help="scan commits about to be pushed (pre-push hook)")
    pre_push.add_argument("remote", nargs="?")
    pre_push.add_argument("url", nargs="?")
    pre_push.set_defaults(handler=_command_pre_push)

    revision_range = commands.add_parser("range", help="scan commits selected by git rev-list arguments")
    revision_range.add_argument("revisions", nargs="+", help='for example "origin/main..HEAD"')
    revision_range.set_defaults(handler=_command_range)

    commands.add_parser("history", help="scan every commit reachable from any ref").set_defaults(
        handler=_command_history
    )
    commands.add_parser("all", help="scan every file that would be committed").set_defaults(handler=_command_all)
    commands.add_parser("install-hooks", help="enable the git hooks for this clone").set_defaults(
        handler=_command_install_hooks
    )

    prepare = commands.add_parser(
        "prepare",
        help="redact sensitive values in new files and stage everything that is safe to publish",
    )
    prepare.add_argument("--yes", action="store_true", help="apply the plan without asking for confirmation")
    prepare.set_defaults(handler=_command_prepare)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    # Never crash on Persian text in consoles that are not UTF-8 (Windows).
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")

    args = _build_parser().parse_args(argv)
    try:
        args.root = gitio.repository_root()
        # git prints paths relative to the working directory; use the root.
        os.chdir(args.root)
        scanner = Scanner(TermMatcher.for_repository(args.root))
        return args.handler(scanner, args)
    except gitio.GitError as error:
        sys.stderr.write(f"repo-guard: git error: {error}\n")
        return EXIT_ERROR
