"""Admin cockpit for approving users and reviewing shop KYC.

This is where the site owner confirms whether a newly-registered account is a
regular customer or an approved auto-parts shop.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Address, KYCDocument, ShopkeeperProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("-date_joined",)
    list_display = ("phone", "full_name", "role", "is_approved", "is_active", "date_joined")
    list_filter = ("role", "is_approved", "is_active", "is_staff")
    search_fields = ("phone", "full_name", "email")
    readonly_fields = ("date_joined", "last_login")

    # Rebuilt fieldsets because the user model is keyed on phone, not username.
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        (_("اطلاعات فردی"), {"fields": ("full_name", "email", "phone_verified")}),
        (
            _("نقش و دسترسی"),
            {"fields": ("role", "is_approved", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        (_("تاریخ‌ها"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "full_name", "role", "password1", "password2"),
            },
        ),
    )

    actions = ("approve_accounts", "revoke_approval")

    @admin.action(description=_("تایید حساب انتخاب‌شده (اجازه خرید)"))
    def approve_accounts(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} حساب تایید شد.")

    @admin.action(description=_("لغو تایید حساب"))
    def revoke_approval(self, request, queryset):
        # Never lock out customers; only shops are gated by approval.
        updated = queryset.exclude(role=User.Role.CUSTOMER).update(is_approved=False)
        self.message_user(request, f"{updated} حساب از حالت تایید خارج شد.")


class KYCDocumentInline(admin.TabularInline):
    model = KYCDocument
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(ShopkeeperProfile)
class ShopkeeperProfileAdmin(admin.ModelAdmin):
    list_display = ("shop_name", "user", "city", "status", "reviewed_at")
    list_filter = ("status", "province", "city")
    search_fields = ("shop_name", "user__phone", "business_license_no")
    inlines = (KYCDocumentInline,)
    readonly_fields = ("reviewed_by", "reviewed_at")
    actions = ("approve_kyc", "reject_kyc")

    @admin.action(description=_("تایید احراز هویت و فعال‌سازی خرید عمده"))
    def approve_kyc(self, request, queryset):
        for profile in queryset:
            profile.approve(reviewer=request.user)
        self.message_user(request, f"{queryset.count()} فروشگاه تایید شد.")

    @admin.action(description=_("رد احراز هویت"))
    def reject_kyc(self, request, queryset):
        queryset.update(
            status=ShopkeeperProfile.Status.REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "city", "is_default")
    list_filter = ("province", "city", "is_default")
    search_fields = ("user__phone", "receiver_name", "city")
