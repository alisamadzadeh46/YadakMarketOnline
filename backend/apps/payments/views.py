"""Online payment API: owner config, start-payment redirect, gateway callback."""

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order

from .models import PaymentGatewaySettings
from .permissions import IsPaymentGatewayAdmin
from .serializers import PaymentGatewaySettingsSerializer
from .services import GatewayError, handle_callback, start_payment


class PaymentGatewaySettingsView(APIView):
    """GET/PATCH the owner's gateway configuration."""

    permission_classes = [IsPaymentGatewayAdmin]

    def get(self, request):
        return Response(PaymentGatewaySettingsSerializer(PaymentGatewaySettings.load()).data)

    def patch(self, request):
        setting = PaymentGatewaySettings.load()
        serializer = PaymentGatewaySettingsSerializer(setting, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


GATEWAY_META = {
    PaymentGatewaySettings.Gateway.ZARINPAL: {
        "title": "زرین‌پال",
        "subtitle": "پرداخت امن با کارت‌های عضو شتاب",
    },
    PaymentGatewaySettings.Gateway.BITPAY: {
        "title": "بیت‌پی",
        "subtitle": "درگاه واسط با کارت‌های عضو شتاب",
    },
}


class PaymentGatewayChoicesView(APIView):
    """The gateways a buyer may pick from, and which one is preselected.

    Public-facing counterpart to PaymentGatewaySettingsView: it deliberately
    exposes only names and availability — never the merchant credentials.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cfg = PaymentGatewaySettings.load()
        return Response(
            {
                "default": cfg.default_gateway,
                "gateways": [
                    {"id": g, **GATEWAY_META.get(g, {"title": g, "subtitle": ""})} for g in cfg.available_gateways
                ],
            }
        )


class PaymentStartView(APIView):
    """Buyer clicked "pay online" — create the gateway session and hand back
    the URL the frontend should send the browser to."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, number):
        order = get_object_or_404(Order, number=number, user=request.user)
        if order.payment_method != Order.PaymentMethod.ONLINE:
            return Response({"detail": "این سفارش با پرداخت آنلاین ثبت نشده است."}, status=400)
        if order.status != Order.Status.PENDING_PAYMENT:
            return Response({"detail": "این سفارش در وضعیت قابل پرداخت نیست."}, status=400)

        def build_callback(gateway):
            return request.build_absolute_uri(f"/api/payments/callback/{gateway}/")

        # start_payment() validates this against the enabled list — the client
        # picking a gateway is a preference, not an authorisation.
        chosen = (request.data or {}).get("gateway") or None
        try:
            redirect_url = start_payment(order, build_callback, gateway=chosen)
        except GatewayError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response({"redirect_url": redirect_url})


class PaymentCallbackView(APIView):
    """Public — the gateway lands the buyer's browser here after payment.

    Both providers use GET redirects with their own query-string shape (bitpay:
    trans_id/id_get, zarinpal: Authority/Status); ``handle_callback`` knows the
    difference. We verify server-side, then bounce the browser to the frontend
    result page — the gateway never talks to the frontend directly.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, gateway):
        from django.conf import settings as dj_settings

        params = request.GET.dict()
        try:
            order, ok = handle_callback(gateway, params)
        except GatewayError:
            return HttpResponseRedirect(f"{dj_settings.FRONTEND_URL}/payments/result?ok=0")
        return HttpResponseRedirect(
            f"{dj_settings.FRONTEND_URL}/payments/result?order={order.number}&ok={'1' if ok else '0'}"
        )
