"""Supplier-facing write API for the catalog (products, categories, brands,
gallery images). All endpoints require the supplier/admin role.
"""

from django.db import transaction
from django.db.models import ProtectedError, Q
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsSiteAdmin, IsSupplierOrAdmin, SupplierCreateAdminChange
from apps.core.images import normalize_image
from apps.core.mixins import ProtectedDeleteMixin
from apps.orders.models import OrderItem

from .models import Brand, Category, Color, Product, ProductAttribute, ProductImage
from .serializers import ProductDetailSerializer


class ProductManageSerializer(ProductDetailSerializer):
    """What the panel needs to *edit* a product, on top of the public payload.

    ProductDetailSerializer is the storefront shape and deliberately omits
    back-office fields. Reading the manage list through it meant `is_active`
    and `focus_keyword` never reached the form: every product showed as
    "draft" however often it was published, and the SEO keyword looked like
    it refused to save because it was never loaded back.
    """

    class Meta(ProductDetailSerializer.Meta):
        fields = tuple(ProductDetailSerializer.Meta.fields) + (
            "is_active",
            "focus_keyword",
            "canonical_url",
            "seo_score",
            "supplier",
        )


class ManagePermissions(permissions.IsAuthenticated):
    pass


class ProductWriteSerializer(serializers.ModelSerializer):
    """Writable product payload; m2m facets accept id lists."""

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
            "stock",
            "min_order_qty",
            "carton_qty",
            "unit",
            "colors",
            "sizes",
            "compatible_cars",
            "is_active",
            "is_featured",
            "supplier",
            "authenticity",
            "warranty_text",
            "variant_group",
            "variant_label",
            "meta_title",
            "meta_description",
            "focus_keyword",
        )
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}


class AttributeWriteSerializer(serializers.ModelSerializer):
    name_text = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = ProductAttribute
        fields = ("id", "name", "name_text", "value")
        extra_kwargs = {"name": {"required": False}}


class ManageProductViewSet(viewsets.ModelViewSet):
    """Full CRUD + gallery management for the supplier panel."""

    queryset = Product.objects.all().select_related("brand", "category").prefetch_related("images")
    permission_classes = [permissions.IsAuthenticated, IsSupplierOrAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return ProductManageSerializer
        return ProductWriteSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # A supplier only manages their own products; the site owner (admin/
        # superuser) sees and manages everything.
        user = self.request.user
        if not (user.is_superuser or user.role == "admin"):
            qs = qs.filter(supplier=user)
        q = self.request.query_params.get("search")
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    def _is_owner(self):
        u = self.request.user
        return bool(u.is_superuser or u.role == "admin")

    def perform_create(self, serializer):
        """Assign ownership.

        The site owner may file a product under any supplier (that's the point
        of the "supplier" selector). A plain supplier always owns what they
        create — the field is ignored for them, so a crafted payload cannot
        push stock into someone else's panel.
        """
        user = self.request.user
        chosen = serializer.validated_data.get("supplier") if self._is_owner() else None
        serializer.save(supplier=chosen or user)

    def perform_update(self, serializer):
        if self._is_owner():
            serializer.save()
        else:
            # Keep the original owner no matter what the payload says.
            serializer.save(supplier=serializer.instance.supplier)

    def destroy(self, request, *args, **kwargs):
        """Delete a product, or explain precisely why it can't be deleted.

        ``OrderItem.product`` is PROTECT on purpose: a past invoice must keep
        pointing at the real product. So deleting anything that has ever been
        ordered raised ProtectedError -> HTTP 500, which the panel swallowed —
        the button simply appeared to do nothing. Answer with a 409 the UI can
        act on, and tell the supplier how many orders are in the way.
        """
        product = self.get_object()
        try:
            with transaction.atomic():
                product.delete()
        except ProtectedError:
            used_in = OrderItem.objects.filter(product=product).values("order").distinct().count()
            return Response(
                {
                    "detail": (
                        f"«{product.name}» در {used_in} سفارش ثبت شده و حذف کامل آن "
                        "سابقه فاکتورها را خراب می‌کند. می‌توانید به‌جای حذف، "
                        "محصول را غیرفعال کنید تا از فروشگاه برداشته شود."
                    ),
                    "code": "protected_by_orders",
                    "orders": used_in,
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="images")
    def upload_image(self, request, pk=None):
        """Attach one gallery image (multipart: image, alt?, order?, color?)."""
        product = self.get_object()
        image = request.FILES.get("image")
        if not image:
            return Response({"detail": "فایل تصویر ارسال نشده است."}, status=400)
        # Camera-roll uploads arrive at 4000px / several MB. Cap and re-encode
        # here so the gallery, the shop grid and the feeds all get a sane file.
        image = normalize_image(image, square=True)
        # Optional: tag this photo as one specific colour of the product, so
        # the product page can swap the gallery when that swatch is picked.
        # Must be one of the product's OWN colours — same rule the cart API
        # enforces — or a stray id could tag a photo with an unrelated colour.
        color_id = request.data.get("color")
        color_id = int(color_id) if color_id not in (None, "", "null") else None
        if color_id and not product.colors.filter(id=color_id).exists():
            return Response({"detail": "این رنگ برای این محصول تعریف نشده است."}, status=400)
        img = ProductImage.objects.create(
            product=product,
            image=image,
            alt=request.data.get("alt", product.name),
            order=int(request.data.get("order", product.images.count())),
            color_id=color_id,
        )
        return Response(
            {
                "id": img.id,
                "image": request.build_absolute_uri(img.image.url),
                "order": img.order,
                "color": img.color_id,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["delete", "patch"], url_path=r"images/(?P<image_id>\d+)")
    def edit_image(self, request, pk=None, image_id=None):
        """DELETE removes the photo; PATCH re-tags which colour it belongs to.

        Re-tagging matters because a supplier uploads the gallery first and
        only then works out which shot is the black one — without this they
        would have to delete and re-upload to correct a mistake.
        """
        product = self.get_object()
        if request.method == "DELETE":
            product.images.filter(id=image_id).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        img = product.images.filter(id=image_id).first()
        if not img:
            return Response({"detail": "تصویر یافت نشد."}, status=404)
        raw = request.data.get("color")
        color_id = int(raw) if raw not in (None, "", "null") else None
        if color_id and not product.colors.filter(id=color_id).exists():
            return Response({"detail": "این رنگ برای این محصول تعریف نشده است."}, status=400)
        img.color_id = color_id
        img.save(update_fields=["color"])
        return Response({"id": img.id, "color": img.color_id})

    @action(detail=True, methods=["post"], url_path="tiers")
    def set_tiers(self, request, pk=None):
        """Replace the product's volume price tiers.

        Body: {"tiers": [{"min_qty": 50, "price": 1500000}, ...]}
        """
        from .models import PriceTier

        product = self.get_object()
        product.tiers.all().delete()
        saved = 0
        for row in request.data.get("tiers", []):
            try:
                min_qty, price = int(row.get("min_qty")), int(row.get("price"))
            except (TypeError, ValueError):
                continue
            if min_qty > 0 and 0 < price < product.price:
                PriceTier.objects.update_or_create(product=product, min_qty=min_qty, defaults={"price": price})
                saved += 1
        return Response({"detail": "قیمت پلکانی ذخیره شد.", "count": saved})

    @action(detail=True, methods=["post"], url_path="attributes")
    def set_attributes(self, request, pk=None):
        """Replace the product's dynamic spec rows.

        Body: {"attributes": [{"name_text": "جنس", "value": "فلز"}, ...]}
        Attribute names are created on the fly so the supplier can invent new
        spec keys without a separate screen.
        """
        from .models import AttributeName

        product = self.get_object()
        rows = request.data.get("attributes", [])
        product.attributes.all().delete()
        for row in rows:
            name_text = (row.get("name_text") or "").strip()
            value = (row.get("value") or "").strip()
            if not name_text or not value:
                continue
            name, _ = AttributeName.objects.get_or_create(name=name_text)
            ProductAttribute.objects.update_or_create(product=product, name=name, defaults={"value": value})
        return Response({"detail": "ویژگی‌ها ذخیره شد.", "count": product.attributes.count()})


class CategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "parent", "icon", "order", "is_active")
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}


class ManageCategoryViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    protected_delete_message = "این دسته‌بندی به محصولاتی متصل است؛ ابتدا محصولات را به دسته دیگری منتقل کنید."
    queryset = Category.objects.all()
    serializer_class = CategoryWriteSerializer
    permission_classes = [IsSiteAdmin]
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        q = (self.request.query_params.get("search") or "").strip()
        if q:
            qs = qs.filter(name__icontains=q)
        return qs


class BrandWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ("id", "name", "name_en", "slug", "is_active")
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}


class ManageBrandViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    protected_delete_message = "این برند به محصولاتی متصل است؛ ابتدا برند آن محصولات را تغییر دهید."
    queryset = Brand.objects.all()
    serializer_class = BrandWriteSerializer
    permission_classes = [IsSiteAdmin]
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        q = (self.request.query_params.get("search") or "").strip()
        if q:
            # Either spelling finds the brand.
            qs = qs.filter(Q(name__icontains=q) | Q(name_en__icontains=q))
        return qs


class ColorWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ("id", "name", "hex_code")
        extra_kwargs = {"hex_code": {"required": False, "allow_blank": True}}


class ManageColorViewSet(viewsets.ModelViewSet):
    """Colours are shared across the whole catalog, so any supplier may add
    one (a new shade of bumper paint is not owned by whoever typed it first)
    — but an existing colour is reused rather than duplicated, otherwise the
    swatch list fills up with the same colour three times over."""

    queryset = Color.objects.all()
    serializer_class = ColorWriteSerializer
    permission_classes = [SupplierCreateAdminChange]
    pagination_class = None

    def create(self, request, *args, **kwargs):
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"detail": "نام رنگ لازم است."}, status=400)
        existing = Color.objects.filter(name__iexact=name).first()
        if existing:
            return Response(ColorWriteSerializer(existing).data, status=status.HTTP_200_OK)
        return super().create(request, *args, **kwargs)


class SupplierChoicesView(APIView):
    """Suppliers the site owner may file a product under.

    Owner-only: a plain supplier has no business enumerating the others, and
    the selector this feeds is only rendered for the owner anyway.
    """

    permission_classes = [permissions.IsAuthenticated, IsSupplierOrAdmin]

    def get(self, request):
        u = request.user
        if not (u.is_superuser or u.role == "admin"):
            return Response([], status=200)
        from apps.accounts.models import User

        rows = (
            User.objects.filter(role=User.Role.SUPPLIER)
            .order_by("full_name", "phone")
            .values("id", "full_name", "phone")
        )
        return Response([{"id": r["id"], "name": r["full_name"] or r["phone"]} for r in rows])
