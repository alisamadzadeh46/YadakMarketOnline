"""Catalog domain: brands, categories, products, gallery, dynamic attributes,
car-compatibility, reviews and favorites.

Design notes
------------
* Color / Size / CarModel are first-class so the shop can offer them as fast,
  indexed filters.
* Free-form product specs use a light EAV pair (AttributeName + ProductAttribute)
  so the supplier can add new spec rows from the admin without code changes.
* Ratings are denormalized onto Product (rating_avg / rating_count) and refreshed
  whenever a review is approved, keeping product listing queries cheap.
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.core.models import SeoModel, TimeStampedModel


def unique_slug(instance, source: str) -> str:
    """A slug that is safe to store in a unique column.

    Two failure modes this guards against, both of which surfaced as a raw 500
    from the panel's quick-add:
      * a name with no slug-able characters (punctuation, emoji, mangled
        encoding) slugifies to "" — and the *second* such row collides;
      * two different names can slugify to the same string.
    Falls back to the model name and appends a counter until it's free.
    """
    base = slugify(source, allow_unicode=True) or instance._meta.model_name
    model = instance.__class__
    slug, n = base, 2
    while model.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


class Brand(TimeStampedModel):
    """Manufacturer of the part (Bosch, Valeo, ...)."""

    name = models.CharField(_("نام برند"), max_length=120, unique=True)
    # Persian shops write the same brand in both scripts (Persian and "BOSCH"). Storing
    # the Latin form separately lets search match either spelling and lets the
    # storefront show the one the buyer recognises.
    name_en = models.CharField(_("نام انگلیسی"), max_length=120, blank=True)
    slug = models.SlugField(_("اسلاگ"), max_length=140, unique=True, allow_unicode=True)
    logo = models.ImageField(_("لوگو"), upload_to="brands/", blank=True, null=True)
    is_active = models.BooleanField(_("فعال"), default=True)

    class Meta:
        verbose_name = _("برند")
        verbose_name_plural = _("برندها")
        ordering = ("name",)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)


class Category(TimeStampedModel):
    """Product category with optional single-level parent for a tree."""

    name = models.CharField(_("نام دسته"), max_length=120)
    slug = models.SlugField(_("اسلاگ"), max_length=140, unique=True, allow_unicode=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True,
        verbose_name=_("دسته والد"),
    )
    icon = models.CharField(_("آیکون"), max_length=40, blank=True, help_text=_("کلید آیکون فرانت"))
    image = models.ImageField(_("تصویر"), upload_to="categories/", blank=True, null=True)
    is_active = models.BooleanField(_("فعال"), default=True)
    order = models.PositiveSmallIntegerField(_("ترتیب"), default=0)

    class Meta:
        verbose_name = _("دسته‌بندی")
        verbose_name_plural = _("دسته‌بندی‌ها")
        ordering = ("order", "name")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)


class CarBrand(TimeStampedModel):
    """A car maker (Iran Khodro, Saipa, Toyota, ...)."""

    name = models.CharField(_("خودروساز"), max_length=100, unique=True)

    class Meta:
        verbose_name = _("برند خودرو")
        verbose_name_plural = _("برندهای خودرو")
        ordering = ("name",)

    def __str__(self):
        return self.name


class CarModel(TimeStampedModel):
    """A specific car a part may fit (Pride, Peugeot 206, ...)."""

    brand = models.ForeignKey(CarBrand, on_delete=models.CASCADE, related_name="models", verbose_name=_("خودروساز"))
    name = models.CharField(_("مدل خودرو"), max_length=100)
    year_from = models.PositiveSmallIntegerField(_("از سال"), null=True, blank=True)
    year_to = models.PositiveSmallIntegerField(_("تا سال"), null=True, blank=True)

    class Meta:
        verbose_name = _("مدل خودرو")
        verbose_name_plural = _("مدل‌های خودرو")
        ordering = ("brand__name", "name")
        unique_together = ("brand", "name")

    def __str__(self):
        return f"{self.brand.name} {self.name}"


class Color(TimeStampedModel):
    name = models.CharField(_("رنگ"), max_length=50, unique=True)
    hex_code = models.CharField(_("کد رنگ"), max_length=7, blank=True, help_text="#RRGGBB")

    class Meta:
        verbose_name = _("رنگ")
        verbose_name_plural = _("رنگ‌ها")
        ordering = ("name",)

    def __str__(self):
        return self.name


class Size(TimeStampedModel):
    name = models.CharField(_("سایز"), max_length=50, unique=True)

    class Meta:
        verbose_name = _("سایز")
        verbose_name_plural = _("سایزها")
        ordering = ("name",)

    def __str__(self):
        return self.name


class AttributeName(TimeStampedModel):
    """A reusable spec key the supplier defines once (e.g. material, country of origin).

    `is_filterable` exposes the attribute as a facet in the shop sidebar.
    """

    name = models.CharField(_("نام ویژگی"), max_length=100, unique=True)
    unit = models.CharField(_("واحد"), max_length=30, blank=True)
    is_filterable = models.BooleanField(_("قابل فیلتر"), default=False)

    class Meta:
        verbose_name = _("عنوان ویژگی")
        verbose_name_plural = _("عناوین ویژگی")
        ordering = ("name",)

    def __str__(self):
        return self.name


class Product(SeoModel, TimeStampedModel):
    """A sellable part. Wholesale-first: price is the wholesale unit price and
    orders enforce a minimum order quantity (MOQ)."""

    class Unit(models.TextChoices):
        PIECE = "piece", _("عدد")
        LITER = "liter", _("لیتر")
        SET = "set", _("ست")
        METER = "meter", _("متر")

    name = models.CharField(_("نام محصول"), max_length=200)
    slug = models.SlugField(_("اسلاگ"), max_length=220, unique=True, allow_unicode=True)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="products", verbose_name=_("برند"))
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products", verbose_name=_("دسته‌بندی")
    )
    sku = models.CharField(_("شماره فنی (SKU)"), max_length=60, unique=True)
    # The supplier who owns/stocks this product. Each supplier manages only their
    # own products in the panel; the site owner (admin) sees everything.
    supplier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="supplied_products",
        verbose_name=_("تامین‌کننده"),
        null=True,
        blank=True,
    )

    short_description = models.CharField(_("توضیح کوتاه"), max_length=300, blank=True)
    description = models.TextField(_("توضیحات کامل"), blank=True)

    price = models.PositiveBigIntegerField(_("قیمت عمده (تومان)"))
    compare_at_price = models.PositiveBigIntegerField(_("قیمت قبل تخفیف"), null=True, blank=True)
    stock = models.PositiveIntegerField(_("موجودی"), default=0)
    min_order_qty = models.PositiveIntegerField(_("حداقل سفارش عمده"), default=1)
    unit = models.CharField(_("واحد"), max_length=10, choices=Unit.choices, default=Unit.PIECE)
    # Wholesale buyers order by the carton, so this drives both the product page
    # spec table and a shop-side filter ("cartons of 24", "cartons of 30", ...).
    carton_qty = models.PositiveIntegerField(
        _("تعداد در کارتن"),
        null=True,
        blank=True,
        help_text=_("چند عدد در هر کارتن بسته‌بندی می‌شود."),
    )

    # Facet relations.
    colors = models.ManyToManyField(Color, blank=True, related_name="products", verbose_name=_("رنگ‌ها"))
    sizes = models.ManyToManyField(Size, blank=True, related_name="products", verbose_name=_("سایزها"))
    compatible_cars = models.ManyToManyField(
        CarModel, blank=True, related_name="products", verbose_name=_("مناسب برای خودرو")
    )

    # Authenticity & warranty shown on the product page; editable from both
    # the Django admin and the supplier panel.
    authenticity = models.CharField(
        _("وضعیت اصالت"),
        max_length=100,
        blank=True,
        default="اصل شرکتی",
        help_text=_("مثلا: اصل شرکتی، اورجینال وارداتی"),
    )
    warranty_text = models.CharField(
        _("گارانتی"),
        max_length=150,
        blank=True,
        help_text=_("مثلا: ۱۸ ماه گارانتی شرکتی"),
    )

    is_active = models.BooleanField(_("منتشر شده"), default=True, db_index=True)
    is_featured = models.BooleanField(_("محصول ویژه"), default=False)

    # A sibling switcher for the "same part, different build" case (e.g. a
    # bumper sold with either a metal or a polymer bracket): each variant is its
    # own Product row (own SKU, price, stock), grouped here so the product
    # page can offer them as clickable chips instead of forcing a new search.
    # Blank = no siblings; the product page shows nothing extra.
    variant_group = models.CharField(
        _("گروه گزینه‌های دیگر"),
        max_length=220,
        blank=True,
        db_index=True,
        help_text=_("محصولاتی با همین مقدار، به‌عنوان «گزینه‌های دیگر» این کالا نمایش داده می‌شوند."),
    )
    variant_label = models.CharField(
        _("برچسب این گزینه"),
        max_length=60,
        blank=True,
        help_text=_("مثلا: دیاق فلزی — روی دکمه انتخاب گزینه‌ها نمایش داده می‌شود."),
    )

    # Denormalized aggregates for cheap listing queries.
    rating_avg = models.DecimalField(_("میانگین امتیاز"), max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField(_("تعداد امتیاز"), default=0)
    sold_count = models.PositiveIntegerField(_("تعداد فروش"), default=0)

    class Meta:
        verbose_name = _("محصول")
        verbose_name_plural = _("محصولات")
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["is_active", "-created_at"]),
            models.Index(fields=["price"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def discount_percent(self):
        if self.compare_at_price and self.compare_at_price > self.price:
            return round((1 - self.price / self.compare_at_price) * 100)
        return 0

    def price_for(self, qty: int) -> int:
        """Effective wholesale unit price for a quantity.

        Tiers (tiered wholesale pricing) give a cheaper unit price at higher volumes;
        the best tier whose min_qty is satisfied wins, else the base price.
        """
        best = self.price
        for tier in self.tiers.all():
            if qty >= tier.min_qty and tier.price < best:
                best = tier.price
        return best

    def refresh_rating(self):
        """Recompute cached rating aggregates from approved reviews."""
        from django.db.models import Avg, Count

        agg = self.reviews.filter(is_approved=True).aggregate(avg=Avg("rating"), count=Count("id"))
        self.rating_avg = round(agg["avg"] or 0, 2)
        self.rating_count = agg["count"] or 0
        self.save(update_fields=["rating_avg", "rating_count"])


class PriceTier(TimeStampedModel):
    """Volume-based wholesale price step (e.g. from 50 pcs -> cheaper unit)."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="tiers", verbose_name=_("محصول"))
    min_qty = models.PositiveIntegerField(_("از تعداد"))
    price = models.PositiveBigIntegerField(_("قیمت واحد (تومان)"))

    class Meta:
        verbose_name = _("پله قیمت عمده")
        verbose_name_plural = _("قیمت پلکانی")
        unique_together = ("product", "min_qty")
        ordering = ("min_qty",)

    def __str__(self):
        return f"{self.product.name}: از {self.min_qty} → {self.price:,}"


class ProductImage(TimeStampedModel):
    """A gallery image; the first (lowest `order`) is the primary thumbnail."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images", verbose_name=_("محصول"))
    image = models.ImageField(_("تصویر"), upload_to="products/")
    alt = models.CharField(_("متن جایگزین"), max_length=150, blank=True)
    order = models.PositiveSmallIntegerField(_("ترتیب"), default=0)
    # Tags this photo as belonging to one of the product's colours (from the
    # `colors` M2M on Product), so clicking a colour swatch on the product
    # page can switch the gallery to matching photos. Blank means "shared" —
    # shown regardless of which colour is selected.
    color = models.ForeignKey(
        Color,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="images",
        verbose_name=_("رنگ مرتبط"),
        help_text=_("خالی = برای همه رنگ‌ها نمایش داده می‌شود."),
    )

    class Meta:
        verbose_name = _("تصویر محصول")
        verbose_name_plural = _("گالری تصاویر")
        ordering = ("order", "id")

    def __str__(self):
        return f"{self.product.name} #{self.order}"


class ProductAttribute(TimeStampedModel):
    """A single spec value for a product (EAV row), editable from the admin."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="attributes", verbose_name=_("محصول"))
    name = models.ForeignKey(AttributeName, on_delete=models.PROTECT, related_name="values", verbose_name=_("ویژگی"))
    value = models.CharField(_("مقدار"), max_length=200)

    class Meta:
        verbose_name = _("ویژگی محصول")
        verbose_name_plural = _("ویژگی‌های محصول")
        unique_together = ("product", "name")

    def __str__(self):
        return f"{self.name}: {self.value}"


class Review(TimeStampedModel):
    """A buyer's rating + comment. Hidden until an admin approves it."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews", verbose_name=_("محصول"))
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name=_("کاربر"),
    )
    rating = models.PositiveSmallIntegerField(_("امتیاز"), validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(_("عنوان"), max_length=150, blank=True)
    body = models.TextField(_("متن نظر"))
    is_approved = models.BooleanField(_("تایید شده"), default=False, db_index=True)

    class Meta:
        verbose_name = _("نظر")
        verbose_name_plural = _("نظرات")
        unique_together = ("product", "user")  # one review per user per product

    def __str__(self):
        return f"{self.product.name} — {self.rating}★"


class RarePartRequest(TimeStampedModel):
    """A buyer's request for a hard-to-find part.

    The supplier reviews these in the panel, hunts the part down and flips the
    status; moving to FOUND notifies the buyer by SMS automatically.
    """

    class Status(models.TextChoices):
        NEW = "new", _("جدید")
        SEARCHING = "searching", _("در حال پیگیری")
        FOUND = "found", _("پیدا شد")
        UNAVAILABLE = "unavailable", _("موجود نیست")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rare_requests",
        verbose_name=_("کاربر"),
    )
    part_name = models.CharField(_("نام قطعه"), max_length=200)
    quantity = models.PositiveIntegerField(_("تعداد موردنیاز"), default=1)
    car_name = models.CharField(_("نام خودرو"), max_length=100)
    car_model = models.CharField(_("مدل خودرو"), max_length=100)
    brand = models.CharField(_("برند موردنیاز"), max_length=100)
    image = models.ImageField(_("تصویر قطعه (اختیاری)"), upload_to="rare-parts/", blank=True, null=True)
    note = models.TextField(_("توضیحات"), blank=True)

    status = models.CharField(_("وضعیت"), max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    admin_note = models.CharField(_("پاسخ تامین‌کننده"), max_length=300, blank=True)

    class Meta:
        verbose_name = _("درخواست قطعه نایاب")
        verbose_name_plural = _("درخواست‌های قطعه نایاب")
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.part_name} — {self.car_name} {self.car_model}"


class Favorite(TimeStampedModel):
    """A product a user has saved to their wishlist."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites",
        verbose_name=_("کاربر"),
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="favorited_by", verbose_name=_("محصول"))

    class Meta:
        verbose_name = _("علاقه‌مندی")
        verbose_name_plural = _("علاقه‌مندی‌ها")
        unique_together = ("user", "product")

    def __str__(self):
        return f"{self.user} ♥ {self.product}"
