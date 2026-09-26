"""Gateway verification — the code path where getting it wrong ships free goods."""

from unittest.mock import patch

from django.test import TestCase

from apps.accounts.models import User
from apps.orders.models import Order
from apps.payments.models import PaymentGatewaySettings, PaymentTransaction
from apps.payments.services import BitPayGateway, ZarinpalGateway


class BitPayVerifyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="09121111111", password="Sample-Passw0rd!")
        self.order = Order.objects.create(
            user=self.user,
            ship_to_name="ت",
            ship_to_phone="09121111111",
            ship_to_city="تهران",
            ship_to_address="خیابان",
            total=500_000,
        )
        self.txn = PaymentTransaction.objects.create(
            order=self.order,
            gateway=PaymentGatewaySettings.Gateway.BITPAY,
            amount=500_000,
            authority="1234",
        )
        self.cfg = PaymentGatewaySettings.load()

    def _verify(self, payload):
        with patch("apps.payments.services._post_json", return_value=payload):
            return BitPayGateway().verify(self.txn, self.cfg, {"trans_id": "9", "id_get": "1234"})

    def test_accepts_a_matching_amount(self):
        # Store keeps Toman, BitPay bills Rial: 500,000 Toman == 5,000,000 Rial.
        result = self._verify({"status": 1, "amount": 5_000_000, "cardNum": "6037****"})
        self.assertTrue(result["ok"])

    def test_rejects_an_underpaid_charge(self):
        """A 1,000 Toman payment must not settle a 500,000 Toman order."""
        result = self._verify({"status": 1, "amount": 10_000})
        self.assertFalse(result["ok"])

    def test_rejects_a_failed_status(self):
        self.assertFalse(self._verify({"status": -1, "amount": 5_000_000})["ok"])

    def test_accepts_already_verified_code_11(self):
        self.assertTrue(self._verify({"status": 11, "amount": 5_000_000})["ok"])

    def test_missing_amount_does_not_block_a_valid_payment(self):
        """BitPay has omitted `amount` in the past; status stays authoritative."""
        self.assertTrue(self._verify({"status": 1})["ok"])


class ZarinpalVerifyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="09122222222", password="Sample-Passw0rd!")
        self.order = Order.objects.create(
            user=self.user,
            ship_to_name="ت",
            ship_to_phone="09122222222",
            ship_to_city="تهران",
            ship_to_address="خیابان",
            total=200_000,
        )
        self.txn = PaymentTransaction.objects.create(
            order=self.order,
            gateway=PaymentGatewaySettings.Gateway.ZARINPAL,
            amount=200_000,
            authority="A0001",
        )
        self.cfg = PaymentGatewaySettings.load()

    def test_cancelled_payment_never_calls_the_bank(self):
        with patch("apps.payments.services._post_json") as post:
            result = ZarinpalGateway().verify(self.txn, self.cfg, {"Status": "NOK"})
        post.assert_not_called()
        self.assertFalse(result["ok"])

    def test_successful_verify(self):
        with patch(
            "apps.payments.services._post_json",
            return_value={"data": {"code": 100, "ref_id": 777, "card_pan": "6037****"}},
        ):
            result = ZarinpalGateway().verify(self.txn, self.cfg, {"Status": "OK"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["ref_id"], "777")

    def test_amount_sent_to_verify_comes_from_the_transaction(self):
        """Never from the callback: that is attacker-controlled."""
        with patch("apps.payments.services._post_json", return_value={"data": {"code": 100}}) as post:
            ZarinpalGateway().verify(self.txn, self.cfg, {"Status": "OK", "amount": "1"})
        self.assertEqual(post.call_args[0][1]["amount"], 200_000 * 10)


class LatePaymentTests(TestCase):
    """A payment that completes after the expiry sweep canceled its order."""

    def setUp(self):
        from datetime import timedelta

        from django.utils import timezone

        from apps.catalog.models import Brand, Category, Product
        from apps.orders.models import OrderItem

        self.user = User.objects.create_user(phone="09123333333", password="Sample-Passw0rd!")
        brand = Brand.objects.create(name="برند", slug="brand")
        category = Category.objects.create(name="دسته", slug="category")
        self.product = Product.objects.create(
            name="کالا", slug="item", sku="SKU-P1", brand=brand, category=category, price=100_000, stock=2
        )
        self.order = Order.objects.create(
            user=self.user,
            ship_to_name="ت",
            ship_to_phone="09123333333",
            ship_to_city="تهران",
            ship_to_address="خیابان",
            total=100_000,
            payment_method=Order.PaymentMethod.ONLINE,
            receipt_deadline=timezone.now() - timedelta(minutes=1),
        )
        OrderItem.objects.create(
            order=self.order, product=self.product, product_name="کالا", unit_price=100_000, quantity=1
        )
        self.product.stock = 1  # one unit is reserved by the order
        self.product.save()
        self.txn = PaymentTransaction.objects.create(
            order=self.order,
            gateway=PaymentGatewaySettings.Gateway.ZARINPAL,
            amount=100_000,
            authority="A-1",
        )

    def _pay(self):
        from apps.payments.services import handle_callback

        verified = {"ok": True, "trans_id": "1", "ref_id": "1", "card_number": "", "raw": {}}
        with patch.object(ZarinpalGateway, "verify", return_value=verified):
            return handle_callback("zarinpal", {"Authority": "A-1", "Status": "OK"})

    def test_expired_order_is_revived_when_stock_remains(self):
        from apps.orders.tasks import close_expired_orders

        close_expired_orders()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CANCELED)

        order, ok = self._pay()
        self.assertTrue(ok)
        self.assertEqual(order.status, Order.Status.CONFIRMED)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)

    def test_expired_order_without_stock_is_reported_for_refund(self):
        from apps.orders.tasks import close_expired_orders

        close_expired_orders()
        self.product.refresh_from_db()
        self.product.stock = 0  # sold to someone else meanwhile
        self.product.save()

        order, ok = self._pay()
        self.assertFalse(ok)
        self.assertEqual(order.status, Order.Status.CANCELED)
        self.txn.refresh_from_db()
        self.assertEqual(self.txn.status, PaymentTransaction.Status.SUCCESS)
