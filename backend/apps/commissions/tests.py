"""Commission maths — the numbers someone eventually gets paid on."""

from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import Address, User
from apps.catalog.models import Brand, Category, Product
from apps.commissions.models import (
    CategoryCommissionRate,
    CommissionEntry,
    CommissionSetting,
    OrderSupplierShare,
)
from apps.commissions.services import calculate_for_order, record_commission
from apps.orders.models import Cart, CartItem, Order, OrderItem
from apps.orders.services import create_order_from_cart
from apps.suppliers.models import CreditAccount


class CommissionCalculationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(phone="09121111111", password="Sample-Passw0rd!")
        self.buyer = User.objects.create_user(phone="09122222222", password="Sample-Passw0rd!")
        self.category = Category.objects.create(name="ترمز", slug="brake")
        self.other_category = Category.objects.create(name="موتور", slug="engine")
        self.brand = Brand.objects.create(name="سایپا", slug="saipa")

        setting = CommissionSetting.load()
        setting.beneficiary = self.owner
        setting.is_active = True
        setting.rate_for_customer = Decimal("10.00")
        setting.rate_for_shopkeeper = Decimal("10.00")
        setting.save()
        self.setting = setting

    def _product(self, name, category, price):
        # sku is unique in the schema, so every fixture product needs its own.
        self._sku = getattr(self, "_sku", 0) + 1
        return Product.objects.create(
            name=name,
            slug=name,
            sku=f"SKU-{self._sku:04d}",
            category=category,
            brand=self.brand,
            price=price,
            stock=100,
        )

    def _order(self, lines, discount=0, tax=0, shipping=0):
        order = Order.objects.create(
            user=self.buyer,
            ship_to_name="ت",
            ship_to_phone="09122222222",
            ship_to_city="تهران",
            ship_to_address="خیابان",
        )
        gross = 0
        for product, unit, qty in lines:
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                unit_price=unit,
                quantity=qty,
            )
            gross += unit * qty
        order.subtotal = gross
        order.discount_amount = discount
        order.tax_amount = tax
        order.shipping_cost = shipping
        order.total = gross - discount + tax + shipping
        order.save()
        return order

    def test_flat_rate(self):
        product = self._product("لنت", self.category, 100_000)
        order = self._order([(product, 100_000, 2)])
        base, amount, rate = calculate_for_order(order)
        self.assertEqual(base, 200_000)
        self.assertEqual(amount, 20_000)  # 10%
        self.assertEqual(rate, Decimal("10.00"))

    def test_category_override_wins_over_the_role_rate(self):
        CategoryCommissionRate.objects.create(category=self.category, rate=Decimal("25.00"))
        product = self._product("لنت", self.category, 100_000)
        order = self._order([(product, 100_000, 1)])
        _base, amount, _rate = calculate_for_order(order)
        self.assertEqual(amount, 25_000)

    def test_each_line_uses_its_own_category_rate(self):
        CategoryCommissionRate.objects.create(category=self.category, rate=Decimal("20.00"))
        brake = self._product("لنت", self.category, 100_000)
        engine = self._product("واشر", self.other_category, 100_000)
        order = self._order([(brake, 100_000, 1), (engine, 100_000, 1)])
        _base, amount, _rate = calculate_for_order(order)
        self.assertEqual(amount, 20_000 + 10_000)

    def test_a_coupon_reduces_the_commission_base_proportionally(self):
        """A discount must not be charged to one line, nor ignored entirely."""
        product = self._product("لنت", self.category, 100_000)
        order = self._order([(product, 100_000, 2)], discount=100_000)  # 50% off
        base, amount, _rate = calculate_for_order(order)
        self.assertEqual(base, 100_000)
        self.assertEqual(amount, 10_000)

    def test_vat_and_shipping_are_not_commissioned(self):
        """Tax belongs to the state and shipping to the courier, not to the sale."""
        product = self._product("لنت", self.category, 100_000)
        order = self._order([(product, 100_000, 2)], tax=20_000, shipping=50_000)
        base, amount, _rate = calculate_for_order(order)
        self.assertEqual(base, 200_000)
        self.assertEqual(amount, 20_000)

    def test_buyer_role_rate_is_used(self):
        self.setting.rate_for_customer = Decimal("15.00")
        self.setting.save()
        product = self._product("لنت", self.category, 100_000)
        order = self._order([(product, 100_000, 1)])
        _base, amount, rate = calculate_for_order(order)
        self.assertEqual((amount, rate), (15_000, Decimal("15.00")))

    def test_zero_value_order_earns_nothing(self):
        product = self._product("رایگان", self.category, 0)
        order = self._order([(product, 0, 1)])
        self.assertEqual(calculate_for_order(order), (0, 0, Decimal("0.00")))


class RecordCommissionTests(CommissionCalculationTests):
    def test_records_an_entry(self):
        product = self._product("لنت", self.category, 100_000)
        order = self._order([(product, 100_000, 1)])
        entry = record_commission(order)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.amount, 10_000)
        self.assertEqual(entry.beneficiary, self.owner)

    def test_is_idempotent(self):
        """A retried callback must not pay the owner twice."""
        product = self._product("لنت", self.category, 100_000)
        order = self._order([(product, 100_000, 1)])
        record_commission(order)
        record_commission(order)
        self.assertEqual(CommissionEntry.objects.filter(order=order).count(), 1)

    def test_disabled_feature_records_nothing(self):
        self.setting.is_active = False
        self.setting.save()
        product = self._product("لنت", self.category, 100_000)
        order = self._order([(product, 100_000, 1)])
        self.assertIsNone(record_commission(order))
        self.assertFalse(CommissionEntry.objects.exists())

    def test_beneficiary_buying_from_themselves_earns_nothing(self):
        product = self._product("لنت", self.category, 100_000)
        order = self._order([(product, 100_000, 1)])
        order.user = self.owner
        order.save()
        self.assertIsNone(record_commission(order))


class CommissionLifecycleTests(TestCase):
    """How the recorded commission follows an order from checkout onwards."""

    def setUp(self):
        self.owner = User.objects.create_superuser(phone="09121111111", password="Sample-Passw0rd!")
        self.supplier = User.objects.create_user(phone="09123333333", role=User.Role.SUPPLIER, is_approved=True)
        self.shop = User.objects.create_user(phone="09124444444", role=User.Role.SHOPKEEPER, is_approved=True)
        CreditAccount.objects.create(supplier=self.supplier, shop=self.shop, credit_limit=10_000_000)
        self.product = Product.objects.create(
            name="لنت",
            slug="brake-pad",
            sku="SKU-L1",
            category=Category.objects.create(name="ترمز", slug="brake"),
            brand=Brand.objects.create(name="سایپا", slug="saipa"),
            price=100_000,
            stock=10,
            supplier=self.supplier,
        )
        self.setting = CommissionSetting.load()
        self.setting.beneficiary = self.owner
        self.setting.save()

    def _credit_checkout(self):
        address = Address.objects.create(
            user=self.shop,
            title="انبار",
            receiver_name="ت",
            receiver_phone=self.shop.phone,
            province="تهران",
            city="تهران",
            line="خیابان",
        )
        cart = Cart.objects.create(user=self.shop)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        return create_order_from_cart(user=self.shop, address=address, payment_method=Order.PaymentMethod.CREDIT)

    def _move_to(self, order, status):
        order.status = status
        order.save(update_fields=["status"])

    def test_a_credit_order_is_recorded_at_checkout(self):
        order = self._credit_checkout()
        entry = CommissionEntry.objects.get(order=order)
        share = OrderSupplierShare.objects.get(order=order)
        self.assertEqual((entry.amount, entry.status), (10_000, CommissionEntry.Status.EARNED))
        self.assertEqual((share.supplier_net, share.status), (90_000, OrderSupplierShare.Status.EARNED))

    def test_a_credit_commission_waits_for_settlement_when_configured(self):
        self.setting.accrue_on_credit_order = False
        self.setting.save()
        order = self._credit_checkout()
        self._move_to(order, Order.Status.PROCESSING)  # shipping it does not pay for it
        self.assertEqual(CommissionEntry.objects.get(order=order).status, CommissionEntry.Status.PENDING)
        self.assertEqual(OrderSupplierShare.objects.get(order=order).status, OrderSupplierShare.Status.PENDING)

        order.credit_invoice.settle()
        self.assertEqual(CommissionEntry.objects.get(order=order).status, CommissionEntry.Status.EARNED)
        self.assertEqual(OrderSupplierShare.objects.get(order=order).status, OrderSupplierShare.Status.EARNED)

    def test_a_rate_change_does_not_rewrite_a_recognised_sale(self):
        order = self._credit_checkout()
        self.setting.default_rate = Decimal("20.00")
        self.setting.save()
        self._move_to(order, Order.Status.PROCESSING)
        entry = CommissionEntry.objects.get(order=order)
        share = OrderSupplierShare.objects.get(order=order)
        self.assertEqual((entry.amount, entry.effective_rate), (10_000, Decimal("10.00")))
        self.assertEqual((share.owner_commission, share.effective_rate), (10_000, Decimal("10.00")))

    def test_a_canceled_order_that_comes_back_is_recognised_afresh(self):
        order = self._credit_checkout()
        self._move_to(order, Order.Status.CANCELED)
        self.assertEqual(CommissionEntry.objects.get(order=order).status, CommissionEntry.Status.VOID)

        self.setting.default_rate = Decimal("20.00")
        self.setting.save()
        self._move_to(order, Order.Status.CREDIT)
        entry = CommissionEntry.objects.get(order=order)
        share = OrderSupplierShare.objects.get(order=order)
        self.assertEqual((entry.amount, entry.status), (20_000, CommissionEntry.Status.EARNED))
        self.assertEqual((share.owner_commission, share.status), (20_000, OrderSupplierShare.Status.EARNED))
