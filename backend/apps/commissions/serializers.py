"""Serializers for the revenue-share panel."""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import (
    CategoryCommissionRate,
    CommissionEntry,
    CommissionSetting,
    OrderSupplierShare,
)


class CommissionSettingSerializer(serializers.ModelSerializer):
    beneficiary_name = serializers.CharField(source="beneficiary.full_name", read_only=True)
    beneficiary_phone = serializers.CharField(source="beneficiary.phone", read_only=True)
    beneficiary_email = serializers.CharField(source="beneficiary.email", read_only=True)

    class Meta:
        model = CommissionSetting
        fields = (
            "is_active",
            "default_rate",
            "rate_for_shopkeeper",
            "rate_for_customer",
            "min_rate",
            "max_rate",
            "accrue_on_credit_order",
            "notify_on_new_commission",
            "beneficiary_name",
            "beneficiary_phone",
            "beneficiary_email",
            "updated_at",
        )
        read_only_fields = ("updated_at",)

    def validate(self, attrs):
        # Run the model's own band check so the API returns the same Persian
        # message the admin shows, instead of a 500 later on.
        instance = self.instance or CommissionSetting.load()
        for key, value in attrs.items():
            setattr(instance, key, value)
        try:
            instance.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return attrs


class CategoryCommissionRateSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = CategoryCommissionRate
        fields = ("id", "category", "category_name", "rate")

    def validate_rate(self, value):
        setting = CommissionSetting.load()
        if not (setting.min_rate <= value <= setting.max_rate):
            raise serializers.ValidationError(f"درصد باید بین {setting.min_rate} و {setting.max_rate} باشد.")
        return value


class CommissionEntrySerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.number", read_only=True)
    order_total = serializers.IntegerField(source="order.total", read_only=True)
    order_status = serializers.CharField(source="order.get_status_display", read_only=True)
    buyer_name = serializers.SerializerMethodField()
    buyer_role_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = CommissionEntry
        fields = (
            "id",
            "order_number",
            "order_total",
            "order_status",
            "buyer_name",
            "buyer_role",
            "buyer_role_display",
            "base_amount",
            "effective_rate",
            "amount",
            "status",
            "status_display",
            "paid_at",
            "note",
            "created_at",
        )

    def get_buyer_name(self, obj):
        return obj.buyer.full_name or obj.buyer.phone

    def get_buyer_role_display(self, obj):
        return obj.buyer.get_role_display()


class OrderSupplierShareSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.number", read_only=True)
    order_total = serializers.IntegerField(source="order.total", read_only=True)
    order_status = serializers.CharField(source="order.get_status_display", read_only=True)
    payment_method = serializers.CharField(source="order.get_payment_method_display", read_only=True)
    supplier_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = OrderSupplierShare
        fields = (
            "id",
            "order_number",
            "order_total",
            "order_status",
            "payment_method",
            "supplier",
            "supplier_name",
            "gross_amount",
            "owner_commission",
            "supplier_net",
            "effective_rate",
            "status",
            "status_display",
            "created_at",
        )

    def get_supplier_name(self, obj):
        return obj.supplier.full_name or obj.supplier.phone
