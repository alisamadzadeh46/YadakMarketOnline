"""Catalog serializers for list, detail, reviews and favorites."""

from django.conf import settings
from rest_framework import serializers

from .models import (
    AttributeName,
    Brand,
    CarModel,
    Category,
    Color,
    Favorite,
    PriceTier,
    Product,
    ProductAttribute,
    ProductImage,
    RarePartRequest,
    Review,
    Size,
)


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ("id", "name", "name_en", "slug", "logo")


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "parent", "icon", "image", "order", "product_count")


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ("id", "name", "hex_code")


class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ("id", "name")


class CarModelSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="brand.name", read_only=True)

    class Meta:
        model = CarModel
        fields = ("id", "name", "brand", "brand_name", "year_from", "year_to")


class PriceTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceTier
        fields = ("min_qty", "price")


class ProductImageSerializer(serializers.ModelSerializer):
    # Bare id (not the nested Color object): the product page already has the
    # full colour list from `Product.colors` and only needs to match this
    # photo against one of those by id when the shopper picks a swatch.
    color = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ProductImage
        fields = ("id", "image", "alt", "order", "color")


class ProductAttributeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="name.name", read_only=True)
    unit = serializers.CharField(source="name.unit", read_only=True)

    class Meta:
        model = ProductAttribute
        fields = ("name", "value", "unit")


class ProductListSerializer(serializers.ModelSerializer):
    """Lean payload for grid cards."""

    brand = serializers.CharField(source="brand.name", read_only=True)
    thumbnail = serializers.SerializerMethodField()
    discount_percent = serializers.IntegerField(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    is_new = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "brand",
            "sku",
            "price",
            "compare_at_price",
            "discount_percent",
            "unit",
            "min_order_qty",
            "carton_qty",
            "rating_avg",
            "rating_count",
            "sold_count",
            "in_stock",
            "thumbnail",
            "is_new",
        )

    def get_is_new(self, obj):
        from datetime import timedelta

        from django.utils import timezone

        return obj.created_at >= timezone.now() - timedelta(days=30)

    def get_thumbnail(self, obj):
        first = obj.images.first()
        if not first:
            return None
        request = self.context.get("request")
        url = first.image.url
        return request.build_absolute_uri(url) if request else url


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full payload for the product page: gallery, specs, facets."""

    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    attributes = ProductAttributeSerializer(many=True, read_only=True)
    colors = ColorSerializer(many=True, read_only=True)
    sizes = SizeSerializer(many=True, read_only=True)
    compatible_cars = CarModelSerializer(many=True, read_only=True)
    tiers = PriceTierSerializer(many=True, read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    seller = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "brand",
            "category",
            "sku",
            "short_description",
            "description",
            "price",
            "compare_at_price",
            "discount_percent",
            "stock",
            "in_stock",
            "min_order_qty",
            "carton_qty",
            "unit",
            "colors",
            "sizes",
            "compatible_cars",
            "attributes",
            "images",
            "tiers",
            "rating_avg",
            "rating_count",
            "sold_count",
            "is_featured",
            "authenticity",
            "warranty_text",
            "seller",
            "variant_label",
            "variants",
            "meta_title",
            "meta_description",
        )

    def get_variants(self, obj):
        """Sibling products of the same part (e.g. a metal vs a polymer
        bracket) — a different SKU/price each, grouped by variant_group.
        Ordered by price so cheaper options sort first, same as a shop grid."""
        if not obj.variant_group:
            return []
        siblings = (
            Product.objects.filter(variant_group=obj.variant_group, is_active=True)
            .only("id", "slug", "name", "variant_label", "price")
            .order_by("price")
        )
        return [
            {
                "id": s.id,
                "slug": s.slug,
                "name": s.name,
                "label": s.variant_label or s.name,
                "price": s.price,
                "is_current": s.id == obj.id,
            }
            for s in siblings
        ]

    def get_seller(self, obj):
        """Real seller stats: active product count and the average rating across
        that seller's rated products. Falls back to the store name when a product
        predates the supplier field."""
        from django.db.models import Avg

        supplier = obj.supplier
        if not supplier:
            return {"name": settings.DEFAULT_SELLER_NAME, "products": None, "rating": None}
        qs = Product.objects.filter(supplier=supplier, is_active=True)
        agg = qs.filter(rating_count__gt=0).aggregate(r=Avg("rating_avg"))
        rating = round(float(agg["r"]), 1) if agg["r"] else None
        name = supplier.full_name or "فروشگاه لوازم یدکی"
        return {
            "name": name,
            "products": qs.count(),
            "rating": rating,
        }


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = Review
        fields = ("id", "product", "user_name", "rating", "title", "body", "created_at", "is_approved")
        read_only_fields = ("is_approved", "created_at")

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class FavoriteSerializer(serializers.ModelSerializer):
    product_detail = ProductListSerializer(source="product", read_only=True)

    class Meta:
        model = Favorite
        fields = ("id", "product", "product_detail", "created_at")
        read_only_fields = ("created_at",)

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class RarePartRequestSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_phone = serializers.CharField(source="user.phone", read_only=True)

    class Meta:
        model = RarePartRequest
        fields = (
            "id",
            "part_name",
            "quantity",
            "car_name",
            "car_model",
            "brand",
            "image",
            "note",
            "status",
            "status_display",
            "admin_note",
            "user_name",
            "user_phone",
            "created_at",
        )
        read_only_fields = ("status", "admin_note", "created_at")

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class AttributeNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeName
        fields = ("id", "name", "unit", "is_filterable")
