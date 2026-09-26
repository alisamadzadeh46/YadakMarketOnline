from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("suppliers", "0003_suppliersettings_online_payment_enabled_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="suppliersettings",
            name="receipt_payment_enabled",
            field=models.BooleanField(default=False, verbose_name="پرداخت با فیش بانکی (کارت به کارت)"),
        ),
    ]
