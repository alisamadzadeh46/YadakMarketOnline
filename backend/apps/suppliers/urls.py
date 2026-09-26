"""Supplier/shop credit routes mounted under /api/suppliers/."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("credit-accounts", views.CreditAccountViewSet, basename="credit-account")
router.register("invoices", views.SupplierInvoiceViewSet, basename="supplier-invoice")
router.register("my-invoices", views.MyCreditInvoiceViewSet, basename="my-invoice")

urlpatterns = [
    path("dashboard/", views.SupplierDashboardView.as_view(), name="supplier_dashboard"),
    path("sms-logs/", views.SmsLogListView.as_view(), name="supplier_sms_logs"),
    path("reports/", views.SalesReportView.as_view(), name="supplier_reports"),
    path("earnings/", views.SupplierEarningsView.as_view(), name="supplier_earnings"),
    path("settings/", views.SupplierSettingsView.as_view(), name="supplier_settings"),
    path("payment-info/", views.PaymentInfoView.as_view(), name="payment_info"),
    path("payment-methods-admin/", views.SupplierPaymentMethodsAdminView.as_view(), name="payment_methods_admin"),
    path("", include(router.urls)),
]
