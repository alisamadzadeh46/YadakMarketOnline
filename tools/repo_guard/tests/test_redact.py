import unittest

from tools.repo_guard.redact import RedactionError, redact_text
from tools.repo_guard.rules import REDACTION_PLACEHOLDER
from tools.repo_guard.scanner import Scanner
from tools.repo_guard.terms import TermMatcher, phrase_digest

PHONE = "09351847264"  # repo-guard: allow
OTHER_PHONE = "09128873365"  # repo-guard: allow


class RedactTextTests(unittest.TestCase):
    def setUp(self):
        self.scanner = Scanner(TermMatcher(digests={phrase_digest("forbidden")}, literals=["Sample Parts Shop"]))

    def redact(self, text, path="app/views.py"):
        return redact_text(self.scanner, path, text)

    def test_every_value_on_a_line_is_replaced(self):
        text, removed = self.redact(f"contacts = ['{PHONE}', '{OTHER_PHONE}']\n")
        self.assertEqual(text, f"contacts = ['{REDACTION_PLACEHOLDER}', '{REDACTION_PLACEHOLDER}']\n")
        self.assertEqual([item.value for item in removed], [PHONE, OTHER_PHONE])
        self.assertEqual({item.line for item in removed}, {1})

    def test_line_endings_and_clean_lines_are_preserved(self):
        original = f"first\r\nphone {PHONE}\r\nlast"
        text, _ = self.redact(original)
        self.assertEqual(text, f"first\r\nphone {REDACTION_PLACEHOLDER}\r\nlast")

    def test_only_the_sensitive_part_is_replaced(self):
        line = "SECRET_KEY = 'django-insecure-k8Qz3vTn1p'"  # repo-guard: allow
        text, removed = self.redact(line)
        self.assertEqual(text, f"SECRET_KEY = '{REDACTION_PLACEHOLDER}'")
        self.assertEqual(removed[0].rule_id, "hardcoded-secret")

    def test_restricted_terms_are_replaced_as_whole_words(self):
        text, _ = self.redact("# helper from MyForbiddenTool\n")
        self.assertEqual(text, f"# helper from {REDACTION_PLACEHOLDER}\n")

    def test_local_literals_are_replaced(self):
        text, _ = self.redact("<h1>Sample Parts Shop</h1>", "templates/base.html")
        self.assertEqual(text, f"<h1>{REDACTION_PLACEHOLDER}</h1>")

    def test_trust_seal_codes_are_fully_removed(self):
        link = "<a href='https://trustseal.enamad.ir/?id=412345&Code=Qw3rTyUi'>"  # repo-guard: allow
        meta = '<meta content="87654321" name="enamad">'  # repo-guard: allow
        text, _ = self.redact(f"{link}\n{meta}\n", "templates/base.html")
        self.assertNotIn("412345", text)  # repo-guard: allow
        self.assertNotIn("Qw3rTyUi", text)  # repo-guard: allow
        self.assertNotIn("87654321", text)  # repo-guard: allow

    def test_redacted_text_passes_the_scanner(self):
        text, _ = self.redact(f"tel: {PHONE}\nSMS_API_KEY = 'k8Qz3vTn1pLw'\n")  # repo-guard: allow
        self.assertEqual(self.scanner.check_text("app/views.py", text), [])

    def test_private_keys_cannot_be_redacted(self):
        with self.assertRaises(RedactionError):
            self.redact("KEY = '''-----BEGIN RSA PRIVATE KEY-----\n")  # repo-guard: allow


if __name__ == "__main__":
    unittest.main()
