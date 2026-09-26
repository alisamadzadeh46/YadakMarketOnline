"""Dynamic shop filters.

Exposes the facets the user asked for: brand, car-compatibility, color, size,
in-stock, and a price range — all combinable, plus free-text search.
"""

import django_filters as df

from .models import Product


class ProductFilter(df.FilterSet):
    # Multi-select facets accept comma-separated ids, e.g. ?brand=1,2
    brand = df.BaseInFilter(field_name="brand_id")
    category = df.BaseInFilter(field_name="category_id")
    color = df.BaseInFilter(field_name="colors__id", distinct=True)
    size = df.BaseInFilter(field_name="sizes__id", distinct=True)
    car = df.BaseInFilter(field_name="compatible_cars__id", distinct=True)

    # Wholesale buyers shop by pack size, so carton count is a first-class facet.
    carton = df.BaseInFilter(field_name="carton_qty")
    min_carton = df.NumberFilter(field_name="carton_qty", lookup_expr="gte")
    max_carton = df.NumberFilter(field_name="carton_qty", lookup_expr="lte")

    min_price = df.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = df.NumberFilter(field_name="price", lookup_expr="lte")
    min_rating = df.NumberFilter(field_name="rating_avg", lookup_expr="gte")

    in_stock = df.BooleanFilter(method="filter_in_stock")
    featured = df.BooleanFilter(field_name="is_featured")
    search = df.CharFilter(method="filter_search")

    class Meta:
        model = Product
        fields = ["brand", "category", "color", "size", "car"]

    def filter_in_stock(self, queryset, name, value):
        # True -> only items with stock; False -> only out-of-stock.
        return queryset.filter(stock__gt=0) if value else queryset.filter(stock=0)

    def filter_search(self, queryset, name, value):
        """Fuzzy, typo-tolerant search: exact/substring matches first, then
        trigram similarity so «فیلتر روغن» still matches «فبلتر روغن»."""
        from django.contrib.postgres.search import TrigramWordSimilarity
        from django.db.models import Q

        value = value.strip()
        base = Q(name__icontains=value) | Q(sku__icontains=value) | Q(brand__name__icontains=value)
        qs = queryset.annotate(sim=TrigramWordSimilarity(value, "name")).filter(base | Q(sim__gt=0.3))
        return qs.order_by("-sim", "-created_at").distinct()
