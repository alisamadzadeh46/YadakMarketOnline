"""Let the buyer pick their gateway instead of the site forcing one.

``active_gateway`` stops meaning "the only gateway" and starts meaning "the one
preselected"; the new per-gateway flags decide what is offered at all.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0002_rename_payments_ord_9c2e01_idx_payments_pa_order_i_3a2ee8_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentgatewaysettings",
            name="bitpay_enabled",
            field=models.BooleanField(
                default=True,
                help_text="اگر خاموش باشد، بیت‌پی در صفحه پرداخت به خریدار پیشنهاد نمی‌شود.",
                verbose_name="نمایش بیت‌پی به خریدار",
            ),
        ),
        migrations.AddField(
            model_name="paymentgatewaysettings",
            name="zarinpal_enabled",
            field=models.BooleanField(
                default=True,
                help_text="اگر خاموش باشد، زرین‌پال در صفحه پرداخت به خریدار پیشنهاد نمی‌شود.",
                verbose_name="نمایش زرین‌پال به خریدار",
            ),
        ),
        migrations.AlterField(
            model_name="paymentgatewaysettings",
            name="active_gateway",
            field=models.CharField(
                choices=[("none", "غیرفعال"), ("bitpay", "بیت‌پی"), ("zarinpal", "زرین‌پال")],
                default="none",
                help_text="درگاهی که هنگام پرداخت از قبل انتخاب شده است.",
                max_length=10,
                verbose_name="درگاه پیش‌فرض",
            ),
        ),
    ]
