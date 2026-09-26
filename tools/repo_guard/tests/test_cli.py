"""End-to-end tests that run the command line interface on a temporary repository."""

import io
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from tools.repo_guard.cli import EXIT_FINDINGS, EXIT_OK, main
from tools.repo_guard.importer import REDACTIONS_FILE
from tools.repo_guard.rules import REDACTION_PLACEHOLDER

SAMPLE_PHONE = "09351847264"  # repo-guard: allow
ZERO_SHA = "0" * 40


@unittest.skipUnless(shutil.which("git"), "git is not installed")
class CliIntegrationTests(unittest.TestCase):
    def setUp(self):
        self._directory = tempfile.TemporaryDirectory()
        self.root = Path(self._directory.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Test User")
        self.git("config", "user.email", "test@example.com")
        self._previous_cwd = os.getcwd()
        os.chdir(self.root)

    def tearDown(self):
        os.chdir(self._previous_cwd)
        self._directory.cleanup()

    def git(self, *args):
        result = subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, text=True)
        return result.stdout.strip()

    def write(self, relative_path, content):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def stage(self, relative_path, content):
        self.write(relative_path, content)
        self.git("add", relative_path)

    def run_cli(self, *args, stdin=""):
        output = io.StringIO()
        with redirect_stderr(output), redirect_stdout(output), mock.patch("sys.stdin", io.StringIO(stdin)):
            exit_code = main(list(args))
        return exit_code, output.getvalue()

    def staged(self):
        return set(self.git("diff", "--cached", "--name-only").splitlines())

    def test_clean_changes_pass(self):
        self.stage("shop/views.py", "def index(request):\n    return None\n")
        self.assertEqual(self.run_cli("staged")[0], EXIT_OK)

    def test_sensitive_file_is_blocked(self):
        self.stage(".env", "DB_NAME=shop\n")
        exit_code, output = self.run_cli("staged")
        self.assertEqual(exit_code, EXIT_FINDINGS)
        self.assertIn("[env-file]", output)

    def test_sensitive_content_is_blocked_and_masked(self):
        self.stage("templates/footer.html", f"<p>{SAMPLE_PHONE}</p>\n")
        exit_code, output = self.run_cli("staged")
        self.assertEqual(exit_code, EXIT_FINDINGS)
        self.assertIn("templates/footer.html:1  [mobile-number]", output)
        self.assertNotIn(SAMPLE_PHONE, output)

    def test_local_terms_are_blocked(self):
        self.write(".repo-guard.local", "# real shop name\nSample Parts Shop\n")
        self.stage("templates/about.html", "<h1>Sample Parts Shop</h1>\n")
        exit_code, output = self.run_cli("staged")
        self.assertEqual(exit_code, EXIT_FINDINGS)
        self.assertIn("[restricted-term]", output)

    def test_commit_identity_is_checked(self):
        self.write(".repo-guard.local", "Blocked Author\n")
        self.git("config", "user.name", "Blocked Author")
        self.stage("shop/views.py", "VALUE = 1\n")
        exit_code, output = self.run_cli("staged")
        self.assertEqual(exit_code, EXIT_FINDINGS)
        self.assertIn("<author>  [restricted-term]", output)
        self.assertIn("<committer>  [restricted-term]", output)

    def test_commit_message_is_checked(self):
        self.write("message.txt", f"Update contact page\n\nCall {SAMPLE_PHONE}\n")
        self.assertEqual(self.run_cli("commit-msg", "message.txt")[0], EXIT_FINDINGS)

    def test_pre_push_checks_every_new_commit(self):
        self.stage("README.md", "# Shop\n")
        self.git("commit", "-q", "-m", "Initial commit")
        self.stage("shop/contact.py", f'PHONE = "{SAMPLE_PHONE}"\n')
        self.git("commit", "-q", "-m", "Add contact")
        head = self.git("rev-parse", "HEAD")

        push_refs = f"refs/heads/main {head} refs/heads/main {ZERO_SHA}\n"
        exit_code, output = self.run_cli("pre-push", "origin", "url", stdin=push_refs)
        self.assertEqual(exit_code, EXIT_FINDINGS)
        self.assertIn(f"{head[:10]}:shop/contact.py:1", output)

    def test_branch_deletion_is_ignored(self):
        stdin = f"(delete) {ZERO_SHA} refs/heads/old {ZERO_SHA}\n"
        self.assertEqual(self.run_cli("pre-push", "origin", "url", stdin=stdin)[0], EXIT_OK)

    def test_prepare_redacts_holds_back_and_stages(self):
        self.write(".gitignore", "*.local\n")
        self.write("shop/settings.py", f'SUPPORT_PHONE = "{SAMPLE_PHONE}"\nDEBUG = False\n')
        self.write("shop/views.py", "def index(request):\n    return None\n")
        self.write("shop/fixtures/sellers.json", "[]\n")
        self.write("venv2/pyvenv.cfg", "home = /usr\n")
        self.write("venv2/lib/site.py", "x = 1\n")

        exit_code, output = self.run_cli("prepare", "--yes")

        self.assertEqual(exit_code, EXIT_OK, output)
        self.assertEqual(self.staged(), {".gitignore", "shop/settings.py", "shop/views.py"})
        settings = (self.root / "shop/settings.py").read_text(encoding="utf-8")
        self.assertIn(f'SUPPORT_PHONE = "{REDACTION_PLACEHOLDER}"', settings)
        self.assertIn(SAMPLE_PHONE, (self.root / REDACTIONS_FILE).read_text(encoding="utf-8"))
        self.assertIn("shop/fixtures/sellers.json", output)
        self.assertIn("/venv2/", (self.root / ".git/info/exclude").read_text(encoding="utf-8"))

    def test_prepare_changes_nothing_without_confirmation(self):
        self.write("shop/settings.py", f'SUPPORT_PHONE = "{SAMPLE_PHONE}"\n')
        exit_code, _ = self.run_cli("prepare", stdin="n\n")
        self.assertEqual(exit_code, EXIT_OK)
        self.assertEqual(self.staged(), set())
        self.assertIn(SAMPLE_PHONE, (self.root / "shop/settings.py").read_text(encoding="utf-8"))

    def test_working_tree_audit_includes_untracked_files(self):
        self.write("notes/servers.txt", "HOST = 93.184.216.34\n")  # repo-guard: allow
        exit_code, output = self.run_cli("all")
        self.assertEqual(exit_code, EXIT_FINDINGS)
        self.assertIn("[server-address]", output)


if __name__ == "__main__":
    unittest.main()
