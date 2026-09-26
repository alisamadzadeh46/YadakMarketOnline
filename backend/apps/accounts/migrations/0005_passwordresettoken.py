import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_alter_user_role"),
    ]

    operations = [
        migrations.CreateModel(
            name="PasswordResetToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("token", models.CharField(db_index=True, max_length=100, unique=True, verbose_name="توکن")),
                ("expires_at", models.DateTimeField(verbose_name="انقضا")),
                ("is_used", models.BooleanField(default=False, verbose_name="استفاده شده")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="password_reset_tokens", to="accounts.user", verbose_name="کاربر")),
            ],
            options={
                "verbose_name": "توکن بازیابی رمز",
                "verbose_name_plural": "توکن‌های بازیابی رمز",
                "ordering": ("-created_at",),
            },
        ),
    ]
