"""Tidy product titles: move any remaining bracketed spec into the detail page
and clean stray punctuation, so the title shows only the product name.

For every product whose name still holds a «(…)» group (a dimension like
«۴۰سانت», a wire count «۶سیم», a side «چپ», a trim «SLX», …):
  * the text is saved as an "additional details" attribute (shown in the spec tab),
  * and removed from the name.

Guardrails:
  * a rename that would duplicate another product's exact name is skipped, so the
    two stay distinguishable in listings (dimension pairs keep their spec),
  * stray dots/commas used as separators are cleaned up (fixes «روآ.۲۰۶» and the
    lone dot under some titles),
  * slugs are left untouched so existing links keep working.

    python manage.py tidy_names --dry-run
    python manage.py tidy_names
"""

import re

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import AttributeName, Product, ProductAttribute

ATTR_NAME = "توضیحات تکمیلی"


def extract_specs(name: str):
    """Return (clean_name, [spec strings]) — pulls out every «(…)» group."""
    specs = [m.strip(" .،-–—") for m in re.findall(r"\(([^)]*)\)", name)]
    # also a trailing unbalanced «(…»
    tail = re.search(r"\(([^)]*)$", name)
    if tail:
        specs.append(tail.group(1).strip(" .،-–—"))
    clean = re.sub(r"\([^)]*\)", " ", name)
    clean = re.sub(r"\([^)]*$", " ", clean)
    # Collapse dot/comma separators and repeated spaces, trim stray punctuation.
    clean = re.sub(r"\s*[.،]\s*", " ", clean)
    clean = re.sub(r"\s{2,}", " ", clean).strip(" .،-–—")
    specs = [s for s in specs if s]
    return clean, specs


class Command(BaseCommand):
    help = "Move leftover bracketed specs from titles into a detail attribute."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        attr, _ = AttributeName.objects.get_or_create(name=ATTR_NAME)

        # Names currently in use, to detect collisions a rename would create.
        used = {}
        for pk, nm in Product.objects.values_list("id", "name"):
            used.setdefault(nm, set()).add(pk)

        moved = renamed = skipped_dup = dotted = 0
        plan = []
        for product in Product.objects.all():
            clean, specs = extract_specs(product.name)
            has_dot = clean != product.name and not specs and "(" not in product.name
            if not clean or clean == product.name:
                if has_dot:
                    dotted += 1
                    plan.append((product, clean, []))
                continue
            # Would this new name clash with a *different* product?
            owners = used.get(clean, set())
            if owners and owners != {product.id}:
                skipped_dup += 1
                continue
            plan.append((product, clean, specs))

        for product, clean, specs in plan[:12]:
            self.stdout.write(f"  {product.name}\n     -> {clean}   specs={specs}")

        if opts["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN — {len(plan)} names to tidy, "
                    f"{sum(1 for _, _, s in plan if s)} carry a spec, "
                    f"skipped {skipped_dup} to avoid duplicate names"
                )
            )
            return

        with transaction.atomic():
            for product, clean, specs in plan:
                if specs:
                    value = "، ".join(dict.fromkeys(specs))  # de-dup, keep order
                    ProductAttribute.objects.get_or_create(product=product, name=attr, defaults={"value": value})
                    moved += 1
                product.name = clean
                product.save(update_fields=["name"])
                renamed += 1

        self.stdout.write(
            self.style.SUCCESS(f"renamed={renamed} specs_moved_to_detail={moved} skipped_duplicate={skipped_dup}")
        )
