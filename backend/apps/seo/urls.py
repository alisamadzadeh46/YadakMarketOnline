from django.urls import path

from .views import SeoAnalyzeView

urlpatterns = [
    path("analyze/", SeoAnalyzeView.as_view(), name="seo_analyze"),
]
