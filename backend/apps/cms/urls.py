from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("slides", views.PublicSlideViewSet, basename="slide")
router.register("manage/slides", views.ManageSlideViewSet, basename="manage-slide")
router.register("manage/contacts", views.ManageContactViewSet, basename="manage-contact")

urlpatterns = [
    path("newsletter/subscribe/", views.NewsletterSubscribeView.as_view(), name="newsletter_subscribe"),
    path("contact/", views.ContactSubmitView.as_view(), name="contact_submit"),
    path("manage/subscribers/", views.ManageSubscribersView.as_view(), name="manage_subscribers"),
] + router.urls
