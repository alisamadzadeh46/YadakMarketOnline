"""Create (or update) the revenue-share partner account and point the
commission settings at it.

    python manage.py setup_partner --phone 09xxxxxxxxx \
        --email partner@example.com --name "Partner name" --rate 10

Without --password a strong one is generated and printed once.
"""

import secrets
import string
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.commissions.models import CommissionSetting


def _random_password(length=16):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class Command(BaseCommand):
    help = "Create the revenue-share partner account and wire the commission settings."

    def add_arguments(self, parser):
        parser.add_argument("--phone", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument("--name", default="شریک درآمدی")
        parser.add_argument("--password", default=None)
        parser.add_argument("--rate", default="10")
        parser.add_argument(
            "--keep-role",
            action="store_true",
            help="Do not change the user's role (use when the owner's existing "
            "admin account is also the revenue-share beneficiary).",
        )
        parser.add_argument(
            "--keep-password",
            action="store_true",
            help="Leave the existing password untouched.",
        )
        parser.add_argument("--min-rate", default="5")
        parser.add_argument("--max-rate", default="20")

    def handle(self, *args, **opts):
        password = opts["password"] or _random_password()
        user, created = User.objects.get_or_create(
            phone=opts["phone"],
            defaults={
                "email": opts["email"],
                "full_name": opts["name"],
                "role": User.Role.PARTNER,
                "is_approved": True,
                "phone_verified": True,
            },
        )
        if not created:
            user.email = opts["email"]
            user.full_name = opts["name"] or user.full_name
            if not opts["keep_role"]:
                user.role = User.Role.PARTNER
            user.is_approved = True
        if not opts["keep_password"]:
            user.set_password(password)
        user.save()

        setting = CommissionSetting.load()
        setting.beneficiary = user
        setting.min_rate = Decimal(opts["min_rate"])
        setting.max_rate = Decimal(opts["max_rate"])
        setting.default_rate = Decimal(opts["rate"])
        setting.is_active = True
        try:
            setting.full_clean(exclude=["beneficiary"])
        except Exception as exc:  # surface the band validation clearly
            raise CommandError(str(exc)) from exc
        setting.save()

        self.stdout.write(
            self.style.SUCCESS(f"partner {'created' if created else 'updated'}: {user.phone} / {user.email}")
        )
        self.stdout.write("password: unchanged" if opts["keep_password"] else f"password: {password}")
        self.stdout.write(f"rate: {setting.default_rate}% (band {setting.min_rate}–{setting.max_rate})")
