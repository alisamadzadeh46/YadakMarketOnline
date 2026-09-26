"""Commission maths — the numbers someone eventually gets paid on."""

from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import User
from apps.catalog.models import Brand, Category, Product
from apps.commissions.models import (
    CategoryCommissionRate,
    CommissionEntry,
    CommissionSetting,
)
from apps.commissions.services import calculate_for_order, record_commission
from apps.orders.models import Order, OrderItem


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
