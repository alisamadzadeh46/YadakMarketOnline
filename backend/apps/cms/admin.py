from django.contrib import admin

from .models import ContactMessage, NewsletterSubscriber, Slide


@admin.register(Slide)
class SlideAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "is_active")
    list_editable = ("order", "is_active")


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("email",)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "subject", "phone", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("name", "subject", "message")
