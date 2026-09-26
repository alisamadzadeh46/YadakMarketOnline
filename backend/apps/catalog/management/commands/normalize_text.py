"""Normalise Arabic characters to Persian across the catalogue.

The Excel price list was full of Arabic letters and broken presentation-form
ligatures that render with wrong dots or joined shapes:
  * «ي» (Arabic yeh, two dots)      -> «ی» (Persian yeh)
  * «ك» (Arabic kaf)                -> «ک» (Persian kaf)
  * «ﻻ» and friends (lam-alef ligature presentation forms) -> «لا»
NFKC folding fixes the ligatures/presentation forms; the two explicit swaps fix
yeh/kaf, which NFKC leaves alone because they are distinct base letters.

Applied to every user-visible text field. Slugs are left untouched so links keep
working. Idempotent — safe to re-run after each price-list import.

    python manage.py normalize_text --dry-run
    python manage.py normalize_text
"""

import re
import unicodedata

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import (
    Brand,
    CarBrand,
    CarModel,
    Category,
    Product,
    ProductAttribute,
)


def normalize(text: str) -> str:
    if not text:
        return text
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("ي", "ی").replace("ك", "ک")
    return re.sub(r"\s{2,}", " ", text).strip()


# (model, [text fields]) to sweep.
TARGETS = [
    (Product, ["name", "short_description", "description", "warranty_text"]),
    (Category, ["name"]),
    (CarModel, ["name"]),
    (CarBrand, ["name"]),
    (Brand, ["name"]),
    (ProductAttribute, ["value"]),
]


class Command(BaseCommand):
    help = "Convert Arabic letters/ligatures to Persian in all catalogue text."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        total = 0
        samples = []
        with transaction.atomic():
            for model, fields in TARGETS:
                changed = 0
                for obj in model.objects.all().only("id", *fields):
                    dirty = []
                    for f in fields:
                        old = getattr(obj, f) or ""
                        new = normalize(old)
                        if new != old:
                            setattr(obj, f, new)
                            dirty.append(f)
                            if len(samples) < 12 and f in ("name", "value"):
                                samples.append((old, new))
                    if dirty and not opts["dry_run"]:
                        obj.save(update_fields=dirty)
                    if dirty:
                        changed += 1
                total += changed
                self.stdout.write(f"  {model.__name__}: {changed} rows")
            if opts["dry_run"]:
                transaction.set_rollback(True)

        for old, new in samples:
            self.stdout.write(f"    {old}  ->  {new}")
        verb = "would fix" if opts["dry_run"] else "fixed"
        self.stdout.write(self.style.SUCCESS(f"{verb} {total} rows"))
