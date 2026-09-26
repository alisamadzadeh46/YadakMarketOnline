from django.conf import settings
from rest_framework import serializers

from apps.accounts.models import Address

from .models import Cart, CartItem, CheckoutSettings, Order, OrderItem, PaymentReceipt


class CheckoutSettingsSerializer(serializers.ModelSerializer):
    # Deployment setting, exposed so the storefront shows the real payment window.
    payment_window_minutes = serializers.SerializerMethodField()

    class Meta:
        model = CheckoutSettings
        fields = ("vat_percent", "shipping_cost", "payment_window_minutes", "updated_at")
        read_only_fields = ("updated_at",)

    def get_payment_window_minutes(self, _obj):
        return settings.PAYMENT_RECEIPT_WINDOW_MINUTES


def _thumb(serializer, product, color_id=None):
    """Absolute URL of the product's thumbnail.

    Prefers a photo tagged with the line's selected colour — a black swatch in
    the cart shouldn't show a white part — falling back to the first shared
    image when the product has none tagged for that colour yet.
    """
    images = list(product.images.all())
    match = next((i for i in images if color_id and i.color_id == color_id), None)
    first = match or (images[0] if images else None)
    if not first:
        return None
    request = serializer.context.get("request")
    url = first.image.url
    return request.build_absolute_uri(url) if request else url


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    thumbnail = serializers.SerializerMethodField()
    # Effective (tier-aware) unit price for the current quantity.
    unit_price = serializers.IntegerField(read_only=True)
    line_total = serializers.IntegerField(read_only=True)
    min_order_qty = serializers.IntegerField(source="product.min_order_qty", read_only=True)
    brand_name = serializers.CharField(source="product.brand.name", read_only=True, default="")
    sku = serializers.CharField(source="product.sku", read_only=True)
    stock = serializers.IntegerField(source="product.stock", read_only=True)
    carton_qty = serializers.IntegerField(source="product.carton_qty", read_only=True)
    supplier_name = serializers.SerializerMethodField()
    problem = serializers.SerializerMethodField()
    color_name = serializers.CharField(source="color.name", read_only=True, default="")

    class Meta:
        model = CartItem
        fields = (
            "id",
            "product",
            "product_name",
            "product_slug",
            "thumbnail",
            "unit_price",
            "quantity",
            "line_total",
            "min_order_qty",
            "brand_name",
            "sku",
            "stock",
            "carton_qty",
            "supplier_name",
            "problem",
            "color",
            "color_name",
        )

    def get_thumbnail(self, obj):
        return _thumb(self, obj.product, obj.color_id)

    def get_supplier_name(self, obj):
        supplier = obj.product.supplier
        return (supplier.full_name or supplier.phone) if supplier else ""

    def get_problem(self, obj):
        """Re-checked live on every cart/checkout load — surfaces exactly why
        this line can no longer be ordered as-is, right on the card itself."""
        product = obj.product
        if not product.is_active:
            return "این محصول دیگر در دسترس نیست."
        if product.stock <= 0:
            return "این کالا ناموجود شده است."
        if obj.quantity > product.stock:
            return f"فقط {product.stock} عدد از این کالا موجود است."
        if obj.quantity < product.min_order_qty:
            return f"حداقل سفارش این کالا {product.min_order_qty} عدد است."
        return None


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = ("id", "items", "subtotal")


class OrderItemSerializer(serializers.ModelSerializer):
    """One invoice line, with enough context to fulfil it without a second call.

    The fulfilment console needs to know *what* to pick and *who* stocks it —
    category, brand, part number and supplier — so they're joined in here
    rather than making the panel fetch each product separately.
    """

    line_total = serializers.IntegerField(read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    sku = serializers.CharField(source="product.sku", read_only=True)
    brand = serializers.CharField(source="product.brand.name", read_only=True, default="")
    category = serializers.CharField(source="product.category.name", read_only=True, default="")
    supplier_name = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product",
            "product_name",
            "product_slug",
            "thumbnail",
            "sku",
            "brand",
            "category",
            "supplier_name",
            "unit_price",
            "quantity",
            "line_total",
            "color_name",
        )

    def get_thumbnail(self, obj):
        return _thumb(self, obj.product, obj.color_id)

    def get_supplier_name(self, obj):
        supplier = getattr(obj.product, "supplier", None)
        if not supplier:
            return ""
        return supplier.full_name or supplier.phone or ""


class PaymentReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentReceipt
        fields = ("id", "image", "reference_number", "paid_amount", "is_confirmed", "confirmed_at")
        read_only_fields = ("is_confirmed", "confirmed_at")

    def validate_image(self, value):
        """Cap the size and re-encode.

        ImageField already refuses non-images, but re-encoding also strips EXIF
        (a phone photo of a bank slip carries GPS) and drops any payload hidden
        alongside valid image data.
        """
        from apps.core.images import normalize_image
        from apps.core.uploads import validate_image_upload

        validate_image_upload(value)
        return normalize_image(value)

    def to_representation(self, instance):
        """Signed, expiring URL — a receipt shows the payer's name and card."""
        from apps.core.protected import protected_url

        data = super().to_representation(instance)
        if instance.image:
            data["image"] = protected_url(self.context.get("request"), instance.image.name)
        return data


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    receipt = PaymentReceiptSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    seconds_left = serializers.IntegerField(read_only=True)
    payment_transactions = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "id",
            "number",
            "status",
            "status_display",
            "payment_method",
            "ship_to_name",
            "ship_to_phone",
            "ship_to_city",
            "ship_to_address",
            "ship_lat",
            "ship_lng",
            "subtotal",
            "discount_amount",
            "tax_amount",
            "shipping_cost",
            "total",
            "coupon_code",
            "receipt_deadline",
            "seconds_left",
            "paid_at",
            "created_at",
            "items",
            "receipt",
            "payment_transactions",
        )

    def get_payment_transactions(self, obj):
        # Only relevant (and imported) for online orders — keeps this app from
        # depending on apps.payments unless there's actually something to show.
        if obj.payment_method != Order.PaymentMethod.ONLINE:
            return []
        from apps.payments.serializers import PaymentTransactionSerializer

        return PaymentTransactionSerializer(obj.payment_transactions.all().order_by("-created_at"), many=True).data


class CheckoutSerializer(serializers.Serializer):
    address_id = serializers.IntegerField()
    payment_method = serializers.ChoiceField(
        choices=Order.PaymentMethod.choices, default=Order.PaymentMethod.CARD_TO_CARD
    )
    coupon_code = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_address_id(self, value):
        user = self.context["request"].user
        if not Address.objects.filter(id=value, user=user).exists():
            raise serializers.ValidationError("آدرس نامعتبر است.")
        return value
