from django.contrib import admin

from .models import CreditAccount, CreditInvoice, SupplierSettings


@admin.register(SupplierSettings)
class SupplierSettingsAdmin(admin.ModelAdmin):
    list_display = ("supplier", "default_reminder_days", "sms_reminders_enabled")


@admin.register(CreditAccount)
class CreditAccountAdmin(admin.ModelAdmin):
    list_display = ("shop", "supplier", "credit_limit", "settlement_days", "reminder_days", "is_active")
    list_filter = ("is_active",)
    search_fields = ("shop__phone", "supplier__phone")


@admin.register(CreditInvoice)
class CreditInvoiceAdmin(admin.ModelAdmin):
    list_display = ("__str__", "account", "amount", "due_date", "is_settled", "reminder_sent_at")
    list_filter = ("is_settled", "due_date")
    search_fields = ("account__shop__phone", "order__number")
    actions = ("mark_settled",)

    @admin.action(description="ثبت تسویه")
    def mark_settled(self, request, queryset):
        for inv in queryset:
            inv.settle()
