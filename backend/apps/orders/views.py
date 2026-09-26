"""Order & payment API.

Buyer side : cart management, checkout, order history, receipt upload.
Supplier   : see all orders, confirm receipts, advance fulfillment status.
"""

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Address
from apps.accounts.permissions import IsSupplierOrAdmin, is_site_admin
from apps.catalog.models import Product
from apps.core.utils import to_fa

from .models import Cart, CartItem, CheckoutSettings, Order, PaymentReceipt
from .serializers import (
    CartSerializer,
    CheckoutSerializer,
    CheckoutSettingsSerializer,
    OrderSerializer,
    PaymentReceiptSerializer,
)
from .services import cancel_order, create_order_from_cart


def _get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def _resolve_color(request, product):
    """Validate an optional `color` id against the product's own colour list.

    Returns None when the request sent none — the ordinary case for a product
    with no colour variants. A colour that exists but isn't one of THIS
    product's is rejected rather than silently dropped, so a stale id from an
    old page never attaches the wrong colour to an order line.
    """
    raw = request.data.get("color")
    if raw in (None, "", "null"):
        return None
    try:
        color_id = int(raw)
    except (TypeError, ValueError):
        return None
    if not product.colors.filter(id=color_id).exists():
        from rest_framework.exceptions import ValidationError

        raise ValidationError({"color": "این رنگ برای این محصول تعریف نشده است."})
    return color_id


def _notify(order, text):
    """Queue an order-status SMS to the buyer (never blocks the request)."""
    from apps.notifications.models import SmsLog
    from apps.notifications.tasks import send_sms

    send_sms.delay(order.user.phone, f"{settings.SITE_SHORT_NAME}\n{text}", kind=SmsLog.Kind.ORDER)


class CartView(APIView):
    """GET the cart; POST/PATCH/DELETE manage its items."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(CartSerializer(_get_cart(request.user), context={"request": request}).data)

    def post(self, request):
        # Add or increment a product in the cart.
        product = get_object_or_404(Product, id=request.data.get("product"), is_active=True)
        # An unavailable or price-less part is an inquiry item, never a cart item —
        # block it at the API so it can't be added by a direct request.
        if product.stock <= 0:
            return Response({"detail": "این کالا در حال حاضر موجود نیست."}, status=400)
        if product.price <= 0:
            return Response({"detail": "قیمت این کالا هنوز ثبت نشده است؛ لطفاً درخواست تأمین ثبت کنید."}, status=400)
        quantity = int(request.data.get("quantity", product.min_order_qty))
        color_id = _resolve_color(request, product)
        cart = _get_cart(request.user)
        # A different colour of the same product is a distinct line — a
        # buyer ordering both black and white brackets sees two rows, each
        # with its own quantity, not one merged count.
        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product, color_id=color_id, defaults={"quantity": quantity}
        )
        if not created:
            item.quantity += quantity
            item.save()
        return Response(CartSerializer(cart, context={"request": request}).data, status=status.HTTP_201_CREATED)

    def patch(self, request):
        # Set an item's exact quantity (0 removes it).
        cart = _get_cart(request.user)
        product = get_object_or_404(Product, id=request.data.get("product"))
        color_id = _resolve_color(request, product)
        item = get_object_or_404(CartItem, cart=cart, product=product, color_id=color_id)
        quantity = int(request.data.get("quantity", 1))
        if quantity <= 0:
            item.delete()
        else:
            item.quantity = quantity
            item.save()
        return Response(CartSerializer(cart, context={"request": request}).data)

    def delete(self, request):
        cart = _get_cart(request.user)
        product = get_object_or_404(Product, id=request.data.get("product"))
        color_id = _resolve_color(request, product)
        cart.items.filter(product=product, color_id=color_id).delete()
        return Response(CartSerializer(cart, context={"request": request}).data)


class CheckoutSettingsView(APIView):
    """GET the VAT rate + shipping cost (any signed-in buyer, for the checkout
    breakdown); PATCH is admin-only (enforced inline — this is site-wide
    financial config, not per-supplier)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(CheckoutSettingsSerializer(CheckoutSettings.load()).data)

    def patch(self, request):
        if not (request.user.is_superuser or request.user.role == "admin"):
            return Response({"detail": "این بخش فقط برای مدیر سایت در دسترس است."}, status=403)
        obj = CheckoutSettings.load()
        serializer = CheckoutSettingsSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class CheckoutView(APIView):
    """Create an order from the cart and start the payment timer."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        address = Address.objects.get(id=data["address_id"], user=request.user)
        order = create_order_from_cart(
            user=request.user,
            address=address,
            payment_method=data["payment_method"],
            coupon_code=data.get("coupon_code", ""),
        )
        if order.status == Order.Status.PENDING_PAYMENT and order.payment_method == Order.PaymentMethod.CARD_TO_CARD:
            _notify(
                order,
                f"سفارش {order.number} ثبت شد. تا {to_fa(settings.PAYMENT_RECEIPT_WINDOW_MINUTES)} دقیقه "
                "فرصت دارید فیش واریز را در سایت بارگذاری کنید.",
            )
        elif order.status == Order.Status.CREDIT:
            _notify(order, f"سفارش اعتباری {order.number} ثبت شد و پس از تایید ارسال می‌شود.")
        # Online orders get no SMS at checkout — only after the gateway
        # confirms payment (see apps.payments.services.handle_callback).
        return Response(OrderSerializer(order, context={"request": request}).data, status=status.HTTP_201_CREATED)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """A buyer's own orders. Supports ?status= filtering for the shop panel."""

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "number"

    def get_queryset(self):
        qs = Order.objects.filter(user=self.request.user).prefetch_related(
            "items",
            "items__product__brand",
            "items__product__category",
            "items__product__supplier",
            "items__product__images",
        )
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def receipt(self, request, number=None):
        """Buyer uploads the card-to-card receipt (only before the deadline)."""
        order = self.get_object()
        if order.status != Order.Status.PENDING_PAYMENT:
            return Response({"detail": "این سفارش در وضعیت انتظار پرداخت نیست."}, status=400)
        if order.receipt_deadline and timezone.now() > order.receipt_deadline:
            return Response({"detail": "مهلت آپلود فیش به پایان رسیده است."}, status=400)

        receipt, _ = PaymentReceipt.objects.get_or_create(order=order)
        serializer = PaymentReceiptSerializer(receipt, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        order.status = Order.Status.RECEIPT_UPLOADED
        order.save(update_fields=["status"])
        return Response(OrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def reorder(self, request, number=None):
        """One-click reorder: copy this order's items back into the cart.

        Wholesale shops buy the same parts repeatedly — this saves them from
        hunting each product down again. Out-of-stock lines are skipped.
        """
        order = self.get_object()
        cart = _get_cart(request.user)
        added, skipped = 0, []
        for line in order.items.select_related("product"):
            product = line.product
            if not product.is_active or product.stock < max(line.quantity, product.min_order_qty):
                skipped.append(product.name)
                continue
            qty = max(line.quantity, product.min_order_qty)
            item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={"quantity": qty})
            if not created:
                item.quantity += qty
                item.save()
            added += 1
        detail = f"{added} قلم به سبد خرید افزوده شد."
        if skipped:
            detail += f" ({len(skipped)} قلم به دلیل ناموجودی اضافه نشد)"
        return Response({"detail": detail, "added": added, "skipped": skipped})


class SupplierOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """Fulfillment console.

    The site owner sees every order. A supplier only sees orders that contain
    at least one of their products, and may only move an order along when all
    of its lines are theirs — an order shared with other suppliers is handled
    by the site owner, so no supplier can confirm or cancel another's sale.
    """

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsSupplierOrAdmin]
    lookup_field = "number"

    def get_queryset(self):
        qs = (
            Order.objects.all()
            .select_related("user")
            .prefetch_related(
                "items",
                "items__product__brand",
                "items__product__category",
                "items__product__supplier",
                "items__product__images",
                "payment_transactions",
            )
        )
        if not is_site_admin(self.request.user):
            qs = qs.filter(items__product__supplier=self.request.user).distinct()
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    def _managed_order(self):
        """The requested order, if the current user may change its status."""
        order = self.get_object()
        user = self.request.user
        if not is_site_admin(user) and order.items.exclude(product__supplier=user).exists():
            raise PermissionDenied("این سفارش کالای تامین‌کنندگان دیگر را هم دارد؛ وضعیت آن را مدیر سایت تغییر می‌دهد.")
        return order

    @action(detail=True, methods=["post"])
    def confirm(self, request, number=None):
        """Confirm the uploaded receipt -> order becomes CONFIRMED (paid)."""
        order = self._managed_order()
        receipt = getattr(order, "receipt", None)
        if order.status != Order.Status.RECEIPT_UPLOADED or not receipt:
            return Response({"detail": "این سفارش فیش تاییدنشده‌ای ندارد."}, status=400)
        receipt.is_confirmed = True
        receipt.confirmed_by = request.user
        receipt.confirmed_at = timezone.now()
        receipt.save()
        order.status = Order.Status.CONFIRMED
        order.paid_at = timezone.now()
        order.save(update_fields=["status", "paid_at"])
        _notify(order, f"پرداخت سفارش {order.number} تایید شد و به‌زودی آماده‌سازی می‌شود.")
        # Only now is the sale real, so this is when the supplier hears about it.
        try:
            from apps.suppliers.tasks import notify_supplier_new_order

            notify_supplier_new_order.delay(order.pk)
        except Exception:
            pass
        return Response(OrderSerializer(order, context={"request": request}).data)

    _STATUS_SMS = {
        Order.Status.PROCESSING: "سفارش {n} در حال آماده‌سازی است.",
        Order.Status.SHIPPED: "سفارش {n} ارسال شد. به‌زودی به دست شما می‌رسد.",
        Order.Status.DELIVERED: "سفارش {n} تحویل شد. از خرید شما سپاسگزاریم.",
    }

    # Allowed source statuses for each fulfillment step.
    _TRANSITIONS = {
        Order.Status.PROCESSING: (Order.Status.CONFIRMED, Order.Status.CREDIT),
        Order.Status.SHIPPED: (Order.Status.PROCESSING,),
        Order.Status.DELIVERED: (Order.Status.SHIPPED,),
    }

    def _set_status(self, order, new_status):
        if order.status not in self._TRANSITIONS[new_status]:
            return Response(
                {"detail": f"سفارش در وضعیت «{order.get_status_display()}» است و این مرحله برای آن مجاز نیست."},
                status=400,
            )
        order.status = new_status
        order.save(update_fields=["status"])
        template = self._STATUS_SMS.get(new_status)
        if template:
            _notify(order, template.format(n=order.number))
        return Response(OrderSerializer(order, context={"request": self.request}).data)

    @action(detail=True, methods=["post"])
    def process(self, request, number=None):
        """Confirmed -> being prepared in the warehouse."""
        return self._set_status(self._managed_order(), Order.Status.PROCESSING)

    @action(detail=True, methods=["post"])
    def ship(self, request, number=None):
        return self._set_status(self._managed_order(), Order.Status.SHIPPED)

    @action(detail=True, methods=["post"])
    def deliver(self, request, number=None):
        return self._set_status(self._managed_order(), Order.Status.DELIVERED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, number=None):
        """Supplier/admin cancels an order — restocks reserved items.

        Rejected with a clear Persian message (not a raw 500) for states that
        can't be canceled: already delivered, already canceled, or a credit
        purchase already settled with the shop.
        """
        order = self._managed_order()
        if order.status == Order.Status.CANCELED:
            return Response({"detail": "این سفارش قبلاً لغو شده است."}, status=400)
        if order.status == Order.Status.DELIVERED:
            return Response({"detail": "سفارش تحویل‌شده را نمی‌توان لغو کرد."}, status=400)
        if (
            order.status == Order.Status.CREDIT
            and getattr(order, "credit_invoice", None)
            and order.credit_invoice.is_settled
        ):
            return Response({"detail": "این خرید اعتباری تسویه شده و قابل لغو نیست."}, status=400)
        try:
            cancel_order(order, restock=True)
        except Exception:
            return Response({"detail": "لغو سفارش با خطا مواجه شد. لطفاً دوباره تلاش کنید."}, status=400)
        _notify(order, f"سفارش {order.number} توسط فروشگاه لغو شد.")
        return Response(OrderSerializer(order, context={"request": self.request}).data)
