from decimal import Decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("commissions", "0002_ordersuppliershare"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="ordersuppliershare",
            new_name="commissions_supplie_2e2e79_idx",
            old_name="commissions_supplie_9e6c8f_idx",
        ),
        migrations.AlterField(
            model_name="ordersuppliershare",
            name="effective_rate",
            field=models.DecimalField(
                decimal_places=2, max_digits=5, verbose_name="درصد پورسانت",
                validators=[
                    django.core.validators.MinValueValidator(Decimal("0")),
                    django.core.validators.MaxValueValidator(Decimal("100")),
                ],
            ),
        ),
    ]
