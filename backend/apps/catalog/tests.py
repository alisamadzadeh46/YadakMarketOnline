"""Colour-tagged images and "other options" (variant siblings) on the
product detail payload."""

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Brand, Category, Color, Product, ProductImage


class ProductImageColorTests(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name="برند", slug="b1")
        self.category = Category.objects.create(name="دسته", slug="c1")
        self.black = Color.objects.create(name="مشکی", hex_code="#111111")
        self.product = Product.objects.create(
            name="آینه بغل",
            slug="mirror",
            sku="SKU-I1",
            brand=self.brand,
            category=self.category,
            price=10_000,
            stock=5,
        )
        self.product.colors.add(self.black)

    def test_detail_payload_reports_the_images_colour(self):
        ProductImage.objects.create(product=self.product, color=self.black, order=0)
        ProductImage.objects.create(product=self.product, order=1)  # shared, no colour
        response = APIClient().get(f"/api/catalog/products/{self.product.slug}/")
        images = response.data["images"]
        self.assertEqual(images[0]["color"], self.black.id)
        self.assertIsNone(images[1]["color"])


class VariantSiblingTests(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name="برند۲", slug="b2")
        self.category = Category.objects.create(name="دسته۲", slug="c2")

    def _product(self, sku, group, label, price, active=True):
        return Product.objects.create(
            name=f"سپر {label}",
            slug=f"soper-{sku}",
            sku=sku,
            brand=self.brand,
            category=self.category,
            price=price,
            stock=5,
            is_active=active,
            variant_group=group,
            variant_label=label,
        )

    def test_siblings_appear_ordered_by_price_with_the_current_one_flagged(self):
        cheap = self._product("V1", "soper-405", "دیاق پلیمری", 100_000)
        pricey = self._product("V2", "soper-405", "دیاق فلزی", 150_000)
        response = APIClient().get(f"/api/catalog/products/{cheap.slug}/")
        variants = response.data["variants"]
        self.assertEqual([v["id"] for v in variants], [cheap.id, pricey.id])
        self.assertTrue(variants[0]["is_current"])
        self.assertFalse(variants[1]["is_current"])

    def test_unrelated_products_are_not_siblings(self):
        a = self._product("V3", "group-a", "الف", 100_000)
        self._product("V4", "group-b", "ب", 100_000)
        response = APIClient().get(f"/api/catalog/products/{a.slug}/")
        self.assertEqual(len(response.data["variants"]), 1)

    def test_no_group_means_no_variants(self):
        solo = Product.objects.create(
            name="تکی",
            slug="solo",
            sku="SKU-SOLO",
            brand=self.brand,
            category=self.category,
            price=10_000,
            stock=5,
        )
        response = APIClient().get(f"/api/catalog/products/{solo.slug}/")
        self.assertEqual(response.data["variants"], [])

    def test_an_unpublished_sibling_is_hidden(self):
        visible = self._product("V5", "group-c", "الف", 100_000)
        self._product("V6", "group-c", "ب", 120_000, active=False)
        response = APIClient().get(f"/api/catalog/products/{visible.slug}/")
        self.assertEqual(len(response.data["variants"]), 1)


class SupplierColorManagementTests(TestCase):
    """A plain supplier — not just the site owner — must be able to define
    colours and tag photos with them, since they are the ones with the
    photos."""

    def setUp(self):
        from apps.accounts.models import User

        self.password = "Sample-Passw0rd!"
        self.supplier = User.objects.create_user(phone="09121111111", password=self.password)
        self.supplier.role = "supplier"
        self.supplier.save()
        self.brand = Brand.objects.create(name="برند س", slug="bs")
        self.category = Category.objects.create(name="دسته س", slug="cs")
        self.product = Product.objects.create(
            name="سپر س",
            slug="separ-s",
            sku="SKU-S1",
            brand=self.brand,
            category=self.category,
            price=10_000,
            stock=5,
            supplier=self.supplier,
        )
        self.client = APIClient()
        resp = self.client.post("/api/accounts/token/", {"phone": self.supplier.phone, "password": self.password})
        self.client.credentials(HTTP_X_CSRFTOKEN=resp.data["csrf_token"])

    def test_supplier_can_create_a_colour(self):
        r = self.client.post("/api/catalog/manage/colors/", {"name": "بژ طلایی", "hex_code": "#C9A961"})
        self.assertIn(r.status_code, (200, 201), r.data)
        self.assertTrue(Color.objects.filter(name="بژ طلایی").exists())

    def test_creating_an_existing_colour_reuses_it(self):
        """Otherwise the swatch list fills with duplicates of the same colour."""
        existing = Color.objects.create(name="مشکی", hex_code="#111111")
        r = self.client.post("/api/catalog/manage/colors/", {"name": "مشکی"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["id"], existing.id)
        self.assertEqual(Color.objects.filter(name="مشکی").count(), 1)

    def test_supplier_can_set_the_products_colours(self):
        black = Color.objects.create(name="مشکی۳", hex_code="#111111")
        r = self.client.patch(
            f"/api/catalog/manage/products/{self.product.id}/",
            {"colors": [black.id]},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(list(self.product.colors.values_list("id", flat=True)), [black.id])

    def test_an_image_can_be_retagged_to_another_colour(self):
        black = Color.objects.create(name="مشکی۴", hex_code="#111111")
        self.product.colors.add(black)
        img = ProductImage.objects.create(product=self.product, order=0)
        r = self.client.patch(
            f"/api/catalog/manage/products/{self.product.id}/images/{img.id}/",
            {"color": black.id},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.data)
        img.refresh_from_db()
        self.assertEqual(img.color, black)

    def test_an_image_can_be_untagged_back_to_all_colours(self):
        black = Color.objects.create(name="مشکی۵", hex_code="#111111")
        self.product.colors.add(black)
        img = ProductImage.objects.create(product=self.product, color=black, order=0)
        r = self.client.patch(
            f"/api/catalog/manage/products/{self.product.id}/images/{img.id}/",
            {"color": ""},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        img.refresh_from_db()
        self.assertIsNone(img.color)

    def test_a_colour_the_product_does_not_offer_is_rejected(self):
        stray = Color.objects.create(name="سرخابی", hex_code="#C0397A")
        img = ProductImage.objects.create(product=self.product, order=0)
        r = self.client.patch(
            f"/api/catalog/manage/products/{self.product.id}/images/{img.id}/",
            {"color": stray.id},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        img.refresh_from_db()
        self.assertIsNone(img.color)

    def test_a_buyer_cannot_create_colours(self):
        from apps.accounts.models import User

        buyer = User.objects.create_user(phone="09122222222", password=self.password)
        client = APIClient()
        resp = client.post("/api/accounts/token/", {"phone": buyer.phone, "password": self.password})
        client.credentials(HTTP_X_CSRFTOKEN=resp.data["csrf_token"])
        r = client.post("/api/catalog/manage/colors/", {"name": "رنگ قاچاقی"})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Color.objects.filter(name="رنگ قاچاقی").exists())


class CategoryProductCountTests(TestCase):
    """The menu count must match what the shop grid can actually show."""

    def setUp(self):
        self.brand = Brand.objects.create(name="برند ش", slug="bsh")
        self.category = Category.objects.create(name="سپر", slug="bumper-cat")

    def _product(self, sku, active):
        return Product.objects.create(
            name=f"سپر {sku}",
            slug=f"sepr-{sku}",
            sku=sku,
            brand=self.brand,
            category=self.category,
            price=1000,
            stock=1,
            is_active=active,
        )

    def test_unpublished_products_are_not_counted(self):
        self._product("C1", True)
        self._product("C2", False)
        self._product("C3", False)
        data = APIClient().get("/api/catalog/categories/").data
        row = next(c for c in data if c["slug"] == "bumper-cat")
        # Three rows exist, one is published — the chip must say 1, not 3,
        # or the menu advertises stock the shop cannot show.
        self.assertEqual(row["product_count"], 1)

    def test_count_matches_the_shop_listing(self):
        for i in range(4):
            self._product(f"D{i}", i < 2)
        cats = APIClient().get("/api/catalog/categories/").data
        row = next(c for c in cats if c["slug"] == "bumper-cat")
        listing = APIClient().get(f"/api/catalog/products/?category={self.category.id}").data
        self.assertEqual(row["product_count"], listing["count"])
