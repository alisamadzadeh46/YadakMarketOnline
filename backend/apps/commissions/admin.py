from django.contrib import admin

from .models import CategoryCommissionRate, CommissionEntry, CommissionSetting


@admin.register(CommissionSetting)
class CommissionSettingAdmin(admin.ModelAdmin):
    list_display = ("beneficiary", "default_rate", "min_rate", "max_rate", "is_active")

    def has_add_permission(self, request):
        # Singleton: edit row 1, never create a second configuration.
        return not CommissionSetting.objects.exists()


@admin.register(CategoryCommissionRate)
class CategoryCommissionRateAdmin(admin.ModelAdmin):
    list_display = ("category", "rate")
    autocomplete_fields = ("category",)


@admin.register(CommissionEntry)
class CommissionEntryAdmin(admin.ModelAdmin):
    list_display = ("order", "buyer", "buyer_role", "base_amount", "effective_rate", "amount", "status")
    list_filter = ("status", "buyer_role")
    search_fields = ("order__number", "buyer__phone", "buyer__full_name")
    readonly_fields = ("order", "beneficiary", "buyer", "base_amount", "effective_rate", "amount")
