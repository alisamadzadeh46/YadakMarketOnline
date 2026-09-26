"""Colour variants in the cart/checkout flow — the part of this feature where
getting it wrong means charging the wrong line or losing a line silently."""

from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import Address, User
from apps.catalog.models import Brand, Category, Color, Product

from .models import Cart, CartItem, Order
from .services import (
    clear_cart_lines_for_order,
    create_order_from_cart,
    restore_cart_from_order,
)


def _csrf_client(user, password):
    client = APIClient(enforce_csrf_checks=True)
    resp = client.post("/api/accounts/token/", {"phone": user.phone, "password": password})
    token = resp.data["csrf_token"]
    client.credentials(HTTP_X_CSRFTOKEN=token)
    return client


class ColorCartTests(TestCase):
    def setUp(self):
        self.password = "Sample-Passw0rd!"
        self.user = User.objects.create_user(phone="09121111111", password=self.password)
        self.brand = Brand.objects.create(name="برند", slug="brand")
        self.category = Category.objects.create(name="دسته", slug="cat")
        self.black = Color.objects.create(name="مشکی", hex_code="#111111")
        self.white = Color.objects.create(name="سفید", hex_code="#F4F4F4")
        self.other_color = Color.objects.create(name="زرد", hex_code="#F2C81B")
        self.product = Product.objects.create(
            name="سپر",
            slug="soper",
            sku="SKU-C1",
            brand=self.brand,
            category=self.category,
            price=100_000,
            stock=50,
        )
        self.product.colors.set([self.black, self.white])
        self.client = _csrf_client(self.user, self.password)

    def test_two_colours_of_the_same_product_are_separate_lines(self):
        self.client.post("/api/orders/cart/", {"product": self.product.id, "quantity": 1, "color": self.black.id})
        self.client.post("/api/orders/cart/", {"product": self.product.id, "quantity": 1, "color": self.white.id})
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 2)

    def test_adding_the_same_colour_twice_increments_one_line(self):
        self.client.post("/api/orders/cart/", {"product": self.product.id, "quantity": 1, "color": self.black.id})
        self.client.post("/api/orders/cart/", {"product": self.product.id, "quantity": 2, "color": self.black.id})
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.first().quantity, 3)

    def test_a_colour_not_belonging_to_the_product_is_rejected(self):
        response = self.client.post(
            "/api/orders/cart/", {"product": self.product.id, "quantity": 1, "color": self.other_color.id}
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CartItem.objects.exists())

    def test_no_colour_still_works_for_a_colourless_product(self):
        plain = Product.objects.create(
            name="فیلتر",
            slug="filter",
            sku="SKU-C2",
            brand=self.brand,
            category=self.category,
            price=50_000,
            stock=10,
        )
        response = self.client.post("/api/orders/cart/", {"product": plain.id, "quantity": 1})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(CartItem.objects.get().color_id, None)

    def test_patch_targets_only_the_matching_colour_line(self):
        self.client.post("/api/orders/cart/", {"product": self.product.id, "quantity": 1, "color": self.black.id})
        self.client.post("/api/orders/cart/", {"product": self.product.id, "quantity": 1, "color": self.white.id})
        self.client.patch("/api/orders/cart/", {"product": self.product.id, "quantity": 5, "color": self.black.id})
        black_line = CartItem.objects.get(product=self.product, color=self.black)
        white_line = CartItem.objects.get(product=self.product, color=self.white)
        self.assertEqual(black_line.quantity, 5)
        self.assertEqual(white_line.quantity, 1)

    def test_delete_removes_only_the_matching_colour_line(self):
        self.client.post("/api/orders/cart/", {"product": self.product.id, "quantity": 1, "color": self.black.id})
        self.client.post("/api/orders/cart/", {"product": self.product.id, "quantity": 1, "color": self.white.id})
        self.client.delete("/api/orders/cart/", {"product": self.product.id, "color": self.black.id})
        remaining = CartItem.objects.filter(product=self.product)
        self.assertEqual(remaining.count(), 1)
        self.assertEqual(remaining.first().color, self.white)

    def test_cart_response_reports_the_colour_name(self):
        self.client.post("/api/orders/cart/", {"product": self.product.id, "quantity": 1, "color": self.black.id})
        data = self.client.get("/api/orders/cart/").data
        self.assertEqual(data["items"][0]["color_name"], "مشکی")


def _credit_shopkeeper(phone, *, credit_limit=10_000_000):
    """An approved shopkeeper with an active credit account from a supplier."""
    from apps.suppliers.models import CreditAccount

    supplier = User.objects.create_user(phone="09129999999", role=User.Role.SUPPLIER, is_approved=True)
    shop = User.objects.create_user(
        phone=phone, password="Sample-Passw0rd!", role=User.Role.SHOPKEEPER, is_approved=True
    )
    CreditAccount.objects.create(supplier=supplier, shop=shop, credit_limit=credit_limit)
    return shop


class ColorCheckoutTests(TestCase):
    def setUp(self):
        self.user = _credit_shopkeeper("09122222222")
        self.brand = Brand.objects.create(name="برند2", slug="brand2")
        self.category = Category.objects.create(name="دسته2", slug="cat2")
        self.black = Color.objects.create(name="مشکی۲", hex_code="#111111")
        self.white = Color.objects.create(name="سفید۲", hex_code="#F4F4F4")
        self.product = Product.objects.create(
            name="سپر۲",
            slug="soper2",
            sku="SKU-C3",
            brand=self.brand,
            category=self.category,
            price=200_000,
            stock=50,
        )
        self.product.colors.set([self.black, self.white])
        self.address = Address.objects.create(
            user=self.user,
            title="خانه",
            receiver_name="ت",
            receiver_phone="09122222222",
            province="تهران",
            city="تهران",
            line="خیابان",
        )
        self.cart, _ = Cart.objects.get_or_create(user=self.user)

    def test_checkout_snapshots_the_colour_onto_the_order_line(self):
        CartItem.objects.create(cart=self.cart, product=self.product, color=self.black, quantity=2)
        order = create_order_from_cart(user=self.user, address=self.address, payment_method=Order.PaymentMethod.CREDIT)
        line = order.items.get()
        self.assertEqual(line.color, self.black)
        self.assertEqual(line.color_name, "مشکی۲")

    def test_checkout_keeps_two_colours_as_two_lines(self):
        CartItem.objects.create(cart=self.cart, product=self.product, color=self.black, quantity=1)
        CartItem.objects.create(cart=self.cart, product=self.product, color=self.white, quantity=1)
        order = create_order_from_cart(user=self.user, address=self.address, payment_method=Order.PaymentMethod.CREDIT)
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(set(order.items.values_list("color_name", flat=True)), {"مشکی۲", "سفید۲"})

    def test_clearing_an_online_order_leaves_the_other_colour_in_the_cart(self):
        """Paying for black must not silently drop white from the basket.

        Built directly rather than via create_order_from_cart(..., ONLINE):
        that path also requires a configured payment gateway, which is not
        what this test is about — only clear_cart_lines_for_order() is.
        """
        from .models import OrderItem

        order = Order.objects.create(
            user=self.user,
            ship_to_name="ت",
            ship_to_phone="09122222222",
            ship_to_city="تهران",
            ship_to_address="خیابان",
            payment_method=Order.PaymentMethod.ONLINE,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            color=self.black,
            color_name="مشکی۲",
            product_name=self.product.name,
            unit_price=self.product.price,
            quantity=1,
        )
        CartItem.objects.create(cart=self.cart, product=self.product, color=self.black, quantity=1)
        # The buyer adds white while the online order sits unpaid.
        CartItem.objects.create(cart=self.cart, product=self.product, color=self.white, quantity=1)
        clear_cart_lines_for_order(order)
        remaining = CartItem.objects.filter(cart=self.cart)
        self.assertEqual(remaining.count(), 1)
        self.assertEqual(remaining.first().color, self.white)

    def test_restoring_a_cancelled_order_brings_back_its_colour(self):
        _owner_card()
        CartItem.objects.create(cart=self.cart, product=self.product, color=self.black, quantity=1)
        order = create_order_from_cart(
            user=self.user, address=self.address, payment_method=Order.PaymentMethod.CARD_TO_CARD
        )
        self.assertFalse(CartItem.objects.filter(cart=self.cart).exists())  # emptied at checkout
        restore_cart_from_order(order)
        restored = CartItem.objects.get(cart=self.cart)
        self.assertEqual(restored.color, self.black)


class CheckoutRulesTests(TestCase):
    """Server-side checkout rules that a hand-crafted API call must not bypass."""

    def setUp(self):
        self.brand = Brand.objects.create(name="برند3", slug="brand3")
        self.category = Category.objects.create(name="دسته3", slug="cat3")
        self.product = Product.objects.create(
            name="لنت۳",
            slug="lent3",
            sku="SKU-R1",
            brand=self.brand,
            category=self.category,
            price=100_000,
            stock=5,
        )

    def _buyer_with_cart(self, user, quantity=1):
        address = Address.objects.create(
            user=user,
            title="انبار",
            receiver_name="ت",
            receiver_phone=user.phone,
            province="تهران",
            city="تهران",
            line="خیابان",
        )
        cart, _ = Cart.objects.get_or_create(user=user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=quantity)
        return address

    def _checkout(self, user, address, method=Order.PaymentMethod.CREDIT):
        return create_order_from_cart(user=user, address=address, payment_method=method)

    def test_retail_customer_cannot_buy_on_credit(self):
        customer = User.objects.create_user(phone="09123333333")
        address = self._buyer_with_cart(customer)
        with self.assertRaises(ValidationError):
            self._checkout(customer, address)
        self.assertFalse(Order.objects.exists())

    def test_shopkeeper_without_credit_account_is_refused(self):
        shop = User.objects.create_user(phone="09124444444", role=User.Role.SHOPKEEPER, is_approved=True)
        address = self._buyer_with_cart(shop)
        with self.assertRaises(ValidationError):
            self._checkout(shop, address)

    def test_credit_limit_is_enforced(self):
        shop = _credit_shopkeeper("09125555555", credit_limit=150_000)
        address = self._buyer_with_cart(shop, quantity=2)  # 200,000 + VAT > 150,000
        with self.assertRaises(ValidationError):
            self._checkout(shop, address)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)  # nothing was reserved

    def test_credit_order_within_limit_opens_an_invoice(self):
        shop = _credit_shopkeeper("09126666666")
        address = self._buyer_with_cart(shop)
        order = self._checkout(shop, address)
        self.assertEqual(order.status, Order.Status.CREDIT)
        self.assertEqual(order.credit_invoice.amount, order.total)

    def test_stock_cannot_be_oversold(self):
        shop = _credit_shopkeeper("09127777777")
        address = self._buyer_with_cart(shop, quantity=6)
        with self.assertRaises(ValidationError):
            self._checkout(shop, address)

    def test_checkout_reserves_and_cancel_returns_stock(self):
        from .services import cancel_order

        shop = _credit_shopkeeper("09128888888")
        address = self._buyer_with_cart(shop, quantity=3)
        order = self._checkout(shop, address)
        self.product.refresh_from_db()
        self.assertEqual((self.product.stock, self.product.sold_count), (2, 3))
        cancel_order(order)
        self.product.refresh_from_db()
        self.assertEqual((self.product.stock, self.product.sold_count), (5, 0))

    def test_inactive_product_cannot_be_checked_out(self):
        shop = _credit_shopkeeper("09120000000")
        address = self._buyer_with_cart(shop)
        Product.objects.filter(pk=self.product.pk).update(is_active=False)
        with self.assertRaises(ValidationError):
            self._checkout(shop, address)


def _owner_card(card_number="6037000000000000"):
    """Give the site owner the marketplace card that card-to-card orders pay into."""
    from apps.suppliers.models import SupplierSettings

    owner = User.objects.filter(is_superuser=True).first() or User.objects.create_superuser(
        phone="09120000000", password="Sample-Passw0rd!"
    )
    return SupplierSettings.objects.update_or_create(
        supplier=owner, defaults={"card_number": card_number, "card_holder": "Marketplace"}
    )[0]


class CardToCardDestinationTests(TestCase):
    """Buyers transfer to the marketplace's card, never to an arbitrary supplier's."""

    SUPPLIER_CARD = "6219000000000000"

    def setUp(self):
        from apps.suppliers.models import SupplierSettings

        self.owner = User.objects.create_superuser(phone="09120000000", password="Sample-Passw0rd!")
        self.supplier = User.objects.create_user(phone="09121111111", role=User.Role.SUPPLIER, is_approved=True)
        self.other_supplier = User.objects.create_user(phone="09122222222", role=User.Role.SUPPLIER, is_approved=True)
        # The supplier's row is the oldest one and carries a card of its own.
        SupplierSettings.objects.create(
            supplier=self.supplier, card_number=self.SUPPLIER_CARD, receipt_payment_enabled=True
        )
        self.product = Product.objects.create(
            name="لنت",
            slug="lent-c2c",
            sku="SKU-C2C",
            brand=Brand.objects.create(name="برند۴", slug="brand4"),
            category=Category.objects.create(name="دسته۴", slug="cat4"),
            price=100_000,
            stock=5,
            supplier=self.supplier,
        )
        self.buyer = User.objects.create_user(phone="09123333333")
        CartItem.objects.create(cart=Cart.objects.create(user=self.buyer), product=self.product, quantity=1)
        self.client = APIClient()
        self.client.force_authenticate(self.buyer)

    def payment_info(self):
        return self.client.get("/api/suppliers/payment-info/").data

    def test_buyers_see_the_site_owners_card(self):
        _owner_card("6037000000000000")
        info = self.payment_info()
        self.assertEqual(info["card_number"], "6037000000000000")
        self.assertTrue(info["methods"]["receipt"])

    def test_card_to_card_is_off_until_the_owner_adds_a_card(self):
        info = self.payment_info()
        self.assertEqual(info["card_number"], "")
        self.assertFalse(info["methods"]["receipt"])
        address = Address.objects.create(
            user=self.buyer,
            title="انبار",
            receiver_name="ت",
            receiver_phone=self.buyer.phone,
            province="تهران",
            city="تهران",
            line="خیابان",
        )
        with self.assertRaises(ValidationError):
            create_order_from_cart(user=self.buyer, address=address, payment_method=Order.PaymentMethod.CARD_TO_CARD)

    def test_a_single_supplier_install_keeps_its_card(self):
        self.other_supplier.delete()
        info = self.payment_info()
        self.assertEqual(info["card_number"], self.SUPPLIER_CARD)
        self.assertTrue(info["methods"]["receipt"])
