from rest_framework import serializers

from .models import PaymentGatewaySettings, PaymentTransaction


class PaymentGatewaySettingsSerializer(serializers.ModelSerializer):
    available_gateways = serializers.ListField(read_only=True)

    class Meta:
        model = PaymentGatewaySettings
        fields = (
            "active_gateway",
            "bitpay_api_key",
            "bitpay_sandbox",
            "bitpay_enabled",
            "zarinpal_merchant_id",
            "zarinpal_sandbox",
            "zarinpal_enabled",
            "is_configured",
            "available_gateways",
            "updated_at",
        )
        read_only_fields = ("is_configured", "available_gateways", "updated_at")


class PaymentTransactionSerializer(serializers.ModelSerializer):
    gateway_display = serializers.CharField(source="get_gateway_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = (
            "id",
            "gateway",
            "gateway_display",
            "amount",
            "ref_id",
            "card_number",
            "status",
            "status_display",
            "created_at",
        )
