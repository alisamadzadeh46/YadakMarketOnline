from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0004_rarepartrequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="carton_qty",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                help_text="چند عدد در هر کارتن بسته‌بندی می‌شود.",
                verbose_name="تعداد در کارتن",
            ),
        ),
    ]
