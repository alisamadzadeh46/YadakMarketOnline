import unittest

from tools.repo_guard import validators


class PlaceholderTests(unittest.TestCase):
    def test_documented_placeholders_are_recognised(self):
        for value in ("change-me", "<your-api-key>", "{{ token }}", "xxxxxxxx", "000000", "example-key"):
            with self.subTest(value=value):
                self.assertTrue(validators.is_placeholder(value))

    def test_random_values_are_not_placeholders(self):
        self.assertFalse(validators.is_placeholder("k8Qz3vTn1pLw"))

    def test_django_style_keys_with_symbols_are_not_placeholders(self):
        self.assertFalse(validators.is_placeholder("django-insecure-a$b%c(d)e!f"))


class DummyNumberTests(unittest.TestCase):
    def test_repeated_and_sequential_numbers_are_dummies(self):
        for digits in ("09120000000", "09123456789", "09129876543"):
            with self.subTest(digits=digits):
                self.assertTrue(validators.is_dummy_number(digits))

    def test_realistic_number_is_not_a_dummy(self):
        self.assertFalse(validators.is_dummy_number("09351847264"))  # repo-guard: allow


class ChecksumTests(unittest.TestCase):
    def test_national_id_checksum(self):
        self.assertTrue(validators.is_valid_national_id("0084126371"))  # repo-guard: allow
        self.assertFalse(validators.is_valid_national_id("0084126372"))
        self.assertFalse(validators.is_valid_national_id("1111111111"))

    def test_luhn(self):
        self.assertTrue(validators.passes_luhn("6037991847263518"))  # repo-guard: allow
        self.assertFalse(validators.passes_luhn("6037991847263519"))
        self.assertFalse(validators.passes_luhn("0000000000000000"))

    def test_iban(self):
        self.assertTrue(validators.is_valid_iban("IR860170000000218475936004"))  # repo-guard: allow
        self.assertTrue(validators.is_valid_iban("IR86 0170 0000 0021 8475 9360 04"))  # repo-guard: allow
        self.assertFalse(validators.is_valid_iban("IR870170000000218475936004"))


class AddressTests(unittest.TestCase):
    def test_public_ip(self):
        self.assertTrue(validators.is_public_ip("93.184.216.34"))  # repo-guard: allow
        for address in ("127.0.0.1", "10.0.0.5", "192.168.1.10", "0.0.0.0", "999.1.1.1"):
            with self.subTest(address=address):
                self.assertFalse(validators.is_public_ip(address))

    def test_email(self):
        self.assertTrue(validators.is_real_email("shop.owner@gmail.com"))  # repo-guard: allow
        for address in ("admin@example.com", "logo@2x.png", "git@github.com", "your-name@gmail.com"):
            with self.subTest(address=address):
                self.assertFalse(validators.is_real_email(address))


if __name__ == "__main__":
    unittest.main()
