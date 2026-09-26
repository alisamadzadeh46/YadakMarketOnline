"""Import the Venda brake-pad / brake-shoe list for a given supplier.

Unlike ``import_pricelist`` (which parses the raw Excel), this command reads a
pre-parsed JSON produced from the two-table Venda sheet. Each record already
carries the final storefront price (unit price in Toman, +12% supplier markup
baked in), so the command stays a dumb, auditable upsert.

SKUs are namespaced with a ``VND-`` prefix so they can never collide with the
existing SKP catalog codes and silently overwrite another supplier's product.

    python manage.py import_venda /path/to/venda.json --supplier 09xxxxxxxxx
"""

import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.catalog.models import Brand, CarBrand, CarModel, Category, Product

User = get_user_model()

BRAND_NAME = "وندا"
CATEGORY_NAME = "لنت و کفشک ترمز"

# Best-effort maker lookup so the "fits these cars" box + /shop?car
# filter work. Anything unmatched falls back to a generic bucket.
MAKER_TOKENS = [
    ("ایران خودرو", ["پیکان", "پژو", "سمند", "دنا", "رانا", "روآ", "سورن", "تارا", "ELX", "EF7"]),
    ("سایپا", ["پراید", "تیبا", "ساینا", "کوییک", "شاهین", "ریو", "کیارساتو", "ساندرو", "کاپرا"]),
    ("رنو", ["L90", "تالیسمان", "مگان", "تندر", "داستر"]),
    ("نیسان", ["نیسان"]),
    ("چری", ["تیگو", "چری", "آریو", "آریزو", "دیگنین"]),
    ("هیوندای", ["هیوندا", "سوناتا", "سانتافه", "ورنا", "النترا", "النتا", "آزرا"]),
    (
        "تویوتا",
        ["تویوتا", "تويوتا", "کمری", "کرولا", "کروﻻ", "پرادو", "راو4", "هایس", "هایلوکس", "یاریس", "لکسوس", "اوریون"],
    ),
    ("مزدا", ["مزدا"]),
    ("جک", ["جک", "جكJ", "S3", "S5", "J4", "J5"]),
    ("جیلی", ["جیلی", "جییل", "امگرند"]),
    ("برلیانس", ["برلیانس"]),
    ("ام‌وی‌ام", ["MVM", "ام وی ام"]),
    ("هایما", ["هایما"]),
    ("کی‌ام‌سی", ["KMC"]),
    ("لیفان", ["لیفان"]),
    ("میتسوبیشی", ["میتسوبیش", "دلیکا", "اوتلندر"]),
    ("سوزوکی", ["سوزوک", "سوزیوک", "ویتارا"]),
    ("دوو", ["دوو", "سیلو"]),
    ("زانتیا", ["زانتیا"]),
]


class Command(BaseCommand):
    help = "Import/refresh the Venda brake list for a supplier from parsed JSON."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Path to the parsed venda.json")
        parser.add_argument(
            "--supplier",
            required=True,
            help="Mobile number of the supplier account that owns the imported products.",
        )
        parser.add_argument("--default-stock", type=int, default=50)
        parser.add_argument("--dry-run", action="store_true")

    def _car(self, car_name):
        if car_name in self._cars:
            return self._cars[car_name]
        maker = next(
            (m for m, tokens in MAKER_TOKENS if any(t in car_name for t in tokens)),
            "سایر خودروها",
        )
        brand = CarBrand.objects.get_or_create(name=maker)[0]
        model = CarModel.objects.get_or_create(brand=brand, name=car_name)[0]
        self._cars[car_name] = model
        return model

    def handle(self, *args, **opts):
        supplier = User.objects.filter(phone=opts["supplier"]).first()
        if not supplier:
            raise CommandError(f"Supplier with phone {opts['supplier']} not found")

        with open(opts["path"], encoding="utf-8") as handle:
            items = json.load(handle)
        brand = Brand.objects.get_or_create(
            name=BRAND_NAME, defaults={"slug": slugify(BRAND_NAME, allow_unicode=True)}
        )[0]
        category = Category.objects.get_or_create(
            name=CATEGORY_NAME,
            defaults={"slug": slugify(CATEGORY_NAME, allow_unicode=True), "icon": "part"},
        )[0]

        self._cars = {}
        created = updated = 0
        with transaction.atomic():
            for it in items:
                sku = it["sku"]
                # The brand belongs in the brand field only — a name ending in
                # a trailing brand word would print the brand twice on the product page.
                name = it["name"].strip()
                if name.endswith(f" {BRAND_NAME}"):
                    name = name[: -(len(BRAND_NAME) + 1)].strip()
                defaults = {
                    "name": name,
                    "brand": brand,
                    "category": category,
                    "supplier": supplier,
                    "price": it["price"],
                    "stock": opts["default_stock"],
                    "carton_qty": it.get("carton_qty"),
                    "min_order_qty": 1,
                    "is_active": True,
                    # No auto-generated blurb: the product page already prints
                    # name / brand / part code from their own fields, so a generated
                    # sentence repeating them just duplicates the same facts.
                    "authenticity": "اصل شرکتی",
                }
                if opts["dry_run"]:
                    created += 1
                    continue

                product = Product.objects.filter(sku=sku).first()
                if product:
                    # Only touch rows that are already ours — never hijack another
                    # supplier's product that happens to share a namespaced code.
                    if product.supplier_id not in (None, supplier.id):
                        continue
                    for f, v in defaults.items():
                        setattr(product, f, v)
                    product.save()
                    updated += 1
                else:
                    defaults["slug"] = slugify(it["name"], allow_unicode=True) or "product"
                    if Product.objects.filter(slug=defaults["slug"]).exists():
                        defaults["slug"] = f"{defaults['slug']}-{sku}"[:220]
                    product = Product.objects.create(sku=sku, **defaults)
                    created += 1

                car = self._car(it["car"])
                product.compatible_cars.set([car])

            if opts["dry_run"]:
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"supplier={supplier.full_name or supplier.phone} "
                f"created={created} updated={updated} cars={len(self._cars)}"
                + (" [DRY RUN]" if opts["dry_run"] else "")
            )
        )
