"""Supplier/admin catalog management.

The supplier edits products, gallery images and dynamic spec rows inline, and
moderates reviews here.
"""

from django.contrib import admin

from .models import (
    AttributeName,
    Brand,
    CarBrand,
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


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class PriceTierInline(admin.TabularInline):
    model = PriceTier
    extra = 1


class ProductAttributeInline(admin.TabularInline):
    # Lets the supplier add/edit dynamic spec rows without touching code.
    model = ProductAttribute
    extra = 1
    autocomplete_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "category", "price", "stock", "is_active", "is_featured", "rating_avg")
    list_filter = ("is_active", "is_featured", "brand", "category")
    list_editable = ("price", "stock", "is_active", "is_featured")
    search_fields = ("name", "sku")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("brand", "category")
    filter_horizontal = ("colors", "sizes", "compatible_cars")
    inlines = (ProductImageInline, ProductAttributeInline, PriceTierInline)
    fieldsets = (
        (None, {"fields": ("name", "slug", "sku", "brand", "category")}),
        ("قیمت و موجودی", {"fields": ("price", "compare_at_price", "stock", "min_order_qty", "unit")}),
        ("توضیحات", {"fields": ("short_description", "description")}),
        ("اصالت و گارانتی", {"fields": ("authenticity", "warranty_text")}),
        ("ویژگی‌ها", {"fields": ("colors", "sizes", "compatible_cars")}),
        ("گزینه‌های دیگر (مثلا دیاق فلزی/پلیمری)", {"fields": ("variant_group", "variant_label")}),
        ("نمایش", {"fields": ("is_active", "is_featured")}),
        ("سئو", {"fields": ("meta_title", "meta_description", "focus_keyword", "seo_score")}),
    )


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "order", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(CarModel)
class CarModelAdmin(admin.ModelAdmin):
    list_display = ("brand", "name", "year_from", "year_to")
    list_filter = ("brand",)
    search_fields = ("name", "brand__name")


@admin.register(AttributeName)
class AttributeNameAdmin(admin.ModelAdmin):
    list_display = ("name", "unit", "is_filterable")
    list_editable = ("is_filterable",)
    search_fields = ("name",)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "is_approved", "created_at")
    list_filter = ("is_approved", "rating")
    search_fields = ("product__name", "user__phone")
    actions = ("approve_reviews",)

    @admin.action(description="تایید نظرات انتخاب‌شده")
    def approve_reviews(self, request, queryset):
        for review in queryset:
            review.is_approved = True
            review.save()  # triggers rating refresh via signal


@admin.register(RarePartRequest)
class RarePartRequestAdmin(admin.ModelAdmin):
    list_display = ("part_name", "car_name", "car_model", "brand", "user", "status", "created_at")
    list_filter = ("status",)
    list_editable = ("status",)
    search_fields = ("part_name", "car_name", "user__phone")


admin.site.register(CarBrand)
admin.site.register(Color)
admin.site.register(Size)
admin.site.register(Favorite)
