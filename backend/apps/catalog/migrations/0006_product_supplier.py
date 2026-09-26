from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def assign_existing(apps, schema_editor):
    """Give every existing product to the current main supplier so nothing is
    left ownerless when the multi-supplier model goes live."""
    Product = apps.get_model("catalog", "Product")
    User = apps.get_model("accounts", "User")
    supplier = (
        User.objects.filter(role="supplier").order_by("id").first()
        or User.objects.filter(is_superuser=True).order_by("id").first()
    )
    if supplier:
        Product.objects.filter(supplier__isnull=True).update(supplier=supplier)


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0005_product_carton_qty"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="supplier",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="supplied_products",
                to=settings.AUTH_USER_MODEL,
                verbose_name="تامین‌کننده",
            ),
        ),
        migrations.RunPython(assign_existing, migrations.RunPython.noop),
    ]
