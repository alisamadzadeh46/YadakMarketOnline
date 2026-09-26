from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.orders"
    verbose_name = "Orders & payments"

    def ready(self):
        from . import signals  # noqa: F401  (registers periodic task on migrate)
