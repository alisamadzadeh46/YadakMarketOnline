"""Remove the seeded demo catalog once real products are in.

`seed_demo` created placeholder products so the site had something to show
during development. They are identified by *not* being part of the supplier's
price list, i.e. their SKU is absent from the imported code set.

Products that already appear on an order are never deleted — that would break
order history — they are deactivated instead.

    python manage.py cleanup_demo --keep-from /tmp/pricelist.xlsx
    python manage.py cleanup_demo --keep-from /tmp/pricelist.xlsx --dry-run
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog.models import Brand, CarBrand, CarModel, Category, Product


class Command(BaseCommand):
    help = "Delete demo/seed products that are not in the supplier price list."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep-from",
            required=True,
            help="Price-list .xlsx whose part codes identify the real products",
        )
        parser.add_argument("--start-row", type=int, default=5)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        try:
            import openpyxl
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise CommandError("openpyxl is required") from exc

        sheet = openpyxl.load_workbook(opts["keep_from"], data_only=True).worksheets[0]
        keep = {str(row[5]).strip() for row in sheet.iter_rows(min_row=opts["start_row"], values_only=True) if row[5]}
        if not keep:
            raise CommandError("No part codes found in the price list — refusing to delete.")

        doomed = Product.objects.exclude(sku__in=keep)
        # An ordered product must survive: OrderItem protects it and the buyer
        # still needs to see what they bought.
        ordered = doomed.filter(orderitem__isnull=False).distinct()
        ordered_ids = set(ordered.values_list("id", flat=True))
        deletable = doomed.exclude(id__in=ordered_ids)

        self.stdout.write(
            f"price-list codes={len(keep)} | not-in-list={doomed.count()} | "
            f"deletable={deletable.count()} | kept-because-ordered={len(ordered_ids)}"
        )
        if opts["dry_run"]:
            for name, sku in deletable.values_list("name", "sku")[:10]:
                self.stdout.write(f"  would delete: {sku} {name}")
            self.stdout.write(self.style.WARNING("DRY RUN — nothing deleted"))
            return

        with transaction.atomic():
            deactivated = Product.objects.filter(id__in=ordered_ids).update(is_active=False)
            deleted, _ = deletable.delete()
            # Facets left with nothing attached are noise in the shop sidebar.
            empty_brands = Brand.objects.filter(products__isnull=True).delete()[0]
            empty_cats = Category.objects.filter(products__isnull=True, children__isnull=True).delete()[0]
            empty_models = CarModel.objects.filter(products__isnull=True).delete()[0]
            empty_makers = CarBrand.objects.filter(models__isnull=True).delete()[0]

        self.stdout.write(
            self.style.SUCCESS(
                f"deleted_rows={deleted} deactivated={deactivated} "
                f"pruned brands={empty_brands} categories={empty_cats} "
                f"car_models={empty_models} car_brands={empty_makers} "
                f"remaining={Product.objects.count()}"
            )
        )
