from django.contrib import admin

from .models import Coupon, CouponRedemption


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "kind", "value", "used_count", "usage_limit", "is_active", "valid_to")
    list_filter = ("kind", "is_active")
    search_fields = ("code",)


@admin.register(CouponRedemption)
class CouponRedemptionAdmin(admin.ModelAdmin):
    list_display = ("coupon", "user", "amount", "created_at")
    search_fields = ("coupon__code", "user__phone")
