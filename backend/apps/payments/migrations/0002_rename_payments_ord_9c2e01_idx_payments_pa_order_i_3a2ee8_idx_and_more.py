from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="paymenttransaction",
            new_name="payments_pa_order_i_3a2ee8_idx",
            old_name="payments_ord_9c2e01_idx",
        ),
        migrations.AlterField(
            model_name="paymentgatewaysettings",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
    ]
