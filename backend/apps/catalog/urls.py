"""Catalog routes mounted under /api/catalog/."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views, views_feed, views_manage

extra = [
    path("feed/", views_feed.ProductFeedView.as_view(), name="product_feed"),
    path("suggest/", views.SearchSuggestView.as_view(), name="search_suggest"),
    path("manage/suppliers/", views_manage.SupplierChoicesView.as_view(), name="manage_supplier_choices"),
    path("stats/", views.SiteStatsView.as_view(), name="site_stats"),
    path("cartons/", views.CartonOptionsView.as_view(), name="carton_options"),
]

router = DefaultRouter()
router.register("manage/products", views_manage.ManageProductViewSet, basename="manage-product")
router.register("manage/categories", views_manage.ManageCategoryViewSet, basename="manage-category")
router.register("manage/brands", views_manage.ManageBrandViewSet, basename="manage-brand")
router.register("manage/colors", views_manage.ManageColorViewSet, basename="manage-color")
router.register("products", views.ProductViewSet, basename="product")
router.register("brands", views.BrandViewSet, basename="brand")
router.register("categories", views.CategoryViewSet, basename="category")
router.register("colors", views.ColorViewSet, basename="color")
router.register("sizes", views.SizeViewSet, basename="size")
router.register("cars", views.CarModelViewSet, basename="car")
router.register("rare-requests", views.RarePartRequestViewSet, basename="rare-request")
router.register("manage/rare-requests", views.ManageRarePartViewSet, basename="manage-rare-request")
router.register("reviews", views.ReviewCreateViewSet, basename="review")
router.register("favorites", views.FavoriteViewSet, basename="favorite")

urlpatterns = extra + router.urls
