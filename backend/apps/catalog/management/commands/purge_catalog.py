"""Wipe every product and category from the site.

Destructive and irreversible — take a database dump first. Dry-run by default:

    python manage.py purge_catalog                    # report only
    python manage.py purge_catalog --apply            # delete
    python manage.py purge_catalog --apply --keep-orders

``OrderItem.product`` is PROTECT, so a product that appears on any invoice
cannot be deleted while that order exists. The default therefore removes orders
too; ``--keep-orders`` refuses instead of destroying sales history, which is
the safer choice on a store that has taken real money.

Brands are deliberately left alone — they carry no stock and rebuilding them is
pure busywork. Pass --brands to drop them as well.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import (
    Brand,
    Category,
    PriceTier,
    Product,
    ProductAttribute,
    ProductImage,
    Review,
)
from apps.orders.models import CartItem, Order, OrderItem


class Command(BaseCommand):
    help = "Delete all products and categories (and, by default, the orders that reference them)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="actually delete")
        parser.add_argument(
            "--keep-orders", action="store_true", help="abort instead of deleting orders that reference products"
        )
        parser.add_argument("--brands", action="store_true", help="also delete brands")

    def handle(self, *args, **opts):
        apply_changes = opts["apply"]
        keep_orders = opts["keep_orders"]
        drop_brands = opts["brands"]

        counts = {
            "محصولات": Product.objects.count(),
            "دسته‌بندی‌ها": Category.objects.count(),
            "تصاویر محصول": ProductImage.objects.count(),
            "مشخصات فنی": ProductAttribute.objects.count(),
            "قیمت پلکانی": PriceTier.objects.count(),
            "نظرات": Review.objects.count(),
            "اقلام سبد خرید": CartItem.objects.count(),
            "اقلام سفارش": OrderItem.objects.count(),
            "سفارش‌ها": Order.objects.count(),
        }
        if drop_brands:
            counts["برندها"] = Brand.objects.count()

        self.stdout.write("خواهد حذف شد:" if apply_changes else "در حالت گزارش (چیزی حذف نمی‌شود):")
        for label, n in counts.items():
            self.stdout.write(f"  {label:16} {n}")

        blocking = OrderItem.objects.values("order").distinct().count() if counts["اقلام سفارش"] else 0
        if blocking and keep_orders:
            self.stderr.write(
                f"\n{blocking} سفارش به محصولات وصل است و --keep-orders داده شده. "
                "بدون حذف سفارش‌ها، محصولات قابل حذف نیستند. متوقف شد."
            )
            return

        if not apply_changes:
            self.stdout.write("\nبرای اجرای واقعی: --apply")
            return

        with transaction.atomic():
            # Order matters: release the PROTECT reference before the products.
            CartItem.objects.all().delete()
            OrderItem.objects.all().delete()
            Order.objects.all().delete()
            Review.objects.all().delete()
            PriceTier.objects.all().delete()
            ProductAttribute.objects.all().delete()
            ProductImage.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            if drop_brands:
                Brand.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"\nانجام شد. باقی‌مانده — محصولات: {Product.objects.count()} · "
                f"دسته‌بندی‌ها: {Category.objects.count()} · "
                f"سفارش‌ها: {Order.objects.count()} · برندها: {Brand.objects.count()}"
            )
        )
        self.stdout.write("توجه: فایل‌های تصویر در /media حذف نشدند؛ در صورت نیاز دستی پاک کنید.")
