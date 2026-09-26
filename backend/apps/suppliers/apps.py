from django.apps import AppConfig


class SuppliersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.suppliers"
    verbose_name = "Supplier credit & settlement"

    def ready(self):
        from . import signals  # noqa: F401
