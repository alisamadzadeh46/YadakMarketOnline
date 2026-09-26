from rest_framework import serializers

from .models import Coupon


def cart_lines(user):
    """``(supplier_id, line_total)`` for every line of the user's cart."""
    cart = getattr(user, "cart", None)
    if cart is None:
        return []
    return [(item.product.supplier_id, item.line_total) for item in cart.items.select_related("product")]


class CouponValidateSerializer(serializers.Serializer):
    """Validate a coupon against the buyer's cart without consuming it.

    The discount is computed from the server-side cart, so a supplier coupon
    only counts that supplier's lines; ``amount`` is used when the cart is empty.
    """

    code = serializers.CharField()
    amount = serializers.IntegerField(min_value=0)

    def validate(self, attrs):
        try:
            coupon = Coupon.objects.get(code__iexact=attrs["code"])
        except Coupon.DoesNotExist:
            raise serializers.ValidationError({"code": "کد تخفیف نامعتبر است."}) from None
        lines = cart_lines(self.context["request"].user)
        if lines:
            attrs["amount"] = sum(total for _supplier, total in lines)
            eligible = coupon.eligible_amount(lines)
        else:
            eligible = attrs["amount"] if coupon.owner_id is None else 0
        try:
            coupon.validate_for(self.context["request"].user, eligible)
        except ValueError as exc:
            raise serializers.ValidationError({"code": str(exc)}) from exc
        attrs["coupon"] = coupon
        attrs["discount"] = coupon.discount_for(eligible)
        return attrs
