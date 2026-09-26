from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0005_checkoutsettings_order_shipping_cost_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="checkoutsettings",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
    ]
