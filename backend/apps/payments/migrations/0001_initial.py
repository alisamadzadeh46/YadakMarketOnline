import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("orders", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentGatewaySettings",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("active_gateway", models.CharField(choices=[("none", "غیرفعال"), ("bitpay", "بیت‌پی"), ("zarinpal", "زرین‌پال")], default="none", max_length=10, verbose_name="درگاه فعال")),
                ("bitpay_api_key", models.CharField(blank=True, max_length=100, verbose_name="کد API بیت‌پی")),
                ("bitpay_sandbox", models.BooleanField(default=False, help_text="فعال باشد، تراکنش‌ها واقعی نیستند (محیط تست بیت‌پی).", verbose_name="حالت آزمایشی بیت‌پی")),
                ("zarinpal_merchant_id", models.CharField(blank=True, max_length=100, verbose_name="مرچنت کد زرین‌پال")),
                ("zarinpal_sandbox", models.BooleanField(default=False, help_text="فعال باشد، درگاه sandbox زرین‌پال استفاده می‌شود.", verbose_name="حالت آزمایشی زرین‌پال")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "تنظیمات درگاه پرداخت",
                "verbose_name_plural": "تنظیمات درگاه پرداخت",
            },
        ),
        migrations.CreateModel(
            name="PaymentTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("gateway", models.CharField(choices=[("none", "غیرفعال"), ("bitpay", "بیت‌پی"), ("zarinpal", "زرین‌پال")], max_length=10, verbose_name="درگاه")),
                ("amount", models.PositiveBigIntegerField(verbose_name="مبلغ (تومان)")),
                ("authority", models.CharField(blank=True, db_index=True, max_length=100, verbose_name="شناسه پرداخت درگاه")),
                ("trans_id", models.CharField(blank=True, max_length=100, verbose_name="شماره تراکنش بیت‌پی")),
                ("ref_id", models.CharField(blank=True, max_length=100, verbose_name="شماره پیگیری بانک")),
                ("card_number", models.CharField(blank=True, max_length=30, verbose_name="شماره کارت پرداخت‌کننده")),
                ("status", models.CharField(choices=[("pending", "در انتظار پرداخت"), ("success", "موفق"), ("failed", "ناموفق")], db_index=True, default="pending", max_length=10, verbose_name="وضعیت")),
                ("raw_response", models.JSONField(blank=True, null=True, verbose_name="پاسخ خام درگاه")),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payment_transactions", to="orders.order", verbose_name="سفارش")),
            ],
            options={
                "verbose_name": "تراکنش پرداخت",
                "verbose_name_plural": "تراکنش‌های پرداخت",
                "ordering": ("-created_at",),
                "indexes": [models.Index(fields=["order", "-created_at"], name="payments_ord_9c2e01_idx")],
            },
        ),
    ]
