"""Public product feed for the Iranian price-comparison engines.

Emalls (emalls.ir) crawls a paginated JSON document rather than reading meta
tags off each product page; the shape below is theirs, verbatim from their
integration guide (``?page=1&item_per_page=50``). Torob and IranMarket read the
per-product meta tags instead — see frontend/app/product/[slug]/layout.tsx —
but they accept this endpoint as the "list of all products" link too.

Security posture, deliberately narrow:
  * GET only, unauthenticated, and it returns *nothing* a visitor could not
    already read off the public shop pages — no stock counts, no supplier
    identity, no cost prices, no user data.
  * ``item_per_page`` is clamped, so nobody can ask for the whole catalogue in
    one query and turn this into a cheap DoS lever.
  * Unpublished products are excluded by the same ``is_active`` filter the
    storefront uses.
  * The nginx ``api_limit`` zone rate-limits it like every other API route.
"""

from django.conf import settings
from django.core.paginator import Paginator
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Product

MAX_PER_PAGE = 100
DEFAULT_PER_PAGE = 50


def _int(raw, default, low, high):
    """Parse a query param defensively — crawlers send junk more often than not."""
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, value))


class ProductFeedView(APIView):
    """``GET /api/catalog/feed/?page=1&item_per_page=50`` — Emalls product list."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []  # never touch session/JWT state for a public feed

    def get(self, request):
        page_num = _int(request.query_params.get("page"), 1, 1, 100_000)
        per_page = _int(request.query_params.get("item_per_page"), DEFAULT_PER_PAGE, 1, MAX_PER_PAGE)

        qs = (
            Product.objects.filter(is_active=True)
            .select_related("brand", "category")
            .prefetch_related("images", "colors")
            .order_by("-created_at", "id")
        )
        paginator = Paginator(qs, per_page)
        page = paginator.get_page(page_num)

        site = settings.FRONTEND_URL.rstrip("/")
        products = []
        for p in page.object_list:
            first_image = p.images.first()
            image_url = ""
            if first_image and first_image.image:
                image_url = first_image.image.url
                if not image_url.startswith("http"):
                    image_url = f"{site}{image_url}"
            color = p.colors.first()
            row = {
                "title": p.name,
                "id": p.sku or str(p.pk),
                "price": p.price,
                "category": p.category.name if p.category_id else "لوازم یدکی",
                "image": image_url,
                "is_available": p.stock > 0,
                "url": f"{site}/product/{p.slug}",
            }
            # old_price only means something when there really is a discount.
            if p.compare_at_price and p.compare_at_price > p.price:
                row["old_price"] = p.compare_at_price
            if color:
                row["color"] = color.name
            if p.warranty_text:
                row["guarantee"] = p.warranty_text
            if p.brand_id:
                row["brand"] = p.brand.name
            products.append(row)

        response = Response(
            {
                "success": True,
                "products": products,
                "total_items": paginator.count,
                "pages_count": paginator.num_pages,
                "item_per_page": per_page,
                "page_num": page.number,
            }
        )
        # Crawlers re-poll every few hours; let the CDN absorb the repeats.
        response["Cache-Control"] = "public, max-age=1800"
        return response

    # Emalls documents the endpoint as "GET / POST" and some of their workers
    # use POST. Safe to allow: the handler is read-only, reads its arguments
    # from the query string only, and runs with authentication disabled — so
    # there is no session or CSRF surface for a POST to abuse.
    post = get
