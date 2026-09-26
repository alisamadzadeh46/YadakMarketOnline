"""Strip car-fitment lists out of product names.

The price list writes fitment into the title, e.g.

    سنسور دریچه گاز ساژم پژو(405 -پارس - سمند)

The cars are already stored properly in Product.compatible_cars (the importer
parses them), so repeating them in the name is noise — the product page shows
them as a proper "fits" section instead.

IMPORTANT: a parenthetical is only removed when EVERY token inside it is a known
car name. Many groups carry essential specs instead — (چپ) / (راست),
(ایربگ دار) / (فاقد ایربگ), (چرخ جلو) / (چرخ عقب), (تک پل کاوردار) — and
deleting those would leave several different products with identical names.
Mixed groups such as «(پراید- سمند طرح بوش)» are left untouched for the same
reason: we cannot drop the spec half without losing meaning.

Slugs are deliberately NOT regenerated: existing URLs, links and search results
should keep working, and the slug is only an identifier.

    python manage.py clean_product_names --dry-run
    python manage.py clean_product_names
"""

import re

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import Product

# Every token we are confident names a car (not a spec). Kept lowercase-free
# because Persian has no case; matched after normalising separators.
CAR_TOKENS = {
    "405",
    "پژو405",
    "پژو 405",
    "206",
    "207",
    "پارس",
    "پژوپارس",
    "پژو پارس",
    "سمند",
    "سورن",
    "دنا",
    "رانا",
    "پیکان",
    "روآ",
    "روا",
    "زانتیا",
    "آریسان",
    "پراید",
    "تیبا",
    "ساینا",
    "کوییک",
    "کوئیک",
    "شاهین",
    "ریو",
    "نیسان",
    "وانت",
    "پراید وانت",
    "نیسان وانت",
    "تندر",
    "تندر90",
    "تندر 90",
    "l90",
    "90l",
    "90 l",
    "مگان",
    "ساندرو",
    "پژو",
    "گروه پژو",
    "آریو",
}

# Split on separators AND single spaces, because the sheet mixes them freely —
# «پراید پیکان» (space) and «پراید-پیکان» (dash) both mean two cars. Splitting
# on spaces too is safe: spec groups («چپ و راست»، «چرخ عقب») still contain
# non-car words, so they fail the all-cars test and are left alone.
SPLIT = re.compile(r"[-–—,،.‌/\s]+")

# Connector words to ignore when judging a group (so «پراید و تیبا» reads as two
# cars, while «چپ و راست» still keeps چپ/راست which are not cars).
IGNORE = {"و", "،", "-"}

_CAR_SET = None


def _norm(token: str) -> str:
    return re.sub(r"\s+", " ", token).strip().replace("ي", "ی").replace("ك", "ک").lower()


def is_car_group(inner: str) -> bool:
    """True when every meaningful token inside the parentheses names a car."""
    global _CAR_SET
    if _CAR_SET is None:
        # Pre-normalise the vocabulary, and split multi-word entries into single
        # words so «پژو پارس» matches the bare tokens «پژو» and «پارس» too.
        _CAR_SET = set()
        for c in CAR_TOKENS:
            n = _norm(c)
            _CAR_SET.add(n)
            _CAR_SET.update(n.split())
    parts = [_norm(t) for t in SPLIT.split(inner) if t.strip()]
    parts = [p for p in parts if p and p not in IGNORE]
    if not parts:
        return False
    return all(p in _CAR_SET for p in parts)


def clean_name(name: str) -> str:
    """Remove purely-car parentheticals; leave everything else alone."""

    def replace(match):
        return "" if is_car_group(match.group(1)) else match.group(0)

    # Tolerate the unbalanced «(» the sheet occasionally contains.
    cleaned = re.sub(r"\(([^)]*)\)", replace, name)
    cleaned = re.sub(r"\(([^)]*)$", lambda m: "" if is_car_group(m.group(1)) else m.group(0), cleaned)
    return re.sub(r"\s{2,}", " ", cleaned).strip(" -–—،,")


class Command(BaseCommand):
    help = "Remove car-fitment lists from product names (kept in compatible_cars)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        changed, skipped_collision = [], []
        seen = {}

        for product in Product.objects.all().only("id", "name", "sku"):
            new = clean_name(product.name)
            if not new or new == product.name:
                continue
            # Never let two products collapse onto the same name.
            if new in seen:
                skipped_collision.append((product.sku, product.name))
                continue
            seen[new] = product.sku
            changed.append((product, new))

        for product, new in changed[:15]:
            self.stdout.write(f"  {product.name}\n     -> {new}")

        if opts["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN — would rename {len(changed)}, skipped {len(skipped_collision)} to avoid duplicate names"
                )
            )
            return

        with transaction.atomic():
            for product, new in changed:
                product.name = new
                product.save(update_fields=["name"])

        self.stdout.write(self.style.SUCCESS(f"renamed={len(changed)} skipped_collision={len(skipped_collision)}"))
