"""Only the configured beneficiary (or a superuser) may see the money."""

from rest_framework.permissions import BasePermission

from .models import CommissionSetting


class IsCommissionBeneficiary(BasePermission):
    message = "این بخش فقط برای حساب دریافت‌کننده پورسانت در دسترس است."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser:
            return True
        return CommissionSetting.load().beneficiary_id == user.id
