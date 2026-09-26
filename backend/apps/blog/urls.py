from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views, views_manage

extra = [
    path("manage/upload/", views_manage.MediaUploadView.as_view(), name="blog_media_upload"),
]

router = DefaultRouter()
router.register("manage/posts", views_manage.ManagePostViewSet, basename="manage-post")
router.register("manage/categories", views_manage.ManageBlogCategoryViewSet, basename="manage-blog-category")
router.register("posts", views.PostViewSet, basename="post")
router.register("categories", views.BlogCategoryViewSet, basename="blog-category")

urlpatterns = extra + router.urls
