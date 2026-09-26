from rest_framework import serializers

from .models import CreditAccount, CreditInvoice, SupplierSettings


class SupplierSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierSettings
        fields = (
            "id",
            "default_reminder_days",
            "sms_reminders_enabled",
            "card_number",
            "card_holder",
            "account_number",
            "iban",
            "reminder_template",
            "receipt_payment_enabled",
            "online_payment_enabled",
            "order_notify_enabled",
            "order_notify_name",
            "order_notify_phone",
            "order_reminder_hours",
            "order_notify_template",
        )


class CreditAccountSerializer(serializers.ModelSerializer):
    shop_name = serializers.SerializerMethodField()
    shop_phone = serializers.CharField(source="shop.phone", read_only=True)
    effective_reminder_days = serializers.IntegerField(read_only=True)
    outstanding = serializers.IntegerField(read_only=True)

    class Meta:
        model = CreditAccount
        fields = (
            "id",
            "shop",
            "shop_name",
            "shop_phone",
            "credit_limit",
            "settlement_days",
            "reminder_days",
            "effective_reminder_days",
            "outstanding",
            "is_active",
        )

    def get_shop_name(self, obj):
        profile = getattr(obj.shop, "shop_profile", None)
        return (profile.shop_name if profile else "") or obj.shop.full_name


class CreditInvoiceSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.number", read_only=True)
    shop_name = serializers.SerializerMethodField()
    days_to_due = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = CreditInvoice
        fields = (
            "id",
            "order_number",
            "shop_name",
            "amount",
            "issued_at",
            "due_date",
            "days_to_due",
            "is_overdue",
            "is_settled",
            "settled_at",
            "reminder_sent_at",
        )

    def get_shop_name(self, obj):
        profile = getattr(obj.account.shop, "shop_profile", None)
        return (profile.shop_name if profile else "") or obj.account.shop.full_name
