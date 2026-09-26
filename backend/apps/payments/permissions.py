"""Gateway credentials are site infrastructure — owner/admin only, not every supplier."""

from rest_framework.permissions import BasePermission

from apps.accounts.models import User


class IsPaymentGatewayAdmin(BasePermission):
    message = "این بخش فقط برای مدیر سایت در دسترس است."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_superuser or u.role == User.Role.ADMIN))
