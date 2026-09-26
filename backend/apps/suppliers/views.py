"""Supplier + shopkeeper credit panels."""

from datetime import timedelta

from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsApprovedShopkeeper, IsSiteAdmin, IsSupplierOrAdmin, is_site_admin
from apps.core.utils import jalali_month_start

from .models import CreditAccount, CreditInvoice, SupplierSettings
from .serializers import (
    CreditAccountSerializer,
    CreditInvoiceSerializer,
    SupplierSettingsSerializer,
)


def _orders_visible_to(user):
    """Every order for the site owner; a supplier's orders are those that
    contain at least one of their products."""
    from apps.orders.models import Order

    if is_site_admin(user):
        return Order.objects.all()
    return Order.objects.filter(items__product__supplier=user).distinct()


def _daily_sales(user, start):
    """``{local_date: {"total", "count"}}`` of non-canceled sales since ``start``.

    The site owner sees order totals; a supplier sees only the value of their
    own lines, so no supplier learns another supplier's revenue.
    """
    from django.db.models import Count, F, Sum
    from django.db.models.functions import TruncDate

    from apps.orders.models import Order, OrderItem

    if is_site_admin(user):
        rows = (
            Order.objects.filter(created_at__date__gte=start)
            .exclude(status=Order.Status.CANCELED)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Sum("total"), count=Count("id"))
        )
    else:
        rows = (
            OrderItem.objects.filter(product__supplier=user, order__created_at__date__gte=start)
            .exclude(order__status=Order.Status.CANCELED)
            .annotate(day=TruncDate("order__created_at"))
            .values("day")
            .annotate(total=Sum(F("quantity") * F("unit_price")), count=Count("order", distinct=True))
        )
    return {row["day"]: row for row in rows}


def _series(daily, start, days):
    """Fill the gaps of a daily map so every day of the range is present."""
    from datetime import timedelta

    series = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        row = daily.get(day)
        series.append({"date": str(day), "total": row["total"] if row else 0, "count": row["count"] if row else 0})
    return series


class SupplierDashboardView(APIView):
    """Aggregate counters for the supplier panel home, scoped like the reports:
    the site owner sees the marketplace, a supplier only their own store."""

    permission_classes = [permissions.IsAuthenticated, IsSupplierOrAdmin]

    def get(self, request):
        from datetime import timedelta

        from django.db.models import Sum
        from django.utils import timezone as tz

        from apps.accounts.models import ShopkeeperProfile, User
        from apps.catalog.models import Product
        from apps.orders.models import Order, OrderItem

        user = request.user
        is_owner = is_site_admin(user)
        products = Product.objects.all() if is_owner else Product.objects.filter(supplier=user)
        orders = _orders_visible_to(user)
        unsettled = CreditInvoice.objects.filter(is_settled=False)
        if not is_owner:
            unsettled = unsettled.filter(account__supplier=user)

        # Last-7-day sales series for the dashboard chart (paid + credit orders).
        week_start = tz.localdate() - timedelta(days=6)
        sales_week = _series(_daily_sales(user, week_start), week_start, 7)

        # Analytical low-stock: based on real 30-day sales velocity, flag items
        # projected to run out within 10 days (plus anything already at zero).
        month_ago = tz.now() - timedelta(days=30)
        velocity = {
            r["product_id"]: r["q"] / 30.0
            for r in OrderItem.objects.filter(order__created_at__gte=month_ago, product__in=products)
            .exclude(order__status=Order.Status.CANCELED)
            .values("product_id")
            .annotate(q=Sum("quantity"))
        }
        low_stock = []
        for p in products.filter(is_active=True).values("id", "name", "sku", "stock"):
            rate = velocity.get(p["id"], 0)
            if p["stock"] == 0:
                low_stock.append({**p, "days_left": 0})
            elif rate > 0 and p["stock"] / rate <= 10:
                low_stock.append({**p, "days_left": round(p["stock"] / rate)})
        low_stock.sort(key=lambda x: x["days_left"])

        pending_shops = ShopkeeperProfile.objects.filter(status=ShopkeeperProfile.Status.PENDING)
        return Response(
            {
                "orders_total": orders.count(),
                "orders_pending_receipt": orders.filter(status=Order.Status.RECEIPT_UPLOADED).count(),
                "orders_awaiting_payment": orders.filter(status=Order.Status.PENDING_PAYMENT).count(),
                # Shop approval is a site-owner task.
                "shops_pending": pending_shops.count() if is_owner else 0,
                "shops_total": User.objects.filter(role=User.Role.SHOPKEEPER).count() if is_owner else 0,
                "products_total": products.count(),
                "products_out_of_stock": products.filter(stock=0).count(),
                "credit_outstanding": unsettled.aggregate(s=Sum("amount"))["s"] or 0,
                "credit_invoices_open": unsettled.count(),
                "sales_week": sales_week,
                "low_stock": low_stock[:8],
            }
        )


class SalesReportView(APIView):
    """Sales report over a date range: totals, daily series, top products and
    status breakdown. GET ?days=30 (7/30/90...).

    The site owner gets the whole marketplace (order totals); a supplier gets
    only the lines of their own products, so no supplier sees another's sales.
    """

    permission_classes = [permissions.IsAuthenticated, IsSupplierOrAdmin]

    def get(self, request):
        from datetime import timedelta

        from django.utils import timezone as tz

        days = max(1, min(365, int(request.query_params.get("days", 30) or 30)))
        # Local (Tehran) calendar days, matching TruncDate in the queries below.
        start = tz.localdate() - timedelta(days=days - 1)
        if is_site_admin(request.user):
            report = self._marketplace_report(start)
        else:
            report = self._supplier_report(request.user, start)
        report["series"] = _series(_daily_sales(request.user, start), start, days)
        report["days"] = days
        report["avg_order"] = round(report["revenue"] / report["orders"]) if report["orders"] else 0
        return Response(report)

    @staticmethod
    def _marketplace_report(start):
        from django.db.models import Count, F, Sum

        from apps.orders.models import Order, OrderItem

        orders = Order.objects.filter(created_at__date__gte=start)
        valid = orders.exclude(status=Order.Status.CANCELED)
        agg = valid.aggregate(total=Sum("total"), count=Count("id"))
        return {
            "revenue": agg["total"] or 0,
            "orders": agg["count"] or 0,
            "canceled": orders.filter(status=Order.Status.CANCELED).count(),
            "top_products": list(
                OrderItem.objects.filter(order__in=valid)
                .values("product_id", "product_name")
                .annotate(qty=Sum("quantity"), revenue=Sum(F("quantity") * F("unit_price")))
                .order_by("-revenue")[:10]
            ),
            "by_status": list(orders.values("status").annotate(count=Count("id"), total=Sum("total"))),
        }

    @staticmethod
    def _supplier_report(supplier, start):
        from django.db.models import Count, F, Sum

        from apps.orders.models import Order, OrderItem

        line_value = F("quantity") * F("unit_price")
        lines = OrderItem.objects.filter(product__supplier=supplier, order__created_at__date__gte=start)
        valid = lines.exclude(order__status=Order.Status.CANCELED)
        agg = valid.aggregate(total=Sum(line_value), count=Count("order", distinct=True))
        return {
            "revenue": agg["total"] or 0,
            "orders": agg["count"] or 0,
            "canceled": lines.filter(order__status=Order.Status.CANCELED).values("order").distinct().count(),
            "top_products": list(
                valid.values("product_id", "product_name")
                .annotate(qty=Sum("quantity"), revenue=Sum(line_value))
                .order_by("-revenue")[:10]
            ),
            "by_status": list(
                lines.values(status=F("order__status")).annotate(
                    count=Count("order", distinct=True), total=Sum(line_value)
                )
            ),
        }


class SupplierEarningsView(APIView):
    """The signed-in supplier's revenue split: for every successful order, how
    much the site owner took and how much is theirs ("my share").

    GET ?days=90&status=earned&q=YM...  (list) + a summary block.
    """

    permission_classes = [permissions.IsAuthenticated, IsSupplierOrAdmin]
    PAGE_SIZE = 20

    def get(self, request):
        from django.db.models import Sum

        from apps.commissions.models import OrderSupplierShare
        from apps.commissions.serializers import OrderSupplierShareSerializer

        qs = (
            OrderSupplierShare.objects.filter(supplier=request.user)
            .select_related("order")
            .exclude(status=OrderSupplierShare.Status.VOID)
        )

        params = request.query_params
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("q"):
            qs = qs.filter(order__number__icontains=params["q"])
        if params.get("days"):
            try:
                since = timezone.now() - timedelta(days=int(params["days"]))
                qs = qs.filter(created_at__gte=since)
            except ValueError:
                pass

        # "This month" is the current Jalali month in local (Tehran) time.
        month_start = jalali_month_start(timezone.localdate())
        base = OrderSupplierShare.objects.filter(supplier=request.user).exclude(status=OrderSupplierShare.Status.VOID)

        def agg(queryset, field):
            return queryset.aggregate(s=Sum(field))["s"] or 0

        summary = {
            "sales_total": agg(base, "gross_amount"),
            "owner_commission_total": agg(base, "owner_commission"),
            "net_total": agg(base, "supplier_net"),
            "net_this_month": agg(base.filter(created_at__date__gte=month_start), "supplier_net"),
            "net_paid": agg(base.filter(status=OrderSupplierShare.Status.PAID), "supplier_net"),
            "net_unpaid": agg(
                base.filter(status__in=[OrderSupplierShare.Status.EARNED, OrderSupplierShare.Status.PENDING]),
                "supplier_net",
            ),
            "orders_count": base.count(),
        }

        page = max(1, int(params.get("page", 1) or 1))
        start = (page - 1) * self.PAGE_SIZE
        return Response(
            {
                "summary": summary,
                "count": qs.count(),
                "results": OrderSupplierShareSerializer(qs[start : start + self.PAGE_SIZE], many=True).data,
            }
        )


class SmsLogListView(APIView):
    """Recent SMS activity for the supplier panel."""

    permission_classes = [IsSiteAdmin]

    PAGE_SIZE = 20

    def get(self, request):
        from apps.notifications.models import SmsLog

        page = max(1, int(request.query_params.get("page", 1) or 1))
        qs = SmsLog.objects.order_by("-created_at").values(
            "id", "recipient", "message", "kind", "provider", "is_sent", "created_at"
        )
        start = (page - 1) * self.PAGE_SIZE
        return Response(
            {
                "count": qs.count(),
                "results": list(qs[start : start + self.PAGE_SIZE]),
            }
        )


class PaymentInfoView(APIView):
    """Card-to-card destination for buyers on the payment page.

    The destination is the marketplace's own card (SupplierSettings.bank_details).
    Which methods are offered depends on what's actually in the buyer's cart:
    online is available whenever the gateway is configured; card-to-card only
    when the admin has switched it on for every supplier represented in the
    cart (see apps.orders.services.card_to_card_allowed).
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.orders.services import card_to_card_allowed
        from apps.payments.models import PaymentGatewaySettings

        s = SupplierSettings.bank_details()

        cart = getattr(request.user, "cart", None)
        items = list(cart.items.select_related("product").all()) if cart else []
        gateway_cfg = PaymentGatewaySettings.load()
        methods = {
            "receipt": card_to_card_allowed(items) if items else False,
            "online": gateway_cfg.is_configured,
        }
        if not s:
            return Response(
                {
                    "card_number": "",
                    "card_holder": "",
                    "account_number": "",
                    "iban": "",
                    "methods": methods,
                }
            )
        return Response(
            {
                "card_number": s.card_number,
                "card_holder": s.card_holder,
                "account_number": s.account_number,
                "iban": s.iban,
                "methods": methods,
            }
        )


class SupplierSettingsView(APIView):
    """Supplier reads/updates their own settings (reminder lead time, card...)."""

    permission_classes = [permissions.IsAuthenticated, IsSupplierOrAdmin]

    def get(self, request):
        obj, _ = SupplierSettings.objects.get_or_create(supplier=request.user)
        return Response(SupplierSettingsSerializer(obj).data)

    def patch(self, request):
        obj, _ = SupplierSettings.objects.get_or_create(supplier=request.user)
        data = request.data.copy()
        # Which payment methods a supplier's products may use is an
        # owner-only decision now — a supplier can't switch this on for
        # themselves, only the admin (from their own panel) can.
        if not (request.user.is_superuser or request.user.role == "admin"):
            data.pop("receipt_payment_enabled", None)
            data.pop("online_payment_enabled", None)
        serializer = SupplierSettingsSerializer(obj, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SupplierPaymentMethodsAdminView(APIView):
    """Admin-only: which suppliers may offer card-to-card (bank receipt) payment.

    GET lists every supplier account with their current flag; PATCH toggles
    one by id. This is deliberately separate from the supplier's own
    /suppliers/settings/ endpoint — a supplier cannot grant this to themselves.
    """

    permission_classes = [permissions.IsAuthenticated]

    def _check_admin(self, request):
        if not (request.user.is_superuser or request.user.role == "admin"):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("این بخش فقط برای مدیر سایت در دسترس است.")

    def get(self, request):
        from apps.accounts.models import User

        self._check_admin(request)
        suppliers = User.objects.filter(role=User.Role.SUPPLIER)
        rows = []
        for u in suppliers:
            settings_obj, _ = SupplierSettings.objects.get_or_create(supplier=u)
            rows.append(
                {
                    "supplier_id": u.id,
                    "supplier_name": u.full_name or u.phone,
                    "phone": u.phone,
                    "receipt_payment_enabled": settings_obj.receipt_payment_enabled,
                }
            )
        return Response(rows)

    def patch(self, request):
        self._check_admin(request)
        supplier_id = request.data.get("supplier_id")
        obj, _ = SupplierSettings.objects.get_or_create(supplier_id=supplier_id)
        obj.receipt_payment_enabled = bool(request.data.get("receipt_payment_enabled"))
        obj.save(update_fields=["receipt_payment_enabled"])
        return Response(
            {
                "supplier_id": obj.supplier_id,
                "receipt_payment_enabled": obj.receipt_payment_enabled,
            }
        )


class CreditAccountViewSet(viewsets.ModelViewSet):
    """Supplier defines/edits per-shop credit terms."""

    serializer_class = CreditAccountSerializer
    permission_classes = [permissions.IsAuthenticated, IsSupplierOrAdmin]

    def get_queryset(self):
        return CreditAccount.objects.filter(supplier=self.request.user).select_related("shop")

    def perform_create(self, serializer):
        serializer.save(supplier=self.request.user)


class SupplierInvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """Supplier's view of all credit invoices; can mark them settled."""

    serializer_class = CreditInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated, IsSupplierOrAdmin]

    def get_queryset(self):
        qs = CreditInvoice.objects.filter(account__supplier=self.request.user)
        state = self.request.query_params.get("state")  # settled | unsettled | overdue
        if state == "settled":
            qs = qs.filter(is_settled=True)
        elif state == "unsettled":
            qs = qs.filter(is_settled=False)
        elif state == "overdue":
            qs = qs.filter(is_settled=False, due_date__lt=timezone.localdate())
        return qs.select_related("order", "account__shop")

    @action(detail=True, methods=["post"])
    def settle(self, request, pk=None):
        invoice = self.get_object()
        invoice.settle()
        return Response(CreditInvoiceSerializer(invoice).data)

    @action(detail=True, methods=["post"])
    def remind(self, request, pk=None):
        """Manually send the settlement-reminder SMS for one invoice, now."""
        from apps.notifications.models import SmsLog
        from apps.notifications.tasks import send_sms

        invoice = self.get_object()
        if invoice.is_settled:
            return Response({"detail": "این فاکتور قبلاً تسویه شده است."}, status=400)
        shop = invoice.account.shop
        shop_name = invoice.shop_display_name
        message = invoice.reminder_message()
        send_sms.delay(shop.phone, message, kind=SmsLog.Kind.SETTLEMENT_REMINDER)
        invoice.reminder_sent_at = timezone.now()
        invoice.save(update_fields=["reminder_sent_at"])
        return Response({"detail": f"پیامک یادآوری برای {shop_name} ارسال شد."})


class MyCreditInvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """Shopkeeper's own purchases panel.

    ?state=settled|unsettled|overdue and ?due_in=<days> support the requested
    filters: which are paid, which are unpaid, and which are due in N days.
    """

    serializer_class = CreditInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated, IsApprovedShopkeeper]

    def get_queryset(self):
        qs = CreditInvoice.objects.filter(account__shop=self.request.user)
        state = self.request.query_params.get("state")
        if state == "settled":
            qs = qs.filter(is_settled=True)
        elif state == "unsettled":
            qs = qs.filter(is_settled=False)
        elif state == "overdue":
            qs = qs.filter(is_settled=False, due_date__lt=timezone.localdate())

        due_in = self.request.query_params.get("due_in")
        if due_in and due_in.isdigit():
            target = timezone.localdate() + timedelta(days=int(due_in))
            qs = qs.filter(is_settled=False, due_date__lte=target)
        return qs.select_related("order")
