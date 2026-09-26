"""Create (or update) the main supplier account and point notifications at it.

    python manage.py create_supplier --phone 09xxxxxxxxx --name "Supplier name"

Without --password a strong one is generated and printed once. The account is
role=supplier, approved and staff (so it can reach the supplier panel), and the
supplier-notification settings are wired to this account (name + phone).
"""

import secrets
import string

from apps.accounts.models import User
from apps.suppliers.models import SupplierSettings
from django.core.management.base import BaseCommand
from django.db import transaction


def _random_password(length=14):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class Command(BaseCommand):
    help = "Create/update the main supplier account and wire order notifications."

    def add_arguments(self, parser):
        parser.add_argument("--phone", required=True)
        parser.add_argument("--name", default="تامین‌کننده")
        parser.add_argument("--password", default=None)
        parser.add_argument("--notify-name", default="", help="Name used in «جناب آقای …»")

    @transaction.atomic
    def handle(self, *args, **opts):
        phone = opts["phone"].strip()
        password = opts["password"] or _random_password()

        user, created = User.objects.get_or_create(phone=phone)
        user.full_name = opts["name"]
        user.role = User.Role.SUPPLIER
        user.is_approved = True
        user.is_staff = True
        user.is_active = True
        if opts["password"] or created:
            user.set_password(password)
        user.save()

        settings_row = SupplierSettings.objects.get_or_create(supplier=user)[0]
        settings_row.order_notify_enabled = True
        settings_row.order_notify_name = opts["notify_name"] or opts["name"].split()[-1]
        # Deliver the new-order SMS to the supplier's own phone by default.
        if not settings_row.order_notify_phone:
            settings_row.order_notify_phone = phone
        settings_row.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"supplier {'created' if created else 'updated'}: {user.full_name} ({phone}), role={user.role}"
            )
        )
        if opts["password"] or created:
            self.stdout.write(self.style.WARNING(f"PASSWORD: {password}"))
        self.stdout.write(
            f"notify_name={settings_row.order_notify_name} notify_phone={settings_row.order_notify_phone}"
        )
