from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0004_order_supplier_reminded_at_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="CheckoutSettings",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("vat_percent", models.DecimalField(decimal_places=2, default=10, max_digits=5, verbose_name="درصد مالیات بر ارزش‌افزوده")),
                ("shipping_cost", models.PositiveBigIntegerField(default=0, verbose_name="هزینه ارسال (تومان)")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "تنظیمات مالی سفارش",
                "verbose_name_plural": "تنظیمات مالی سفارش",
            },
        ),
        migrations.AddField(
            model_name="order",
            name="shipping_cost",
            field=models.PositiveBigIntegerField(default=0, verbose_name="هزینه ارسال"),
        ),
        migrations.AddField(
            model_name="order",
            name="tax_amount",
            field=models.PositiveBigIntegerField(default=0, verbose_name="مالیات بر ارزش‌افزوده"),
        ),
    ]
