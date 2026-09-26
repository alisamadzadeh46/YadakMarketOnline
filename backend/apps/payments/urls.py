"""Payment gateway routes mounted under /api/payments/."""

from django.urls import path

from . import views

urlpatterns = [
    path("settings/", views.PaymentGatewaySettingsView.as_view(), name="payment_gateway_settings"),
    path("gateways/", views.PaymentGatewayChoicesView.as_view(), name="payment_gateway_choices"),
    path("start/<str:number>/", views.PaymentStartView.as_view(), name="payment_start"),
    path("callback/<str:gateway>/", views.PaymentCallbackView.as_view(), name="payment_callback"),
]
