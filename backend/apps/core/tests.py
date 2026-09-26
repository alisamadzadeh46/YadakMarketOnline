"""Private-media plumbing: signing, expiry, and refusing to serve public paths."""

import os
import shutil
import tempfile

from django.core.signing import BadSignature
from django.http import Http404
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core import protected


class SignPathTests(TestCase):
    def test_round_trip(self):
        token = protected.sign_path("private/kyc/7/abc.png")
        self.assertEqual(protected.unsign_path(token), "private/kyc/7/abc.png")

    def test_tampered_token_is_rejected(self):
        token = protected.sign_path("private/kyc/7/abc.png")
        # Swap the payload for another user's directory, keep the signature.
        forged = token.replace("kyc/7/", "kyc/8/")
        with self.assertRaises(BadSignature):
            protected.unsign_path(forged)

    def test_expired_token_is_rejected(self):
        token = protected.sign_path("private/kyc/7/abc.png")
        with self.assertRaises(BadSignature):  # SignatureExpired subclasses it
            protected.unsign_path(token, ttl=-1)

    def test_is_private(self):
        self.assertTrue(protected.is_private("private/receipts/YM250100001/x.jpg"))
        self.assertFalse(protected.is_private("products/x.jpg"))


class ProtectedUrlTests(TestCase):
    def test_public_path_gets_a_plain_media_url(self):
        url = protected.protected_url(None, "products/x.jpg")
        self.assertIn("products/x.jpg", url)
        self.assertNotIn("media-protected", url)

    def test_private_path_gets_a_signed_url(self):
        url = protected.protected_url(None, "private/kyc/7/x.png")
        self.assertIn(reverse("protected_media"), url)
        self.assertIn("t=", url)
        # The token is signed, not encrypted — like an S3 presigned URL, the
        # path stays visible. What must hold is that it cannot be swapped for
        # another one, which is why the filename is a random uuid rather than
        # anything guessable.
        token = url.split("t=", 1)[1]
        self.assertNotEqual(token, "private/kyc/7/x.png")
        self.assertGreater(len(token), len("private/kyc/7/x.png") + 20)


class ServePrivateTests(TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "private", "kyc"), exist_ok=True)
        with open(os.path.join(self.root, "private", "kyc", "doc.txt"), "wb") as fh:
            fh.write(b"secret")
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_refuses_to_serve_a_public_path(self):
        """Even a validly signed token may only point inside private/."""
        with self.assertRaises(Http404):
            protected.serve_private("products/x.jpg")

    def test_path_traversal_is_refused(self):
        with self.assertRaises(Http404):
            protected.serve_private("private/../../etc/passwd")

    def test_serves_the_file_without_nginx(self):
        with override_settings(MEDIA_ROOT=self.root, USE_X_ACCEL_REDIRECT=False):
            response = protected.serve_private("private/kyc/doc.txt")
        self.assertEqual(b"".join(response.streaming_content), b"secret")

    def test_delegates_to_nginx_when_enabled(self):
        with override_settings(
            MEDIA_ROOT=self.root,
            USE_X_ACCEL_REDIRECT=True,
            X_ACCEL_MEDIA_PREFIX="/protected-media/",
        ):
            response = protected.serve_private("private/kyc/doc.txt")
        self.assertEqual(response["X-Accel-Redirect"], "/protected-media/kyc/doc.txt")
        self.assertEqual(response.content, b"")


class ProtectedViewTests(TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "private"), exist_ok=True)
        with open(os.path.join(self.root, "private", "doc.txt"), "wb") as fh:
            fh.write(b"secret")
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_missing_token_is_404(self):
        self.assertEqual(self.client.get(reverse("protected_media")).status_code, 404)

    def test_garbage_token_is_404(self):
        url = reverse("protected_media") + "?t=not-a-real-token"
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_valid_token_serves(self):
        token = protected.sign_path("private/doc.txt")
        with override_settings(MEDIA_ROOT=self.root, USE_X_ACCEL_REDIRECT=False):
            response = self.client.get(reverse("protected_media"), {"t": token})
        self.assertEqual(response.status_code, 200)


class JalaliCalendarTests(TestCase):
    def test_conversion_and_month_start(self):
        from datetime import date

        from apps.core.utils import gregorian_to_jalali, jalali_month_start, to_jalali

        self.assertEqual(gregorian_to_jalali(2024, 3, 20), (1403, 1, 1))
        self.assertEqual(gregorian_to_jalali(2026, 9, 27), (1405, 7, 5))
        self.assertEqual(to_jalali(date(2026, 9, 27)), "۱۴۰۵/۰۷/۰۵")
        self.assertEqual(jalali_month_start(date(2026, 9, 27)), date(2026, 9, 23))
