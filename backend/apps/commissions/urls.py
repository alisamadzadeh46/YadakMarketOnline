"""Revenue-share routes mounted under /api/commissions/."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("category-rates", views.CategoryRateViewSet, basename="category-rate")
router.register("entries", views.CommissionEntryActionViewSet, basename="commission-entry")

urlpatterns = [
    path("settings/", views.CommissionSettingView.as_view(), name="commission_settings"),
    path("summary/", views.CommissionSummaryView.as_view(), name="commission_summary"),
    path("by-supplier/", views.CommissionBySupplierView.as_view(), name="commission_by_supplier"),
    path("ledger/", views.CommissionEntryListView.as_view(), name="commission_ledger"),
    path("", include(router.urls)),
]
