from django.contrib import admin

from .models import PaymentGatewaySettings, PaymentTransaction


@admin.register(PaymentGatewaySettings)
class PaymentGatewaySettingsAdmin(admin.ModelAdmin):
    list_display = ("active_gateway", "is_configured", "updated_at")

    def has_add_permission(self, request):
        return not PaymentGatewaySettings.objects.exists()


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("order", "gateway", "amount", "status", "ref_id", "created_at")
    list_filter = ("gateway", "status")
    search_fields = ("order__number", "authority", "trans_id", "ref_id")
    readonly_fields = [f.name for f in PaymentTransaction._meta.fields]

    def has_add_permission(self, request):
        return False
