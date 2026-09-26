"""Reusable DRF permission classes for role-based access control."""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import User


def is_site_admin(user) -> bool:
    """The site owner: a superuser or an account with the admin role."""
    return bool(user and user.is_authenticated and (user.is_superuser or user.role == User.Role.ADMIN))


class IsSupplierOrAdmin(BasePermission):
    """Any supplier (for their own store) or the site owner may pass.

    Views using this permission must scope their data to ``request.user`` for
    suppliers; site-wide controls use ``IsSiteAdmin`` instead.
    """

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (is_site_admin(u) or u.role == User.Role.SUPPLIER))


class IsSiteAdmin(BasePermission):
    """Site-wide controls (KYC approval, taxonomy, content, communications)."""

    message = "این بخش فقط برای مدیر سایت در دسترس است."

    def has_permission(self, request, view):
        return is_site_admin(request.user)


class SupplierCreateAdminChange(BasePermission):
    """Suppliers may list and add shared records; only the site owner may edit
    or delete them, because every other supplier's products depend on them."""

    message = "ویرایش و حذف این مورد فقط برای مدیر سایت مجاز است."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS or request.method == "POST":
            return IsSupplierOrAdmin().has_permission(request, view)
        return is_site_admin(request.user)


class IsApprovedShopkeeper(BasePermission):
    """An auto-parts shop that has cleared KYC and can buy wholesale."""

    message = "حساب فروشگاه شما هنوز تایید نشده است."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.can_buy_wholesale)


class IsOwnerOrReadOnly(BasePermission):
    """Object-level: only the owning user may modify; anyone may read."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        owner = getattr(obj, "user", None)
        return owner == request.user
