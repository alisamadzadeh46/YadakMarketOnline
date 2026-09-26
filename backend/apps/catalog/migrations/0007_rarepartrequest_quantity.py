from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0006_product_supplier"),
    ]

    operations = [
        migrations.AddField(
            model_name="rarepartrequest",
            name="quantity",
            field=models.PositiveIntegerField(default=1, verbose_name="تعداد موردنیاز"),
        ),
    ]
