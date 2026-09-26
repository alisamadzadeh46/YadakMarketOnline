"""Re-encode gallery images that were uploaded before the size cap existed.

Uploads are normalised at the door now (apps.core.images), but everything
already in /media predates that. Run once after deploying:

    python manage.py resize_images            # report only, changes nothing
    python manage.py resize_images --apply    # actually rewrite them
"""

import contextlib
import os

from django.core.management.base import BaseCommand

from apps.catalog.models import ProductImage
from apps.core.images import MAX_EDGE, SKIP_UNDER_BYTES, normalize_image


class Command(BaseCommand):
    help = "Cap oversized product images to MAX_EDGE and re-encode them."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="write the changes")
        parser.add_argument("--max-edge", type=int, default=MAX_EDGE)
        parser.add_argument("--square", action="store_true", help="also pad every image onto a square canvas")

    def handle(self, *args, **opts):
        apply_changes = opts["apply"]
        max_edge = opts["max_edge"]
        square = opts["square"]
        try:
            from PIL import Image
        except ImportError:
            self.stderr.write("Pillow is not installed.")
            return

        checked = skipped = converted = failed = 0
        saved_bytes = 0

        for row in ProductImage.objects.select_related("product").iterator():
            if not row.image:
                continue
            checked += 1
            try:
                path = row.image.path
                before = os.path.getsize(path)
                with Image.open(path) as im:
                    width, height = im.size
            except Exception as exc:
                failed += 1
                self.stderr.write(f"  ! #{row.pk}: unreadable ({exc})")
                continue

            # Dimensions alone are not enough: a 1600x1600 PNG photo can still
            # be 3 MB, which is exactly what was making product pages 11 MB.
            needs_square = square and width != height
            if max(width, height) <= max_edge and before <= SKIP_UNDER_BYTES and not needs_square:
                skipped += 1
                continue

            self.stdout.write(
                f"  #{row.pk} {os.path.basename(path)}: {width}x{height}, {before // 1024} KB"
                + (" [not square]" if square and width != height else "")
            )
            if not apply_changes:
                converted += 1
                continue

            try:
                with open(path, "rb") as fh:
                    from django.core.files.uploadedfile import SimpleUploadedFile

                    original = SimpleUploadedFile(os.path.basename(path), fh.read())
                new_file = normalize_image(original, max_edge=max_edge, square=square)
                # save() writes a new name; drop the old file so /media doesn't
                # keep growing with orphans.
                old_path = path
                row.image.save(new_file.name, new_file, save=True)
                after = os.path.getsize(row.image.path)
                saved_bytes += max(0, before - after)
                converted += 1
                if os.path.abspath(old_path) != os.path.abspath(row.image.path):
                    with contextlib.suppress(OSError):
                        os.remove(old_path)
                self.stdout.write(f"     -> {after // 1024} KB")
            except Exception as exc:
                failed += 1
                self.stderr.write(f"  ! #{row.pk}: {exc}")

        verb = "converted" if apply_changes else "would convert"
        self.stdout.write(
            self.style.SUCCESS(
                f"checked={checked} {verb}={converted} already-ok={skipped} failed={failed} "
                f"saved={saved_bytes // 1024} KB"
            )
        )
        if not apply_changes and converted:
            self.stdout.write("Re-run with --apply to write the changes.")
