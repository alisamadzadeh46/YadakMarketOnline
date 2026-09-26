import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("orders", "0001_initial"),
        ("commissions", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrderSupplierShare",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("gross_amount", models.PositiveBigIntegerField(default=0, verbose_name="مبلغ فروش")),
                ("owner_commission", models.PositiveBigIntegerField(default=0, verbose_name="پورسانت مدیر سایت")),
                ("supplier_net", models.PositiveBigIntegerField(default=0, verbose_name="سهم تامین‌کننده")),
                ("effective_rate", models.DecimalField(decimal_places=2, max_digits=5, verbose_name="درصد پورسانت")),
                ("status", models.CharField(choices=[("pending", "در انتظار تسویه سفارش"), ("earned", "قطعی‌شده"), ("paid", "پرداخت شد"), ("void", "باطل (سفارش لغو شد)")], db_index=True, default="earned", max_length=12, verbose_name="وضعیت")),
                ("note", models.CharField(blank=True, max_length=200, verbose_name="یادداشت")),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="supplier_shares", to="orders.order", verbose_name="سفارش")),
                ("supplier", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sale_shares", to=settings.AUTH_USER_MODEL, verbose_name="تامین‌کننده")),
            ],
            options={
                "verbose_name": "سهم فروش تامین‌کننده",
                "verbose_name_plural": "سهم فروش تامین‌کنندگان",
                "ordering": ("-created_at",),
                "unique_together": {("order", "supplier")},
                "indexes": [models.Index(fields=["supplier", "-created_at"], name="commissions_supplie_9e6c8f_idx")],
            },
        ),
    ]
