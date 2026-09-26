"""Import the supplier's Excel price list into the catalog.

The sheet is right-to-left, so openpyxl sees the columns in this order:
    A (blank) | B price (Rial) | C carton qty | D product group | E name
    F part code | G row number

Conventions the file uses that we translate into catalog data:
  * A price cell of «*» means the item is currently out of stock (no price yet).
  * Prices are quoted in Rial; the storefront works in Toman, so we divide by 10.
  * The product group becomes a Category.
  * The brand and the cars a part fits are written inside the product name,
    so we parse them out into real Brand / CarModel rows that drive the filters.

Re-running is safe: products are matched on their part code (SKU) and updated
in place, so this doubles as the "refresh prices" routine each time the
supplier sends a new sheet.

    python manage.py import_pricelist /path/to/pricelist.xlsx
"""

import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.catalog.models import (
    Brand,
    CarBrand,
    CarModel,
    Category,
    Color,
    Product,
)

# --- Parsing tables ---------------------------------------------------------

# Part manufacturers that appear inside product names, longest first so
# «طرح زیمنس» is not mistaken for a bare «زیمنس» match.
BRAND_PATTERNS = [
    ("SSAT", "SSAT"),
    ("زیمنس", "زیمنس"),
    ("ساژم", "ساژم"),
    ("بوش", "بوش"),
    ("والئو", "والئو"),
    ("کروز", "کروز"),
    ("دلفي", "دلفی"),
    ("دلفی", "دلفی"),
    ("مارلي", "مارلی"),
    ("مارلی", "مارلی"),
    ("ایساکو", "ایساکو"),
]
# Everything on this price list is manufactured under the supplier's own SKP
# brand; the maker names inside product titles (Siemens, Sagem, ...) describe the
# system the part is designed for, not who made it.
GENERIC_BRAND = "SKP"

# Car models written into names -> (maker, canonical model name).
CAR_PATTERNS = [
    ("ایران خودرو", "پژو ۴۰۵", ["405"]),
    ("ایران خودرو", "پژو ۲۰۶", ["206"]),
    ("ایران خودرو", "پژو ۲۰۷", ["207"]),
    ("ایران خودرو", "پژو پارس", ["پارس"]),
    ("ایران خودرو", "سمند", ["سمند"]),
    ("ایران خودرو", "سورن", ["سورن"]),
    ("ایران خودرو", "دنا", ["دنا"]),
    ("ایران خودرو", "رانا", ["رانا"]),
    ("ایران خودرو", "پیکان", ["پیکان"]),
    ("ایران خودرو", "روآ", ["روآ", "روا"]),
    ("ایران خودرو", "تندر ۹۰", ["تندر", "L90", "90L", "90 L"]),
    ("سایپا", "پراید", ["پراید"]),
    ("سایپا", "تیبا", ["تیبا"]),
    ("سایپا", "ساینا", ["ساینا"]),
    ("سایپا", "کوییک", ["کوییک"]),
    ("سایپا", "شاهین", ["شاهین"]),
    ("سایپا", "ریو", ["ریو"]),
    ("زامیاد", "نیسان وانت", ["نیسان"]),
    ("ایران خودرو", "زانتیا", ["زانتیا"]),
]

COLOR_PATTERNS = [
    ("مشکي", "مشکی", "#1B1B1B"),
    ("مشکی", "مشکی", "#1B1B1B"),
    ("طوسي", "طوسی", "#8C8C8C"),
    ("طوسی", "طوسی", "#8C8C8C"),
    ("آبي", "آبی", "#1F6FEB"),
    ("آبی", "آبی", "#1F6FEB"),
    ("سبز", "سبز", "#1F9D63"),
    ("قرمز", "قرمز", "#E24545"),
    ("زرد", "زرد", "#F2C81B"),
    ("سفید", "سفید", "#F4F4F4"),
    ("قهوه", "قهوه‌ای", "#7A4A2B"),
]

# Category icon keys the frontend already knows how to draw.
ICON_HINTS = [
    ("سنسور", "sensor"),
    ("کویل", "coil"),
    ("شمع", "spark"),
    ("وایر", "wire"),
    ("رله", "relay"),
    ("سوکت", "socket"),
    ("پمپ", "pump"),
    ("کلید", "switch"),
    ("فیوز", "fuse"),
    ("موتور", "motor"),
    ("صافي", "filter"),
    ("انژکتور", "injector"),
]

DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def clean(value):
    """Trim, normalise digits + Arabic letters, and drop the odd zero-width
    characters Excel exports leave behind in Persian text."""
    if value is None:
        return ""
    import unicodedata

    text = unicodedata.normalize("NFKC", str(value))  # fixes ﻻ-style ligatures
    text = text.translate(DIGITS)
    text = text.replace("ي", "ی").replace("ك", "ک")  # Arabic yeh/kaf -> Persian
    text = text.replace("‌", " ").replace("‏", "").replace("‎", "")
    return re.sub(r"\s+", " ", text).strip()


def parse_int(value):
    text = re.sub(r"[^\d]", "", clean(value))
    return int(text) if text else None


class Command(BaseCommand):
    help = "Import/refresh products from the supplier's Excel price list."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Path to the .xlsx price list")
        parser.add_argument("--sheet", default=None, help="Sheet name (defaults to the first sheet)")
        parser.add_argument(
            "--start-row",
            type=int,
            default=5,
            help="First data row; rows above it are the merged header (default 5)",
        )
        parser.add_argument(
            "--default-stock",
            type=int,
            default=50,
            help="Stock to set for in-stock items (default 50)",
        )
        parser.add_argument(
            "--rial",
            action="store_true",
            default=True,
            help="Treat sheet prices as Rial and store Toman (default on)",
        )
        parser.add_argument("--dry-run", action="store_true", help="Parse and report without writing")

    # -- lookup helpers, each memoised for the length of one import ----------

    def _brand(self, name):
        if name not in self._brands:
            self._brands[name] = Brand.objects.get_or_create(
                name=name, defaults={"slug": slugify(name, allow_unicode=True)}
            )[0]
        return self._brands[name]

    def _category(self, name):
        if name not in self._categories:
            icon = next((k for word, k in ICON_HINTS if word in name), "part")
            self._categories[name] = Category.objects.get_or_create(
                name=name,
                defaults={"slug": slugify(name, allow_unicode=True), "icon": icon},
            )[0]
        return self._categories[name]

    def _car(self, maker, model):
        key = (maker, model)
        if key not in self._cars:
            brand = CarBrand.objects.get_or_create(name=maker)[0]
            self._cars[key] = CarModel.objects.get_or_create(brand=brand, name=model)[0]
        return self._cars[key]

    def _color(self, name, hex_code):
        if name not in self._colors:
            self._colors[name] = Color.objects.get_or_create(name=name, defaults={"hex_code": hex_code})[0]
        return self._colors[name]

    def _unique_slug(self, name, sku):
        """Names repeat across variants, so fall back to the part code."""
        base = slugify(name, allow_unicode=True) or "product"
        candidate = base
        if Product.objects.filter(slug=candidate).exclude(sku=sku).exists():
            candidate = f"{base}-{sku}"
        return candidate[:220]

    # -- main ---------------------------------------------------------------

    def handle(self, *args, **opts):
        try:
            import openpyxl
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise CommandError("openpyxl is required: pip install openpyxl") from exc

        workbook = openpyxl.load_workbook(opts["path"], data_only=True)
        sheet = workbook[opts["sheet"]] if opts["sheet"] else workbook.worksheets[0]

        self._brands, self._categories, self._cars, self._colors = {}, {}, {}, {}
        created = updated = skipped = out_of_stock = 0
        seen_skus = set()

        rows = sheet.iter_rows(min_row=opts["start_row"], values_only=True)
        with transaction.atomic():
            for raw in rows:
                # Pad short rows so the fixed column offsets stay valid.
                cells = list(raw) + [None] * (7 - len(raw))
                price_cell, carton_cell = clean(cells[1]), clean(cells[2])
                group, name, sku = clean(cells[3]), clean(cells[4]), clean(cells[5])

                if not sku or not name or not group:
                    skipped += 1
                    continue
                if sku in seen_skus:
                    skipped += 1
                    continue
                seen_skus.add(sku)

                # «*» in the price column is the sheet's out-of-stock marker.
                is_out = "*" in price_cell or not price_cell
                rial = parse_int(price_cell) or 0
                price = rial // 10 if opts["rial"] else rial
                carton = parse_int(carton_cell)

                brand_name = GENERIC_BRAND
                cars = [
                    (maker, model) for maker, model, tokens in CAR_PATTERNS if any(token in name for token in tokens)
                ]
                colors = [(canon, hex_code) for token, canon, hex_code in COLOR_PATTERNS if token in name]

                if opts["dry_run"]:
                    created += 1
                    if is_out:
                        out_of_stock += 1
                    continue

                stock = 0 if is_out else opts["default_stock"]
                if is_out:
                    out_of_stock += 1

                defaults = {
                    "name": name,
                    "brand": self._brand(brand_name),
                    "category": self._category(group),
                    "price": price,
                    "stock": stock,
                    "carton_qty": carton,
                    "min_order_qty": 1,
                    "is_active": True,
                    # No auto-generated blurb: the product page already prints
                    # name / brand / part code from their own fields.
                    "authenticity": "اصل شرکتی",
                }
                product = Product.objects.filter(sku=sku).first()
                if product:
                    for field, value in defaults.items():
                        setattr(product, field, value)
                    product.save()
                    updated += 1
                else:
                    defaults["slug"] = self._unique_slug(name, sku)
                    product = Product.objects.create(sku=sku, **defaults)
                    created += 1

                # Facets: replace rather than append so a re-import stays exact.
                product.compatible_cars.set([self._car(maker, model) for maker, model in cars])
                product.colors.set([self._color(canon, hex_code) for canon, hex_code in colors])

            if opts["dry_run"]:
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"created={created} updated={updated} skipped={skipped} "
                f"out_of_stock={out_of_stock} "
                f"categories={len(self._categories)} brands={len(self._brands)} "
                f"cars={len(self._cars)} colors={len(self._colors)}"
                + (" [DRY RUN — nothing written]" if opts["dry_run"] else "")
            )
        )
