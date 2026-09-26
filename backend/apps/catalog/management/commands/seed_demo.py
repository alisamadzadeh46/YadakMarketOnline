"""Populate the database with realistic demo catalog data.

Idempotent-ish: safe to run once on a fresh database. Creates brands, car
models, facets, ~40 products with dynamic attributes, and a welcome coupon.
"""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.catalog.models import (
    AttributeName,
    Brand,
    CarBrand,
    CarModel,
    Category,
    Color,
    Product,
    ProductAttribute,
    Size,
)
from apps.discounts.models import Coupon

BRANDS = ["BOSCH", "VALEO", "MANN", "NGK", "DENSO", "SKF", "GATES", "MAHLE", "BREMBO"]
CATEGORIES = [
    ("لنت و دیسک ترمز", "brake"),
    ("فیلتر و صافی", "filter"),
    ("روغن و روانکار", "oil"),
    ("لاستیک و رینگ", "tire"),
    ("قطعات موتوری", "engine"),
    ("برق و باتری", "battery"),
    ("تعلیق و فرمان", "susp"),
    ("لوازم مصرفی", "misc"),
]
CARS = {
    "ایران خودرو": ["پژو ۲۰۶", "پژو پارس", "سمند", "دنا", "تارا"],
    "سایپا": ["پراید", "تیبا", "کوییک", "شاهین"],
    "تویوتا": ["کرولا", "کمری"],
}
COLORS = [("مشکی", "#111111"), ("نقره‌ای", "#C0C0C0"), ("قرمز", "#D33"), ("آبی", "#2450C0")]
SIZES = ["کوچک", "متوسط", "بزرگ", "استاندارد"]
PART_NAMES = {
    "brake": ["لنت ترمز جلو", "دیسک ترمز", "لنت ترمز عقب", "کالیپر ترمز"],
    "filter": ["فیلتر روغن", "فیلتر هوا", "فیلتر کابین", "فیلتر بنزین"],
    "oil": ["روغن موتور سنتتیک", "روغن گیربکس", "مایع خنک‌کننده", "روغن ترمز DOT4"],
    "tire": ["لاستیک رادیال", "رینگ آلومینیومی", "والف تایر", "وزنه بالانس"],
    "engine": ["واشر سرسیلندر", "تسمه تایم", "پمپ آب", "شمع پلاتینی"],
    "battery": ["باتری ۶۰ آمپر", "دینام", "استارت", "رله چراغ"],
    "susp": ["کمک فنر جلو", "سیبک فرمان", "طبق چرخ", "بلبرینگ چرخ"],
    "misc": ["برف پاک‌کن", "لامپ هالوژن", "چراغ مه‌شکن", "بوق حلزونی"],
}
UNIT_BY_CAT = {"oil": Product.Unit.LITER, "tire": Product.Unit.PIECE}


class Command(BaseCommand):
    help = "Seed demo catalog data"

    def handle(self, *args, **options):
        random.seed(1405)

        brands = [Brand.objects.get_or_create(name=b)[0] for b in BRANDS]
        cats = [
            Category.objects.get_or_create(name=n, defaults={"icon": key, "order": i})[0]
            for i, (n, key) in enumerate(CATEGORIES)
        ]
        colors = [Color.objects.get_or_create(name=n, defaults={"hex_code": h})[0] for n, h in COLORS]
        sizes = [Size.objects.get_or_create(name=s)[0] for s in SIZES]

        car_models = []
        for cb_name, models_ in CARS.items():
            cb = CarBrand.objects.get_or_create(name=cb_name)[0]
            for m in models_:
                car_models.append(CarModel.objects.get_or_create(brand=cb, name=m)[0])

        attr_material = AttributeName.objects.get_or_create(name="جنس", defaults={"is_filterable": True})[0]
        attr_origin = AttributeName.objects.get_or_create(name="کشور سازنده", defaults={"is_filterable": True})[0]
        attr_warranty = AttributeName.objects.get_or_create(name="گارانتی")[0]

        materials = ["فلز", "سرامیک", "پلیمر", "کامپوزیت"]
        origins = ["آلمان", "ژاپن", "کره", "ایران", "ترکیه"]

        created = 0
        for (_cat_name, key), cat in zip(CATEGORIES, cats, strict=False):
            for _i, base_name in enumerate(PART_NAMES[key]):
                for variant in range(1, 3):
                    brand = random.choice(brands)
                    price = random.choice([420_000, 890_000, 1_650_000, 2_450_000, 3_500_000, 5_200_000])
                    has_off = random.random() < 0.4
                    compare = round(price / (1 - random.choice([0.1, 0.15, 0.2]))) if has_off else None
                    name = f"{base_name} {brand.name}" + (" پک ۴ عددی" if variant == 2 else "")
                    sku = f"{brand.name[:3]}-{random.randint(10000, 99999)}"
                    if Product.objects.filter(sku=sku).exists():
                        continue
                    p = Product.objects.create(
                        name=name,
                        brand=brand,
                        category=cat,
                        sku=sku,
                        short_description=f"{base_name} اصل با ضمانت اصالت کالا.",
                        description=(
                            f"{name} از برند {brand.name} با کیفیت استاندارد کارخانه‌ای، "
                            "مناسب فروش عمده به فروشگاه‌ها و تعمیرگاه‌ها."
                        ),
                        price=price,
                        compare_at_price=compare,
                        stock=random.randint(20, 400),
                        min_order_qty=random.choice([2, 4, 5, 10]),
                        unit=UNIT_BY_CAT.get(key, Product.Unit.PIECE),
                        is_featured=random.random() < 0.25,
                        sold_count=random.randint(50, 900),
                    )
                    p.colors.set(random.sample(colors, k=random.randint(1, 3)))
                    p.sizes.set(random.sample(sizes, k=random.randint(1, 2)))
                    p.compatible_cars.set(random.sample(car_models, k=random.randint(1, 4)))
                    ProductAttribute.objects.create(product=p, name=attr_material, value=random.choice(materials))
                    ProductAttribute.objects.create(product=p, name=attr_origin, value=random.choice(origins))
                    ProductAttribute.objects.create(product=p, name=attr_warranty, value="۱۸ ماه")
                    created += 1

        Coupon.objects.get_or_create(
            code="WELCOME15",
            defaults={
                "kind": Coupon.Kind.PERCENT,
                "value": 15,
                "max_discount": 500_000,
                "min_order_amount": 1_000_000,
                "valid_to": timezone.now() + timedelta(days=90),
                "per_user_limit": 1,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded: {Product.objects.count()} products ({created} new), "
                f"{Brand.objects.count()} brands, {Category.objects.count()} categories, "
                f"{CarModel.objects.count()} car models, coupon WELCOME15."
            )
        )
