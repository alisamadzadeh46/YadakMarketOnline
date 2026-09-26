# Enables Postgres trigram similarity for fuzzy (typo-tolerant) search and
# adds the authenticity/warranty fields to Product.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            reverse_sql="DROP EXTENSION IF EXISTS pg_trgm;",
        ),
        migrations.AddField(
            model_name="product",
            name="authenticity",
            field=models.CharField(
                blank=True, default="اصل شرکتی",
                help_text="مثلا: اصل شرکتی، اورجینال وارداتی",
                max_length=100, verbose_name="وضعیت اصالت",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="warranty_text",
            field=models.CharField(
                blank=True, help_text="مثلا: ۱۸ ماه گارانتی شرکتی",
                max_length=150, verbose_name="گارانتی",
            ),
        ),
    ]
