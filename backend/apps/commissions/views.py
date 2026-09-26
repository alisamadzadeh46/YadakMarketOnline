"""Revenue-share API — dashboard, ledger and self-service rate control."""

import contextlib
from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.utils import jalali_month_start

from .models import (
    CategoryCommissionRate,
    CommissionEntry,
    CommissionSetting,
    OrderSupplierShare,
)
from .permissions import IsCommissionBeneficiary
from .serializers import (
    CategoryCommissionRateSerializer,
    CommissionEntrySerializer,
    CommissionSettingSerializer,
)
from .services import mark_paid


class CommissionSettingView(APIView):
    """GET/PATCH the revenue-share configuration — the owner's own control."""

    permission_classes = [IsCommissionBeneficiary]

    def get(self, request):
        return Response(CommissionSettingSerializer(CommissionSetting.load()).data)

    def patch(self, request):
        setting = CommissionSetting.load()
        serializer = CommissionSettingSerializer(setting, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class CommissionEntryListView(ListAPIView):
    """The ledger: every sale that earned the owner money.

    Filters: ?status=earned&role=shopkeeper&days=30&q=YM250100012
    """

    serializer_class = CommissionEntrySerializer
    permission_classes = [IsCommissionBeneficiary]

    def get_queryset(self):
        qs = CommissionEntry.objects.select_related("order", "buyer")
        params = self.request.query_params
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("role"):
            qs = qs.filter(buyer_role=params["role"])
        if params.get("days"):
            try:
                since = timezone.now() - timedelta(days=int(params["days"]))
                qs = qs.filter(created_at__gte=since)
            except ValueError:
                pass
        if params.get("q"):
            qs = qs.filter(order__number__icontains=params["q"])
        return qs


class CommissionEntryActionViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Settlement actions on a single ledger row."""

    serializer_class = CommissionEntrySerializer
    permission_classes = [IsCommissionBeneficiary]
    queryset = CommissionEntry.objects.select_related("order", "buyer")

    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request, pk=None):
        entry = self.get_object()
        return Response(CommissionEntrySerializer(mark_paid(entry)).data)


class CommissionSummaryView(APIView):
    """Headline numbers + a 14-day earnings chart for the dashboard."""

    permission_classes = [IsCommissionBeneficiary]

    def get(self, request):
        qs = CommissionEntry.objects.all()
        earned = qs.filter(status=CommissionEntry.Status.EARNED)
        # Local (Tehran) calendar: TruncDate and __date lookups use it too, and
        # "this month" is the current Jalali month.
        today = timezone.localdate()
        month_start = jalali_month_start(today)

        def total(queryset):
            return queryset.aggregate(s=Sum("amount"))["s"] or 0

        days = 14
        since = today - timedelta(days=days - 1)
        rows = {
            r["d"]: r["s"]
            for r in qs.exclude(status=CommissionEntry.Status.VOID)
            .filter(created_at__date__gte=since)
            .annotate(d=TruncDate("created_at"))
            .values("d")
            .annotate(s=Sum("amount"))
        }
        chart = [
            {"date": (since + timedelta(days=i)).isoformat(), "total": rows.get(since + timedelta(days=i), 0)}
            for i in range(days)
        ]

        by_role = list(
            qs.exclude(status=CommissionEntry.Status.VOID)
            .values("buyer_role")
            .annotate(total=Sum("amount"), orders=Count("id"))
            .order_by("-total")
        )

        setting = CommissionSetting.load()
        return Response(
            {
                "unpaid": total(earned),
                "paid": total(qs.filter(status=CommissionEntry.Status.PAID)),
                "pending": total(qs.filter(status=CommissionEntry.Status.PENDING)),
                "this_month": total(
                    qs.exclude(status=CommissionEntry.Status.VOID).filter(created_at__date__gte=month_start)
                ),
                "lifetime": total(qs.exclude(status=CommissionEntry.Status.VOID)),
                "orders_count": qs.exclude(status=CommissionEntry.Status.VOID).count(),
                "current_rate": setting.default_rate,
                "is_active": setting.is_active,
                "chart": chart,
                "by_role": by_role,
            }
        )


class CommissionBySupplierView(APIView):
    """Owner-side breakdown of every supplier's sales and the split.

    Answers, for the beneficiary, «per supplier: how much they sold, how much I
    took, how much is theirs». GET ?days=30 optional.
    """

    permission_classes = [IsCommissionBeneficiary]

    def get(self, request):
        qs = OrderSupplierShare.objects.exclude(status=OrderSupplierShare.Status.VOID)
        days = request.query_params.get("days")
        if days:
            with contextlib.suppress(ValueError):
                qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=int(days)))
        rows = list(
            qs.values("supplier_id", "supplier__full_name", "supplier__phone")
            .annotate(
                sales=Sum("gross_amount"),
                owner_commission=Sum("owner_commission"),
                supplier_net=Sum("supplier_net"),
                orders=Count("order_id", distinct=True),
            )
            .order_by("-owner_commission")
        )
        for r in rows:
            r["supplier_name"] = r.pop("supplier__full_name") or r.pop("supplier__phone")
            r.pop("supplier__phone", None)
        return Response(rows)


class CategoryRateViewSet(viewsets.ModelViewSet):
    """Per-category overrides, fully editable from the panel."""

    serializer_class = CategoryCommissionRateSerializer
    permission_classes = [IsCommissionBeneficiary]
    queryset = CategoryCommissionRate.objects.select_related("category")
    pagination_class = None
