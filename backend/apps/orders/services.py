"""Order creation logic kept out of the views for testability.

Stock is reserved (decremented) at checkout and returned if the order is later
canceled for non-payment. Everything runs in a single transaction so a failure
never leaves stock or totals half-applied.
"""

from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.db.models.functions import Greatest
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.catalog.models import Product
from apps.discounts.models import Coupon, CouponRedemption

from .models import Cart, CartItem, CheckoutSettings, Order, OrderItem


def card_to_card_allowed(items):
    """Whether the given cart lines may be paid by card-to-card, right now.

    Online payment only depends on the gateway being configured (checked
    separately). Card-to-card is only offered when there is a card to transfer
    to and the site owner has switched it on — for **every** supplier
    represented in the cart, since a single order can only carry one payment
    method. One unconfigured supplier in the cart is enough to hide the option
    for the whole order.
    """
    from apps.suppliers.models import SupplierSettings

    if SupplierSettings.bank_details() is None:
        return False
    supplier_ids = {i.product.supplier_id for i in items if i.product.supplier_id}
    if not supplier_ids:
        return True  # ownerless products — don't block checkout on this alone
    settings_by_supplier = {
        s.supplier_id: s.receipt_payment_enabled for s in SupplierSettings.objects.filter(supplier_id__in=supplier_ids)
    }
    # A supplier with no settings row yet defaults to the model default (False).
    return all(settings_by_supplier.get(sid, False) for sid in supplier_ids)


@transaction.atomic
def create_order_from_cart(*, user, address, payment_method, coupon_code=""):
    """Turn the user's cart into an Order. Returns the created Order."""
    cart = getattr(user, "cart", None)
    items = list(cart.items.select_related("product", "color").all()) if cart else []
    if not items:
        raise ValidationError("سبد خرید شما خالی است.")

    # An online order holds its stock reservation while the cart keeps showing
    # the same lines (see below). Checking out again therefore means the buyer
    # abandoned the previous attempt — release it, or the same goods stay
    # reserved twice and the second checkout can fail with "insufficient stock".
    stale = Order.objects.filter(
        user=user,
        status=Order.Status.PENDING_PAYMENT,
        payment_method=Order.PaymentMethod.ONLINE,
    )
    for old in stale:
        cancel_order(old, restock=True)

    # Lock the products for the rest of the transaction: two buyers checking
    # out the last units at the same moment must not both pass the stock check.
    # Rows are locked in id order so concurrent checkouts cannot deadlock.
    locked = {
        product.pk: product
        for product in Product.objects.select_for_update()
        .filter(pk__in=sorted({item.product_id for item in items}))
        .order_by("pk")
    }
    for item in items:
        item.product = locked[item.product_id]

    lines = []  # (supplier_id, line_total) for coupon eligibility
    for item in items:
        product = item.product
        if not product.is_active:
            raise ValidationError(f"«{product.name}» دیگر فروخته نمی‌شود؛ آن را از سبد خرید حذف کنید.")
        if item.quantity < product.min_order_qty:
            raise ValidationError(
                f"حداقل سفارش «{product.name}» {product.min_order_qty} {product.get_unit_display()} است."
            )
        if item.quantity > product.stock:
            raise ValidationError(f"موجودی «{product.name}» کافی نیست.")
        # Tiered wholesale pricing: unit price depends on the line quantity.
        lines.append((product.supplier_id, product.price_for(item.quantity) * item.quantity))
    subtotal = sum(total for _supplier, total in lines)

    # Apply an optional coupon.
    coupon = None
    discount = 0
    if coupon_code:
        try:
            coupon = Coupon.objects.select_for_update().get(code__iexact=coupon_code)
            eligible = coupon.eligible_amount(lines)
            coupon.validate_for(user, eligible)
            discount = coupon.discount_for(eligible)
        except Coupon.DoesNotExist:
            raise ValidationError("کد تخفیف نامعتبر است.") from None
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    is_credit = payment_method == Order.PaymentMethod.CREDIT

    # Enforce the owner's payment-method switches (a client can't bypass them).
    if payment_method == Order.PaymentMethod.CARD_TO_CARD:
        if not card_to_card_allowed(items):
            raise ValidationError("پرداخت با فیش بانکی برای این سفارش فعال نیست؛ لطفاً پرداخت آنلاین را انتخاب کنید.")
    elif payment_method == Order.PaymentMethod.ONLINE:
        from apps.payments.models import PaymentGatewaySettings

        gateway_cfg = PaymentGatewaySettings.load()
        if not gateway_cfg.is_configured:
            raise ValidationError("درگاه پرداخت آنلاین هنوز پیکربندی نشده است.")

    # VAT + flat shipping — snapshotted so a later rate change never rewrites
    # an already-placed order's total.
    checkout_cfg = CheckoutSettings.load()
    taxable = subtotal - discount
    tax_amount = (
        int((Decimal(taxable) * checkout_cfg.vat_percent / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        if taxable > 0
        else 0
    )
    shipping_cost = 0 if is_credit else checkout_cfg.shipping_cost
    total = subtotal - discount + tax_amount + shipping_cost
    if is_credit:
        _check_credit(user, total)

    order = Order.objects.create(
        user=user,
        ship_to_name=address.receiver_name,
        ship_to_phone=address.receiver_phone,
        ship_to_city=address.city,
        ship_to_address=address.line,
        ship_lat=address.lat,
        ship_lng=address.lng,
        payment_method=payment_method,
        status=Order.Status.CREDIT if is_credit else Order.Status.PENDING_PAYMENT,
        subtotal=subtotal,
        discount_amount=discount,
        tax_amount=tax_amount,
        shipping_cost=shipping_cost,
        total=total,
        coupon_code=coupon.code if coupon else "",
        discount_supplier_id=coupon.owner_id if coupon else None,
        # Both card-to-card and online orders run against the same countdown —
        # one waits on a buyer upload, the other on the gateway callback.
        receipt_deadline=(
            None if is_credit else timezone.now() + timedelta(minutes=settings.PAYMENT_RECEIPT_WINDOW_MINUTES)
        ),
    )

    # Snapshot items and reserve stock.
    for item in items:
        product = item.product
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            unit_price=product.price_for(item.quantity),
            quantity=item.quantity,
            color=item.color,
            color_name=item.color.name if item.color_id else "",
        )
        Product.objects.filter(pk=product.pk).update(
            stock=F("stock") - item.quantity, sold_count=F("sold_count") + item.quantity
        )

    # Record coupon redemption.
    if coupon:
        coupon.used_count += 1
        coupon.save(update_fields=["used_count"])
        CouponRedemption.objects.create(coupon=coupon, user=user, order=order, amount=discount)

    # A credit order is live the moment it is placed, but its post_save ran
    # before the lines above existed, so listeners that read the lines (the
    # commission engine) saw an empty order. Save once more now it is complete.
    if is_credit:
        order.save(update_fields=["status"])

    # Empty the cart now that it has become an order — EXCEPT for online
    # orders, which are not paid yet. If the gateway errors out, the buyer
    # cancels, or the bank simply times out, emptying the cart here would
    # throw away everything they picked; they'd have to rebuild the whole
    # basket to try again. Online carts are cleared by
    # clear_cart_lines_for_order() the moment the payment actually verifies.
    if payment_method != Order.PaymentMethod.ONLINE:
        cart.items.all().delete()

    # Tell the supplier to start procuring — but ONLY for credit orders, which
    # are live the moment they're placed. A card-to-card or online order is
    # still unpaid at this point; texting "sold" now would announce a sale
    # that may never happen (and did: the buyer saw a failed gateway while the
    # supplier had already been told the item sold). Those are notified from
    # notify_supplier_order_paid() once the payment is actually confirmed.
    if is_credit:

        def _notify_supplier():
            try:
                from apps.suppliers.tasks import notify_supplier_new_order

                notify_supplier_new_order.delay(order.pk)
            except Exception:  # never let a messaging hiccup break checkout
                pass

        transaction.on_commit(_notify_supplier)
    return order


def _check_credit(user, amount):
    """Refuse a credit purchase the buyer is not entitled to.

    Credit ("buy now, settle later") is only for approved shopkeepers with an
    active credit account, and never beyond the account's remaining limit. The
    account row is locked so two simultaneous credit checkouts cannot both
    spend the same remaining credit.
    """
    from apps.suppliers.models import CreditAccount

    if not user.can_buy_wholesale:
        raise ValidationError("خرید اعتباری فقط برای فروشگاه‌های تاییدشده فعال است.")
    account = CreditAccount.active_for(user, lock=True)
    if account is None:
        raise ValidationError("برای حساب شما اعتبار خریدی تعریف نشده است.")
    if amount > account.available_credit:
        raise ValidationError(
            f"اعتبار شما برای این سفارش کافی نیست. اعتبار قابل استفاده: {account.available_credit:,} تومان."
        )


@transaction.atomic
def revive_paid_order(order):
    """Re-open an order that expired while its online payment was completing.

    The expiry sweep may cancel an order (returning its stock) moments before
    the gateway confirms the payment. If every item is still in stock, the
    reservation is taken again and the order is confirmed; otherwise nothing
    changes and False is returned, meaning the payment must be refunded.
    """
    items = list(order.items.all())
    products = {
        product.pk: product
        for product in Product.objects.select_for_update()
        .filter(pk__in=sorted({item.product_id for item in items}))
        .order_by("pk")
    }
    if any(products[item.product_id].stock < item.quantity for item in items):
        return False
    for item in items:
        Product.objects.filter(pk=item.product_id).update(
            stock=F("stock") - item.quantity, sold_count=F("sold_count") + item.quantity
        )
    order.status = Order.Status.CONFIRMED
    order.paid_at = timezone.now()
    order.save(update_fields=["status", "paid_at"])
    return True


@transaction.atomic
def clear_cart_lines_for_order(order):
    """Remove exactly the lines this order consumed from the buyer's cart.

    Used once an online payment verifies. Deliberately targeted rather than
    ``cart.items.all().delete()``: the buyer may well have added something new
    while the order sat unpaid, and that must survive.
    """
    cart = getattr(order.user, "cart", None)
    if not cart:
        return
    # (product, colour) pairs, not just product ids — a buyer with both a
    # black and a white line of the same part in their cart, who only just
    # paid for black, must still find white waiting for them afterwards.
    pairs = list(order.items.values_list("product_id", "color_id"))
    for product_id, color_id in pairs:
        cart.items.filter(product_id=product_id, color_id=color_id).delete()


@transaction.atomic
def restore_cart_from_order(order):
    """Put an unpaid order's lines back into the buyer's cart.

    Only relevant for orders whose cart was emptied at checkout (card-to-card);
    online carts are never emptied before payment, so this is a no-op for them.
    Merges instead of overwriting — a product already in the cart keeps the
    larger quantity rather than the sum, so re-running this never inflates an
    order the buyer rebuilt by hand.
    """
    cart, _ = Cart.objects.get_or_create(user=order.user)
    existing = {(i.product_id, i.color_id): i for i in cart.items.all()}
    for item in order.items.select_related("product", "color"):
        if not item.product_id or not item.product.is_active:
            continue
        line = existing.get((item.product_id, item.color_id))
        if line is None:
            CartItem.objects.create(cart=cart, product=item.product, color=item.color, quantity=item.quantity)
        elif line.quantity < item.quantity:
            line.quantity = item.quantity
            line.save(update_fields=["quantity"])
    return cart


@transaction.atomic
def cancel_order(order, *, restock=True):
    """Cancel an order and (optionally) return reserved stock."""
    if order.status in (Order.Status.CANCELED, Order.Status.DELIVERED):
        return order
    if restock:
        # F() expressions: a concurrent checkout of the same product must not
        # overwrite the returned stock with its own stale copy.
        for item in order.items.all():
            Product.objects.filter(pk=item.product_id).update(
                stock=F("stock") + item.quantity,
                sold_count=Greatest(F("sold_count") - item.quantity, 0),
            )
    order.status = Order.Status.CANCELED
    order.save(update_fields=["status"])
    # Cancelling must not cost the buyer their basket. Online carts still hold
    # the lines (never emptied pre-payment); the other methods need them back.
    if order.payment_method != Order.PaymentMethod.ONLINE:
        restore_cart_from_order(order)
    return order
