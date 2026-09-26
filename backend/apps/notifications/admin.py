from django.contrib import admin

from .models import SmsLog


@admin.register(SmsLog)
class SmsLogAdmin(admin.ModelAdmin):
    list_display = ("recipient", "kind", "is_sent", "provider", "created_at")
    list_filter = ("kind", "is_sent", "provider")
    search_fields = ("recipient", "message")
    readonly_fields = ("recipient", "message", "kind", "provider", "is_sent", "provider_ref", "created_at")
