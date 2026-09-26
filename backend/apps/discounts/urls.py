from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CouponValidateView, ManageCouponViewSet

router = DefaultRouter()
router.register("manage/coupons", ManageCouponViewSet, basename="manage-coupon")

urlpatterns = [
    path("validate/", CouponValidateView.as_view(), name="coupon_validate"),
] + router.urls
