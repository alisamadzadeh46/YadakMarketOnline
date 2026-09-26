"""KYC: who may register as what, and who may read the documents."""

import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import KYCDocument, User


def png_bytes():
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


class RegistrationRoleTests(TestCase):
    """Self-service registration must not be a path to privilege."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/accounts/register/"

    def _register(self, phone, role=None):
        payload = {"phone": phone, "password": "Sample-Passw0rd!", "full_name": "ت"}
        if role:
            payload["requested_role"] = role
        return self.client.post(self.url, payload)

    def test_customer_is_approved_immediately(self):
        self.assertEqual(self._register("09121111111").status_code, 201)
        user = User.objects.get(phone="09121111111")
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertTrue(user.is_approved)

    def test_shopkeeper_starts_unapproved(self):
        self.assertEqual(self._register("09122222222", "shopkeeper").status_code, 201)
        user = User.objects.get(phone="09122222222")
        self.assertEqual(user.role, User.Role.SHOPKEEPER)
        self.assertFalse(user.is_approved)

    def test_cannot_self_assign_supplier(self):
        self.assertEqual(self._register("09123333333", "supplier").status_code, 400)
        self.assertFalse(User.objects.filter(phone="09123333333").exists())

    def test_cannot_self_assign_admin(self):
        self.assertEqual(self._register("09124444444", "admin").status_code, 400)

    def test_cannot_self_assign_partner(self):
        self.assertEqual(self._register("09125555555", "partner").status_code, 400)


class KYCUploadTests(TestCase):
    """Uploads go to a throwaway MEDIA_ROOT — a test must never write into the
    directory the running site serves from."""

    def setUp(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        patcher = override_settings(MEDIA_ROOT=root)
        patcher.enable()
        self.addCleanup(patcher.disable)
        self.user = User.objects.create_user(phone="09126666666", password="Sample-Passw0rd!")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = "/api/accounts/kyc/upload/"

    def test_accepts_a_real_image(self):
        upload = SimpleUploadedFile("card.png", png_bytes(), content_type="image/png")
        response = self.client.post(self.url, {"doc_type": "national_card", "file": upload}, format="multipart")
        self.assertEqual(response.status_code, 201, response.data)

    def test_rejects_an_svg(self):
        payload = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        upload = SimpleUploadedFile("card.svg", payload, content_type="image/svg+xml")
        response = self.client.post(self.url, {"doc_type": "national_card", "file": upload}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(KYCDocument.objects.exists())

    def test_stores_under_private_with_an_opaque_name(self):
        upload = SimpleUploadedFile("my-national-card.png", png_bytes(), content_type="image/png")
        self.client.post(self.url, {"doc_type": "national_card", "file": upload}, format="multipart")
        doc = KYCDocument.objects.get()
        self.assertTrue(doc.file.name.startswith("private/kyc/"))
        # The client's own filename must not survive into the path.
        self.assertNotIn("my-national-card", doc.file.name)

    def test_response_hands_back_a_signed_url_not_the_raw_path(self):
        upload = SimpleUploadedFile("card.png", png_bytes(), content_type="image/png")
        response = self.client.post(self.url, {"doc_type": "national_card", "file": upload}, format="multipart")
        self.assertIn("media-protected", response.data["file"])

    def test_document_is_not_reachable_from_the_public_media_url(self):
        """The regression this whole change exists for."""
        upload = SimpleUploadedFile("card.png", png_bytes(), content_type="image/png")
        self.client.post(self.url, {"doc_type": "national_card", "file": upload}, format="multipart")
        doc = KYCDocument.objects.get()
        anonymous = APIClient()
        response = anonymous.get(f"/media/{doc.file.name}")
        self.assertIn(response.status_code, (403, 404))
