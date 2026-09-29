"""Marketplace access rules: suppliers only reach their own store, and
site-wide controls stay with the site owner."""

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import ShopkeeperProfile, User
from apps.catalog.models import Brand, Category, Product
from apps.commissions.models import CommissionSetting
from apps.commissions.services import calculate_for_order, record_supplier_shares
from apps.discounts.models import Coupon
from apps.notifications.models import SmsLog
from apps.notifications.tasks import send_sms
from apps.orders.models import Cart, CartItem, Order, OrderItem, PaymentReceipt


class MarketplaceFixture(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(phone="09120000000", password="Sample-Passw0rd!")
        self.supplier_a = User.objects.create_user(phone="09121111111", role=User.Role.SUPPLIER, is_approved=True)
        self.supplier_b = User.objects.create_user(phone="09122222222", role=User.Role.SUPPLIER, is_approved=True)
        self.buyer = User.objects.create_user(phone="09123333333")
        brand = Brand.objects.create(name="برند", slug="brand")
        self.category = Category.objects.create(name="دسته", slug="category")
        self.product_a = Product.objects.create(
            name="کالای الف",
            slug="a",
            sku="SKU-A",
            brand=brand,
            category=self.category,
            price=100_000,
            stock=10,
            supplier=self.supplier_a,
        )
        self.product_b = Product.objects.create(
            name="کالای ب",
            slug="b",
            sku="SKU-B",
            brand=brand,
            category=self.category,
            price=100_000,
            stock=10,
            supplier=self.supplier_b,
        )

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def order_with(self, *products, status=Order.Status.RECEIPT_UPLOADED):
        order = Order.objects.create(
            user=self.buyer,
            ship_to_name="ت",
            ship_to_phone=self.buyer.phone,
            ship_to_city="تهران",
            ship_to_address="خیابان",
            status=status,
        )
        for product in products:
            OrderItem.objects.create(
                order=order, product=product, product_name=product.name, unit_price=product.price, quantity=1
            )
        order.subtotal = order.total = 100_000 * len(products)
        order.save()
        return order


class SupplierOrderAccessTests(MarketplaceFixture):
    def test_supplier_only_lists_orders_with_their_products(self):
        own = self.order_with(self.product_a)
        self.order_with(self.product_b)
        numbers = [
            o["number"] for o in self.client_for(self.supplier_a).get("/api/orders/supplier/orders/").data["results"]
        ]
        self.assertEqual(numbers, [own.number])

    def test_supplier_cannot_act_on_another_suppliers_order(self):
        other = self.order_with(self.product_b)
        response = self.client_for(self.supplier_a).post(f"/api/orders/supplier/orders/{other.number}/cancel/")
        self.assertEqual(response.status_code, 404)

    def test_shared_order_is_managed_by_the_site_owner(self):
        shared = self.order_with(self.product_a, self.product_b, status=Order.Status.CONFIRMED)
        url = f"/api/orders/supplier/orders/{shared.number}/process/"
        self.assertEqual(self.client_for(self.supplier_a).post(url).status_code, 403)
        self.assertEqual(self.client_for(self.admin).post(url).status_code, 200)

    def test_status_transitions_are_enforced(self):
        unpaid = self.order_with(self.product_a, status=Order.Status.PENDING_PAYMENT)
        client = self.client_for(self.supplier_a)
        self.assertEqual(client.post(f"/api/orders/supplier/orders/{unpaid.number}/ship/").status_code, 400)
        self.assertEqual(client.post(f"/api/orders/supplier/orders/{unpaid.number}/confirm/").status_code, 400)

    def test_supplier_confirms_their_own_receipt(self):
        order = self.order_with(self.product_a)
        PaymentReceipt.objects.create(order=order, image="private/receipts/x.png")
        response = self.client_for(self.supplier_a).post(f"/api/orders/supplier/orders/{order.number}/confirm/")
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CONFIRMED)

    def test_sales_report_is_scoped_to_the_supplier(self):
        self.order_with(self.product_a, status=Order.Status.CONFIRMED)
        self.order_with(self.product_b, self.product_b, status=Order.Status.CONFIRMED)
        report = self.client_for(self.supplier_a).get("/api/suppliers/reports/?days=7").data
        self.assertEqual((report["revenue"], report["orders"]), (100_000, 1))
        site = self.client_for(self.admin).get("/api/suppliers/reports/?days=7").data
        self.assertEqual((site["revenue"], site["orders"]), (300_000, 2))


class SiteAdminOnlyTests(MarketplaceFixture):
    def test_site_wide_controls_are_refused_to_suppliers(self):
        client = self.client_for(self.supplier_a)
        for url in (
            "/api/accounts/supplier/shops/",
            "/api/suppliers/sms-logs/",
            "/api/cms/manage/contacts/",
            "/api/cms/manage/subscribers/",
            "/api/cms/manage/slides/",
            "/api/blog/manage/posts/",
            "/api/catalog/manage/categories/",
            "/api/catalog/manage/brands/",
        ):
            with self.subTest(url=url):
                self.assertEqual(client.get(url).status_code, 403)

    def test_suppliers_may_add_but_not_change_shared_colours(self):
        client = self.client_for(self.supplier_a)
        created = client.post("/api/catalog/manage/colors/", {"name": "زرشکی"})
        self.assertEqual(created.status_code, 201)
        self.assertEqual(client.delete(f"/api/catalog/manage/colors/{created.data['id']}/").status_code, 403)

    def test_kyc_approval_is_site_admin_only(self):
        shop = User.objects.create_user(phone="09124444444", role=User.Role.SHOPKEEPER)
        profile = ShopkeeperProfile.objects.create(user=shop, shop_name="فروشگاه")
        url = f"/api/accounts/supplier/shops/{profile.id}/approve/"
        self.assertEqual(self.client_for(self.supplier_a).post(url).status_code, 403)
        self.assertEqual(self.client_for(self.admin).post(url).status_code, 200)

    def test_category_in_use_answers_conflict_not_server_error(self):
        response = self.client_for(self.admin).delete(f"/api/catalog/manage/categories/{self.category.id}/")
        self.assertEqual(response.status_code, 409)


class VerificationCodeLogTests(TestCase):
    def test_codes_are_masked_in_the_sms_log(self):
        send_sms.apply(args=("09125555555", "کد بازیابی رمز عبور: 482913"), kwargs={"kind": SmsLog.Kind.VERIFICATION})
        log = SmsLog.objects.get()
        self.assertNotIn("482913", log.message)
        self.assertIn("******", log.message)

    def test_other_messages_are_logged_as_sent(self):
        send_sms.apply(args=("09125555555", "سفارش 1234 ارسال شد"), kwargs={"kind": SmsLog.Kind.ORDER})
        self.assertIn("1234", SmsLog.objects.get().message)


class SupplierCouponTests(MarketplaceFixture):
    def setUp(self):
        super().setUp()
        from datetime import timedelta

        from django.utils import timezone

        self.coupon = Coupon.objects.create(
            code="SUPA",
            owner=self.supplier_a,
            kind=Coupon.Kind.PERCENT,
            value=50,
            valid_to=timezone.now() + timedelta(days=1),
        )
        cart = Cart.objects.create(user=self.buyer)
        CartItem.objects.create(cart=cart, product=self.product_a, quantity=1)
        CartItem.objects.create(cart=cart, product=self.product_b, quantity=1)

    def test_supplier_coupon_only_discounts_their_lines(self):
        response = self.client_for(self.buyer).post("/api/discounts/validate/", {"code": "SUPA", "amount": 200_000})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["discount"], 50_000)  # 50% of supplier A's 100,000 only

    def test_supplier_coupon_does_not_touch_other_suppliers_share(self):
        setting = CommissionSetting.load()
        setting.beneficiary = self.admin
        setting.save()
        # The coupon is part of the order before it is confirmed, as at checkout.
        order = self.order_with(self.product_a, self.product_b)
        order.discount_amount = 50_000
        order.discount_supplier = self.supplier_a
        order.status = Order.Status.CONFIRMED
        order.save()
        shares = {share.supplier_id: share for share in record_supplier_shares(order)}
        self.assertEqual(shares[self.supplier_a.id].gross_amount, 50_000)
        self.assertEqual(shares[self.supplier_b.id].gross_amount, 100_000)
        self.assertEqual(calculate_for_order(order)[0], 150_000)

    def test_suppliers_only_see_their_own_coupons(self):
        rows = self.client_for(self.supplier_b).get("/api/discounts/manage/coupons/").data["results"]
        self.assertEqual(rows, [])
