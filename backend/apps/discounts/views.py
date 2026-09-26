from rest_framework import permissions, serializers, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsSupplierOrAdmin, is_site_admin

from .models import Coupon
from .serializers import CouponValidateSerializer


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = (
            "id",
            "code",
            "scope",
            "kind",
            "value",
            "max_discount",
            "min_order_amount",
            "usage_limit",
            "used_count",
            "per_user_limit",
            "valid_from",
            "valid_to",
            "is_active",
        )
        read_only_fields = ("used_count",)

    scope = serializers.SerializerMethodField()

    def get_scope(self, coupon):
        """Human readable coverage of the coupon for the panel list."""
        if coupon.owner_id is None:
            return "کل سایت"
        return coupon.owner.full_name or coupon.owner.phone


class ManageCouponViewSet(viewsets.ModelViewSet):
    """Discount code CRUD: the site owner manages site-wide coupons, a supplier
    manages coupons that only apply to their own products."""

    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAuthenticated, IsSupplierOrAdmin]

    def get_queryset(self):
        queryset = Coupon.objects.select_related("owner").order_by("-created_at")
        if is_site_admin(self.request.user):
            return queryset
        return queryset.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=None if is_site_admin(self.request.user) else self.request.user)


class CouponValidateView(APIView):
    """POST {code, amount} -> {valid, discount, final_amount}."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CouponValidateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return Response(
            {
                "valid": True,
                "code": data["coupon"].code,
                "discount": data["discount"],
                "final_amount": data["amount"] - data["discount"],
            }
        )
