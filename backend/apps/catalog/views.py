"""Catalog API: public browsing + authenticated reviews/favorites.

Reads are open to everyone (the storefront is public); writing reviews or
managing favorites requires login.
"""

from django.conf import settings
from django.db.models import Count, Prefetch, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import ProductFilter
from .models import (
    Brand,
    CarModel,
    Category,
    Color,
    Favorite,
    Product,
    Review,
    Size,
)
from .serializers import (
    BrandSerializer,
    CarModelSerializer,
    CategorySerializer,
    ColorSerializer,
    FavoriteSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    RarePartRequestSerializer,
    ReviewSerializer,
    SizeSerializer,
)


class ReadOnlyPublic(viewsets.ReadOnlyModelViewSet):
    """Small helper: readable by anyone, no auth."""

    permission_classes = [permissions.AllowAny]


class BrandViewSet(ReadOnlyPublic):
    queryset = Brand.objects.filter(is_active=True)
    serializer_class = BrandSerializer
    pagination_class = None


class CategoryViewSet(ReadOnlyPublic):
    serializer_class = CategorySerializer
    pagination_class = None
    lookup_field = "slug"

    def get_queryset(self):
        # Count only what a shopper can actually open. Counting every row —
        # drafts included — is why the menu advertised "Bumper (182)" while the shop
        # grid, which filters on is_active, could show four products.
        return Category.objects.filter(is_active=True).annotate(
            product_count=Count("products", filter=Q(products__is_active=True))
        )


class ColorViewSet(ReadOnlyPublic):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer
    pagination_class = None


class SizeViewSet(ReadOnlyPublic):
    queryset = Size.objects.all()
    serializer_class = SizeSerializer
    pagination_class = None


class CarModelViewSet(ReadOnlyPublic):
    queryset = CarModel.objects.select_related("brand")
    serializer_class = CarModelSerializer
    pagination_class = None


class ProductViewSet(ReadOnlyPublic):
    """Product listing with dynamic filters + sorting, and a rich detail view."""

    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ProductFilter
    # Whitelist of sortable fields; the client passes ?ordering=-price etc.
    ordering_fields = ["price", "created_at", "rating_avg", "sold_count"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True).select_related("brand", "category")
        if self.action == "retrieve":
            # Detail view needs the whole gallery + specs; prefetch to avoid N+1.
            return qs.prefetch_related(
                "images",
                "colors",
                "sizes",
                "compatible_cars__brand",
                Prefetch("attributes"),
            )
        return qs.prefetch_related("images")

    def get_serializer_class(self):
        return ProductDetailSerializer if self.action == "retrieve" else ProductListSerializer

    @action(detail=True, methods=["get"], url_path="reviews", permission_classes=[permissions.AllowAny])
    def reviews(self, request, slug=None):
        """Approved reviews for a product."""
        product = self.get_object()
        qs = product.reviews.filter(is_approved=True).select_related("user")
        return Response(ReviewSerializer(qs, many=True, context={"request": request}).data)

    @action(detail=True, methods=["get"], url_path="related", permission_classes=[permissions.AllowAny])
    def related(self, request, slug=None):
        """Genuinely related parts, ranked by what actually makes two parts
        alternatives for a mechanic:

          * fits the same car          (strongest — a Pride part suits a Pride)
          * same category              (a MAP sensor next to other MAP sensors)
          * similar price bracket      (keeps wholesale tiers comparable)
          * in stock                   (a buyable suggestion beats a dead one)

        Scored in SQL in one query rather than by fetching and sorting in Python,
        so it stays cheap as the catalogue grows.
        """
        from django.db.models import Case, Count, F, IntegerField, Q, When

        product = self.get_object()
        car_ids = list(product.compatible_cars.values_list("id", flat=True))

        qs = (
            Product.objects.filter(is_active=True, stock__gt=0, price__gt=0)
            .exclude(pk=product.pk)
            .select_related("brand", "category")
            .prefetch_related("images")
        )
        # Related must be BUYABLE alternatives — never suggest out-of-stock or
        # price-less parts, especially when the main product is itself
        # unavailable (that would send the shopper into another dead end).
        # Only consider products sharing at least one real signal, otherwise a
        # "related" strip is just random stock.
        relevance = Q(category_id=product.category_id)
        if car_ids:
            relevance |= Q(compatible_cars__in=car_ids)
        qs = qs.filter(relevance).distinct()

        shared_cars = (
            Count("compatible_cars", filter=Q(compatible_cars__in=car_ids), distinct=True)
            if car_ids
            else Count("pk", filter=Q(pk__isnull=True))
        )

        qs = (
            qs.annotate(
                shared_cars=shared_cars,
                same_category=Case(
                    When(category_id=product.category_id, then=3),
                    default=0,
                    output_field=IntegerField(),
                ),
                buyable=Case(When(stock__gt=0, then=1), default=0, output_field=IntegerField()),
            )
            .annotate(score=F("same_category") + F("shared_cars") * 2 + F("buyable"))
            .order_by("-score", "-sold_count", "-rating_avg")[:12]
        )

        data = ProductListSerializer(qs, many=True, context={"request": request}).data
        return Response(data)


class SiteStatsView(APIView):
    """Real headline numbers for the home page (cached for 10 minutes).

    Replaces the hard-coded "12K part codes" style figures with live counts.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from django.core.cache import cache

        stats = cache.get("site_stats")
        if stats is None:
            from apps.accounts.models import User

            stats = {
                "products": Product.objects.filter(is_active=True).count(),
                "brands": Brand.objects.filter(is_active=True).count(),
                "categories": Category.objects.filter(is_active=True).count(),
                "shops": User.objects.filter(role=User.Role.SHOPKEEPER, is_approved=True).count(),
            }
            cache.set("site_stats", stats, 600)
        return Response(stats)


class CartonOptionsView(APIView):
    """Distinct carton sizes in the catalog, so the shop filter lists only the
    pack sizes that actually exist instead of a hard-coded guess."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        values = (
            Product.objects.filter(is_active=True, carton_qty__gt=0)
            .values_list("carton_qty", flat=True)
            .order_by("carton_qty")
            .distinct()
        )
        return Response(list(values))


class SearchSuggestView(APIView):
    """Live autocomplete for the header search box.

    GET ?q=... -> {products, brands, categories} — fuzzy (trigram) so typos
    still find the part, plus name/SKU/brand substring matches.
    """

    permission_classes = [permissions.AllowAny]

    # Persian/Arabic digits -> Latin, so a buyer typing either digit set finds
    # the same technical code (SKUs are stored with Persian digits).
    _DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

    def get(self, request):
        q = str(request.query_params.get("q", "")).strip()
        if len(q) < 2:
            return Response({"products": [], "brands": [], "categories": []})
        q_fa = q.translate(self._DIGITS)

        from django.contrib.postgres.search import TrigramWordSimilarity
        from django.db.models import Q

        # Word-level similarity survives typos inside long product names
        # (e.g. «فبلتر» still matches «فیلتر روغن BOSCH»).
        products = (
            Product.objects.filter(is_active=True)
            .annotate(sim=TrigramWordSimilarity(q, "name"))
            .filter(
                Q(name__icontains=q)
                | Q(sku__icontains=q)
                | Q(sku__icontains=q_fa)
                | Q(brand__name__icontains=q)
                | Q(sim__gt=0.3)
            )
            .select_related("brand")
            .prefetch_related("images")
            .order_by("-sim", "-sold_count")[:6]
        )

        def thumb(p):
            first = p.images.first()
            if not first:
                return None
            url = first.image.url
            return request.build_absolute_uri(url) if request else url

        return Response(
            {
                "products": [
                    {
                        "name": p.name,
                        "slug": p.slug,
                        "sku": p.sku,
                        "brand": p.brand.name,
                        "price": p.price,
                        "in_stock": p.stock > 0,
                        "thumbnail": thumb(p),
                    }
                    for p in products
                ],
                "brands": list(Brand.objects.filter(is_active=True, name__icontains=q).values("id", "name")[:3]),
                "categories": list(Category.objects.filter(is_active=True, name__icontains=q).values("id", "name")[:3]),
            }
        )


class ReviewCreateViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Authenticated users submit a review (held for moderation)."""

    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Review.objects.all()


class RarePartRequestViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """Buyer submits a rare-part request (multipart for the optional photo)
    and tracks their own requests."""

    serializer_class = RarePartRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from .models import RarePartRequest

        return RarePartRequest.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        # A supplier answers these requests; letting them file one would mean
        # broadcasting their own request back to themselves.
        from apps.accounts.models import User

        if request.user.is_superuser or request.user.role in (User.Role.SUPPLIER, User.Role.ADMIN):
            return Response(
                {"detail": "ثبت درخواست قطعه نایاب فقط برای کاربران خریدار امکان‌پذیر است."},
                status=403,
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        from django.db import transaction

        obj = serializer.save(user=self.request.user)

        # Broadcast to every supplier — after commit so the worker can never
        # read a half-written row.
        def _broadcast():
            try:
                from apps.suppliers.tasks import notify_suppliers_rare_part

                notify_suppliers_rare_part.delay(obj.pk)
            except Exception:  # never let a messaging hiccup fail the request
                pass

        transaction.on_commit(_broadcast)


class ManageRarePartViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Supplier reviews every request, updates status/reply; flipping the
    status to FOUND texts the buyer automatically."""

    serializer_class = RarePartRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        from apps.accounts.permissions import IsSupplierOrAdmin

        return [permissions.IsAuthenticated(), IsSupplierOrAdmin()]

    def get_queryset(self):
        from .models import RarePartRequest

        qs = RarePartRequest.objects.select_related("user")
        state = self.request.query_params.get("status")
        if state:
            qs = qs.filter(status=state)
        return qs

    def get_serializer_class(self):
        base = self.serializer_class

        class Writable(base):  # type: ignore[misc, valid-type]
            class Meta(base.Meta):  # type: ignore[misc]
                read_only_fields = ("created_at",)  # supplier may set status/reply

        return Writable

    def perform_update(self, serializer):
        from .models import RarePartRequest

        old_status = serializer.instance.status
        instance = serializer.save()
        if old_status != RarePartRequest.Status.FOUND and instance.status == RarePartRequest.Status.FOUND:
            from apps.notifications.tasks import send_sms

            send_sms.delay(
                instance.user.phone,
                f"{settings.SITE_SHORT_NAME}\nقطعه درخواستی شما «{instance.part_name}» پیدا شد! "
                + (instance.admin_note or "برای هماهنگی با ما تماس بگیرید."),
            )


class FavoriteViewSet(viewsets.ModelViewSet):
    """The signed-in user's wishlist."""

    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return (
            Favorite.objects.filter(user=self.request.user)
            .select_related("product", "product__brand")
            .prefetch_related("product__images")
        )
