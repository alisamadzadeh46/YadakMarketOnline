"""Order routes mounted under /api/orders/."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("orders", views.OrderViewSet, basename="order")
router.register("supplier/orders", views.SupplierOrderViewSet, basename="supplier-order")

urlpatterns = [
    path("cart/", views.CartView.as_view(), name="cart"),
    path("checkout/", views.CheckoutView.as_view(), name="checkout"),
    path("checkout-settings/", views.CheckoutSettingsView.as_view(), name="checkout_settings"),
    path("", include(router.urls)),
]
