import unittest

from tools.repo_guard.models import Line
from tools.repo_guard.scanner import ALLOW_MARKER, Scanner, is_content_scanned
from tools.repo_guard.terms import TermMatcher


def rule_ids(findings):
    return {finding.rule_id for finding in findings}


class ScannerTestCase(unittest.TestCase):
    def setUp(self):
        self.scanner = Scanner(TermMatcher(digests=()))

    def line_rules(self, text, path="app/module.py"):
        return rule_ids(self.scanner.check_line(Line(path, 1, text)))

    def path_rules(self, path):
        return rule_ids(self.scanner.check_path(path))


class PathRuleTests(ScannerTestCase):
    def test_sensitive_files_are_blocked(self):
        expectations = {
            ".env": "env-file",
            "config/.env.production": "env-file",
            "db.sqlite3": "database-file",
            "dumps/shop.sql": "database-file",
            "backups/site.tar.gz": "backup-file",
            "backup/readme.txt": "backup-file",
            "settings.py.bak": "backup-file",
            "deploy/id_rsa": "key-file",
            "certs/server.pem": "key-file",
            "shop/local_settings.py": "local-settings",
            ".repo-guard.local": "local-settings",
            "media/sellers/card.jpg": "uploaded-media",
            "sellers_export.csv": "data-export",
        }
        for path, rule_id in expectations.items():
            with self.subTest(path=path):
                self.assertIn(rule_id, self.path_rules(path))

    def test_regular_source_files_are_allowed(self):
        for path in (".env.example", "shop/settings.py", "templates/base.html", "static/css/site.css"):
            with self.subTest(path=path):
                self.assertEqual(self.path_rules(path), set())

    def test_windows_separators_are_understood(self):
        self.assertIn("uploaded-media", self.path_rules("media\\products\\photo.jpg"))


class ContentRuleTests(ScannerTestCase):
    def test_phone_numbers(self):
        self.assertIn("mobile-number", self.line_rules('PHONE = "09351847264"'))  # repo-guard: allow
        self.assertIn("mobile-number", self.line_rules("+98 935 184 7264"))  # repo-guard: allow
        self.assertIn("mobile-number", self.line_rules("تماس: ۰۹۳۵۱۸۴۷۲۶۴"))  # repo-guard: allow
        self.assertIn("landline-number", self.line_rules("tel: 021-66554433"))  # repo-guard: allow
        self.assertEqual(self.line_rules('placeholder="09123456789"'), set())

    def test_personal_identifiers(self):
        self.assertIn("national-id", self.line_rules('"national_code": "0084126371"'))  # repo-guard: allow
        self.assertEqual(self.line_rules('"order_id": "0084126371"'), set())  # repo-guard: allow
        self.assertIn("bank-card", self.line_rules("card = '6037-9918-4726-3518'"))  # repo-guard: allow
        self.assertIn("sheba-number", self.line_rules("IR86 0170 0000 0021 8475 9360 04"))  # repo-guard: allow

    def test_infrastructure_details(self):
        self.assertIn("server-address", self.line_rules('HOST = "93.184.216.34"'))  # repo-guard: allow
        self.assertEqual(self.line_rules('HOST = "127.0.0.1"'), set())
        self.assertIn("credential-url", self.line_rules("postgres://shop:S3cr3tPw@db/shop"))  # repo-guard: allow
        self.assertIn("private-key", self.line_rules("-----BEGIN OPENSSH PRIVATE KEY-----"))  # repo-guard: allow

    def test_payment_and_sms_credentials(self):
        merchant = 'ZARINPAL_MERCHANT_ID = "3f2c1a9e-7b4d-4e8a-9c1f-5d6e7f8a9b0c"'  # repo-guard: allow
        self.assertIn("payment-merchant-id", self.line_rules(merchant))
        sms_url = "https://api.kavenegar.com/v1/4A7B2C9D1E3F5A6B7C8D/sms/send.json"  # repo-guard: allow
        self.assertIn("sms-api-key", self.line_rules(sms_url))

    def test_trust_seal_codes(self):
        seal = "<a href='https://trustseal.enamad.ir/?id=412345&Code=Qw3rTy'>"  # repo-guard: allow
        self.assertIn("trust-seal", self.line_rules(seal, "templates/footer.html"))
        templated = "<a href='https://trustseal.enamad.ir/?id={{ enamad_id }}'>"
        self.assertEqual(self.line_rules(templated, "templates/footer.html"), set())

    def test_hardcoded_secrets(self):
        assignment = "SECRET_KEY = 'django-insecure-k8Qz3vTn1p'"  # repo-guard: allow
        env_default = 'os.getenv("SMS_API_KEY", "k8Qz3vTn1pLw")'  # repo-guard: allow
        config_line = "DB_PASSWORD=k8Qz3vTn1p"  # repo-guard: allow
        self.assertIn("hardcoded-secret", self.line_rules(assignment))
        self.assertIn("env-default-secret", self.line_rules(env_default))
        self.assertIn("config-secret", self.line_rules(config_line, "deploy/.env.production"))

    def test_code_that_reads_secrets_from_the_environment_is_allowed(self):
        for text in (
            'SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]',
            'SMS_API_KEY = env("SMS_API_KEY", default="")',
            "password = forms.CharField(widget=forms.PasswordInput)",
            "'password': 'گذرواژه'",
            "PASSWORD_FIELD = 'new_password'",
            "success_url = reverse_lazy('password_reset_done')",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.line_rules(text, "shop/settings.py"), set())

    def test_config_files_may_reference_secrets(self):
        for path, text in (
            (".env.example", "DJANGO_SECRET_KEY=change-me"),
            (".env.example", "DB_PASSWORD="),
            ("deploy/backup.sh", 'export PGPASSWORD="$DB_PASSWORD"'),
            ("deploy/start.bat", "set DB_PASSWORD=%DB_PASSWORD%"),
            ("docker-compose.yml", "      POSTGRES_PASSWORD: ${{ secrets.DB_PASSWORD }}"),
        ):
            with self.subTest(path=path, text=text):
                self.assertEqual(self.line_rules(text, path), set())

    def test_allow_marker_suppresses_findings(self):
        self.assertEqual(self.line_rules(f"call 09351847264  # {ALLOW_MARKER}"), set())  # repo-guard: allow

    def test_excerpt_masks_the_value(self):
        findings = self.scanner.check_line(Line("app.py", 3, 'PHONE = "09351847264"'))  # repo-guard: allow
        self.assertEqual(len(findings), 1)
        self.assertNotIn("1847264", findings[0].excerpt)  # repo-guard: allow
        self.assertEqual(findings[0].location, "app.py:3")


class CommitMetadataTests(unittest.TestCase):
    def setUp(self):
        self.scanner = Scanner(TermMatcher(digests=()))

    def test_git_comment_lines_are_ignored(self):
        message = "Add catalogue filters\n\n# call 09351847264\n"  # repo-guard: allow
        self.assertEqual(self.scanner.check_commit_message("<message>", message), [])

    def test_message_body_is_checked(self):
        message = "Update footer\n\nContact 09351847264\n"  # repo-guard: allow
        findings = self.scanner.check_commit_message("<message>", message)
        self.assertEqual([(finding.rule_id, finding.line) for finding in findings], [("mobile-number", 3)])


class ContentScopeTests(unittest.TestCase):
    def test_vendored_and_minified_files_are_skipped(self):
        self.assertFalse(is_content_scanned("static/js/jquery.min.js"))
        self.assertFalse(is_content_scanned("node_modules/pkg/index.js"))
        self.assertTrue(is_content_scanned("static/js/cart.js"))


if __name__ == "__main__":
    unittest.main()
