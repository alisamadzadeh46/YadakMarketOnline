"""Cookie-based JWT: the token must never be reachable from JavaScript."""

from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User


class CookieLoginTests(TestCase):
    def setUp(self):
        self.password = "Sample-Passw0rd!"
        self.user = User.objects.create_user(phone="09121111111", password=self.password)
        self.client = APIClient(enforce_csrf_checks=True)

    def login(self):
        return self.client.post("/api/accounts/token/", {"phone": self.user.phone, "password": self.password})

    def test_login_sets_httponly_cookies(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        access = response.cookies[settings.JWT_ACCESS_COOKIE]
        refresh = response.cookies[settings.JWT_REFRESH_COOKIE]
        self.assertTrue(access["httponly"])
        self.assertTrue(refresh["httponly"])
        self.assertEqual(access["samesite"], "Lax")

    def test_the_flag_cookie_is_readable_but_holds_no_token(self):
        response = self.login()
        flag = response.cookies[settings.JWT_FLAG_COOKIE]
        self.assertFalse(flag["httponly"])
        self.assertEqual(flag.value, "1")

    def test_no_token_in_the_response_body(self):
        """The regression this change exists for."""
        response = self.login()
        self.assertNotIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        self.assertIn("user", response.data)

    def test_bad_credentials_set_nothing(self):
        response = self.client.post("/api/accounts/token/", {"phone": self.user.phone, "password": "Wrong-sample-pass"})
        self.assertEqual(response.status_code, 401)
        self.assertNotIn(settings.JWT_ACCESS_COOKIE, response.cookies)

    def test_cookie_authenticates_a_later_request(self):
        self.login()
        response = self.client.get("/api/accounts/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["phone"], self.user.phone)

    def test_anonymous_request_is_rejected(self):
        self.assertEqual(self.client.get("/api/accounts/me/").status_code, 401)


class CsrfTests(TestCase):
    """A cookie rides along automatically, so writes need a second factor."""

    def setUp(self):
        self.password = "Sample-Passw0rd!"
        self.user = User.objects.create_user(phone="09122222222", password=self.password)
        self.client = APIClient(enforce_csrf_checks=True)
        self.login_response = self.client.post(
            "/api/accounts/token/", {"phone": self.user.phone, "password": self.password}
        )

    def test_write_without_a_csrf_token_is_refused(self):
        response = self.client.post(
            "/api/accounts/addresses/",
            {
                "title": "خانه",
                "receiver_name": "ت",
                "receiver_phone": "09127777777",
                "province": "تهران",
                "city": "تهران",
                "line": "خیابان ولیعصر",
                "postal_code": "1234567890",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("CSRF", str(response.data))

    def test_write_with_the_csrf_token_succeeds(self):
        token = self.login_response.data["csrf_token"]
        response = self.client.post(
            "/api/accounts/addresses/",
            {
                "title": "خانه",
                "receiver_name": "ت",
                "receiver_phone": "09127777777",
                "province": "تهران",
                "city": "تهران",
                "line": "خیابان ولیعصر",
                "postal_code": "1234567890",
            },
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertIn(response.status_code, (200, 201), response.data)

    def test_reads_need_no_csrf_token(self):
        self.assertEqual(self.client.get("/api/accounts/me/").status_code, 200)


class RefreshAndLogoutTests(TestCase):
    def setUp(self):
        self.password = "Sample-Passw0rd!"
        self.user = User.objects.create_user(phone="09123333333", password=self.password)
        self.client = APIClient()
        self.client.post("/api/accounts/token/", {"phone": self.user.phone, "password": self.password})

    def test_refresh_issues_a_new_access_cookie(self):
        response = self.client.post("/api/accounts/token/refresh/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(settings.JWT_ACCESS_COOKIE, response.cookies)
        self.assertNotIn("access", response.data)

    def test_refresh_without_a_cookie_is_401(self):
        anonymous = APIClient()
        self.assertEqual(anonymous.post("/api/accounts/token/refresh/").status_code, 401)

    def test_logout_clears_the_cookies(self):
        response = self.client.post("/api/accounts/logout/")
        self.assertEqual(response.status_code, 200)
        for name in (settings.JWT_ACCESS_COOKIE, settings.JWT_REFRESH_COOKIE, settings.JWT_FLAG_COOKIE):
            self.assertEqual(response.cookies[name].value, "")

    def test_session_is_dead_after_logout(self):
        self.client.post("/api/accounts/logout/")
        self.assertEqual(self.client.get("/api/accounts/me/").status_code, 401)


class HeaderAuthStillWorksTests(TestCase):
    """API clients and scripts keep using the header; nothing stores it."""

    def setUp(self):
        self.user = User.objects.create_user(phone="09124444444", password="Sample-Passw0rd!")

    def test_bearer_header_authenticates(self):
        from rest_framework_simplejwt.tokens import RefreshToken

        access = RefreshToken.for_user(self.user).access_token
        client = APIClient(enforce_csrf_checks=True)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        self.assertEqual(client.get("/api/accounts/me/").status_code, 200)

    def test_header_writes_need_no_csrf_token(self):
        """An attacker's page cannot set a header, so CSRF does not apply."""
        from rest_framework_simplejwt.tokens import RefreshToken

        access = RefreshToken.for_user(self.user).access_token
        client = APIClient(enforce_csrf_checks=True)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = client.post(
            "/api/accounts/addresses/",
            {
                "title": "خانه",
                "receiver_name": "ت",
                "receiver_phone": "09127777777",
                "province": "تهران",
                "city": "تهران",
                "line": "خیابان ولیعصر",
                "postal_code": "1234567890",
            },
        )
        self.assertIn(response.status_code, (200, 201), response.data)


class ResetCodeGuessingTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.addCleanup(cache.clear)

    def test_code_guesses_are_limited_per_phone(self):
        client = APIClient()
        statuses = [
            client.post(
                "/api/accounts/password-reset/confirm/",
                {"phone": "09125555555", "code": f"{guess:06d}", "new_password": "Sample-Passw0rd!"},
                REMOTE_ADDR=f"10.0.0.{guess}",  # a different address for every guess
            ).status_code
            for guess in range(12)
        ]
        self.assertEqual(statuses[:10], [400] * 10)
        self.assertEqual(statuses[10:], [429, 429])
