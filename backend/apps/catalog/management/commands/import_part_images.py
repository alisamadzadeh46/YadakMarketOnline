"""Attach downloaded manufacturer photos to products, matched on part code.

Expects a directory holding `manifest.json` in the shape:

    {"110990010": ["110990010_0.webp", "110990010_1.jpg"], ...}

where each key is a part code (Product.sku) and the values are image files
sitting next to the manifest, ordered primary-first.

Products keep their existing gallery unless --replace is passed, so re-running
after downloading a few more photos only fills the gaps.

    python manage.py import_part_images /tmp/skp_images
"""

import json
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog.models import Product, ProductImage


class Command(BaseCommand):
    help = "Attach part photos to products by SKU, using a manifest.json index."

    def add_arguments(self, parser):
        parser.add_argument("directory", help="Folder containing manifest.json + images")
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Drop each product's existing gallery before attaching",
        )

    def handle(self, *args, **opts):
        folder = Path(opts["directory"])
        manifest_path = folder / "manifest.json"
        if not manifest_path.exists():
            raise CommandError(f"manifest.json not found in {folder}")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        attached = skipped_missing = skipped_has_images = 0

        with transaction.atomic():
            for sku, filenames in manifest.items():
                product = Product.objects.filter(sku=str(sku).strip()).first()
                if not product:
                    skipped_missing += 1
                    continue

                if opts["replace"]:
                    product.images.all().delete()
                elif product.images.exists():
                    skipped_has_images += 1
                    continue

                for order, filename in enumerate(filenames):
                    path = folder / filename
                    if not path.exists():
                        continue
                    with path.open("rb") as handle:
                        image = ProductImage(product=product, order=order, alt=product.name)
                        image.image.save(filename, File(handle), save=True)
                    attached += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"attached={attached} products_in_manifest={len(manifest)} "
                f"sku_not_in_catalog={skipped_missing} "
                f"already_had_images={skipped_has_images}"
            )
        )
