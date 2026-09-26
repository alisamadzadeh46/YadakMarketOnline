"""BitPay / ZarinPal gateway clients + the request/verify orchestration.

Uses the standard library only (urllib), matching apps.notifications.backends —
no extra runtime dependency to pull from a package index.

Both providers follow the same three-step shape:
  1. request(order)  -> POST amount+callback, get back an authority/id_get
  2. redirect the buyer to the bank page built from that authority
  3. the bank redirects back to our callback; verify(...) confirms the charge

Amounts everywhere in this app are Toman; both gateways bill in Rial, so we
multiply/divide by 10 at the edges only.
"""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.orders.models import Order

from .models import PaymentGatewaySettings, PaymentTransaction

logger = logging.getLogger(__name__)

Gateway = PaymentGatewaySettings.Gateway


class GatewayError(Exception):
    """Raised for any failure that should show the buyer a friendly message."""


def _post(url, data, timeout=20, as_json=False):
    """POST to a gateway.

    ``as_json`` picks the encoding: BitPay wants a classic form body, ZarinPal's
    REST v4 rejects anything that is not ``application/json``. Errors carry the
    response body through so a 4xx from the gateway is still diagnosable —
    ZarinPal in particular returns its real reason inside an HTTP 400.
    """
    if as_json:
        payload = json.dumps(data).encode()
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
    else:
        payload = urllib.parse.urlencode(data).encode()
        headers = {}
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
        logger.info("gateway POST %s -> %r", url, body[:400])
        return body
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace") if exc.fp else ""
        logger.error("gateway POST %s -> HTTP %s %r", url, exc.code, detail[:400])
        # ZarinPal answers a rejected request with 400 + a JSON error body; that
        # body is far more useful than the status code, so hand it back.
        if as_json and detail:
            try:
                return detail
            except ValueError:
                pass
        raise GatewayError(f"درگاه پرداخت پاسخ خطا داد (HTTP {exc.code}).") from exc
    except urllib.error.URLError as exc:
        logger.error("gateway POST %s unreachable: %s", url, exc.reason)
        raise GatewayError(
            "در حال حاضر ارتباط با درگاه پرداخت برقرار نشد. لطفاً چند لحظه بعد دوباره تلاش کنید."
        ) from exc


def _post_json(url, data, timeout=20, as_json=False):
    body = _post(url, data, timeout=timeout, as_json=as_json)
    try:
        return json.loads(body)
    except ValueError as exc:
        raise GatewayError("پاسخ نامعتبر از درگاه پرداخت دریافت شد.") from exc


# --- BitPay ------------------------------------------------------------------


class BitPayGateway:
    """https://bitpay.ir — POST+redirect+POST-verify, plain-text / JSON mixed."""

    # Documented gateway-send rejection codes (BP_PGW_DOC v2.2).
    SEND_ERRORS = {
        -1: "کد API درگاه نامعتبر است (باید دقیقاً ۵۲ کاراکتر باشد).",
        -2: "مبلغ نامعتبر است؛ حداقل مبلغ پرداخت ۵٬۰۰۰ ریال (۵۰۰ تومان) است.",
        -3: "آدرس بازگشت (redirect) خالی است.",
        -4: "درگاهی با این اطلاعات وجود ندارد یا هنوز تایید نشده است — "
        "کد API و تطابق دامنه ثبت‌شده در بیت‌پی را بررسی کنید.",
        -5: "خطا در اتصال به درگاه بیت‌پی؛ لطفاً دوباره تلاش کنید.",
    }

    # BitPay bills in Rial; the whole store works in Toman.
    MIN_RIAL = 5000

    def _base(self, cfg):
        return "https://bitpay.ir/payment-test" if cfg.bitpay_sandbox else "https://bitpay.ir/payment"

    def request(self, order, cfg, callback_url):
        amount_rial = order.total * 10
        if amount_rial < self.MIN_RIAL:
            raise GatewayError(f"حداقل مبلغ پرداخت آنلاین {self.MIN_RIAL // 10:,} تومان است.")
        body = _post(
            f"{self._base(cfg)}/gateway-send",
            {
                "api": cfg.bitpay_api_key,
                "redirect": callback_url,
                "amount": amount_rial,
                "factorId": order.pk,
                "name": order.ship_to_name,
                "description": f"سفارش {order.number} — {settings.SITE_NAME}",
            },
        )
        raw = (body or "").strip()
        try:
            id_get = int(raw)
        except ValueError:
            logger.error("BitPay gateway-send returned non-numeric body: %r", raw[:200])
            raise GatewayError("پاسخ نامعتبر از بیت‌پی دریافت شد.") from None
        if id_get <= 0:
            logger.error("BitPay rejected gateway-send with code %s", id_get)
            raise GatewayError(self.SEND_ERRORS.get(id_get, f"بیت‌پی درخواست را رد کرد (کد {id_get})."))
        redirect_url = f"{self._base(cfg)}/gateway-{id_get}-get"
        return str(id_get), redirect_url

    def verify(self, txn, cfg, params):
        trans_id = params.get("trans_id", "")
        id_get = params.get("id_get", txn.authority)
        data = _post_json(
            f"{self._base(cfg)}/gateway-result-second",
            {
                "api": cfg.bitpay_api_key,
                "trans_id": trans_id,
                "id_get": id_get,
                "json": 1,
            },
        )
        status_code = data.get("status")
        ok = status_code in (1, "1", 11, "11")  # 11 = already verified
        # ZarinPal validates the amount server-side (it answers -50 on a
        # mismatch); BitPay does not, so a successful status alone would let a
        # smaller charge settle a larger order. Compare it ourselves, against
        # the amount recorded when the transaction was created — never against
        # anything in the callback.
        if ok:
            try:
                paid_rial = int(float(data.get("amount") or 0))
            except (TypeError, ValueError):
                paid_rial = 0
            expected_rial = txn.amount * 10
            if paid_rial and paid_rial != expected_rial:
                logger.error(
                    "BitPay amount mismatch on txn %s: paid %s rial, expected %s rial",
                    txn.pk,
                    paid_rial,
                    expected_rial,
                )
                ok = False
        return {
            "ok": ok,
            "trans_id": str(trans_id),
            "ref_id": str(data.get("factorId") or trans_id),
            "card_number": str(data.get("cardNum") or ""),
            "raw": data,
        }


# --- ZarinPal ------------------------------------------------------------------


class ZarinpalGateway:
    """https://www.zarinpal.com/docs — REST v4, JSON in and JSON out.

    Three things here are easy to get wrong and all three break payment:
      * the host is ``payment.zarinpal.com``, not ``api.`` and not ``www.``
      * the body MUST be ``application/json``; a form-encoded POST is rejected
      * ``currency`` is sent explicitly as IRR so the Rial amount is never
        re-interpreted as Toman by a change of account default.
    """

    # ZarinPal's floor is 1,000 Toman.
    MIN_TOMAN = 1000

    # Documented rejection codes worth translating; anything else falls back to
    # ZarinPal's own message, which is already Persian.
    ERRORS = {
        -9: "اطلاعات ارسالی به زرین‌پال ناقص یا نامعتبر است.",
        -10: "آی‌پی یا مرچنت کد پذیرنده صحیح نیست.",
        -11: "مرچنت کد فعال نیست؛ با پشتیبانی زرین‌پال تماس بگیرید.",
        -12: "تلاش‌های ناموفق بیش از حد مجاز؛ کمی بعد دوباره تلاش کنید.",
        -15: "درگاه پرداخت به حالت تعلیق درآمده است.",
        -16: "سطح تایید پذیرنده پایین‌تر از سطح نقره‌ای است.",
        -50: "مبلغ پرداخت‌شده با مبلغ ارسالی در تایید یکسان نیست.",
        -51: "پرداخت ناموفق بود.",
        -53: "این تراکنش متعلق به این پذیرنده نیست.",
        -54: "شناسه تراکنش (authority) نامعتبر است.",
    }

    API = "https://payment.zarinpal.com/pg/v4/payment"
    START = "https://payment.zarinpal.com/pg/StartPay"
    SANDBOX_API = "https://sandbox.zarinpal.com/pg/v4/payment"
    SANDBOX_START = "https://sandbox.zarinpal.com/pg/StartPay"

    def _api_base(self, cfg):
        return self.SANDBOX_API if cfg.zarinpal_sandbox else self.API

    def _start_pay_base(self, cfg):
        return self.SANDBOX_START if cfg.zarinpal_sandbox else self.START

    def _fail(self, data, fallback):
        """Turn a ZarinPal ``errors`` payload into a message for the buyer."""
        errors = (data or {}).get("errors") or {}
        if isinstance(errors, list):  # v4 sometimes returns [] instead of {}
            errors = errors[0] if errors else {}
        code = errors.get("code")
        message = self.ERRORS.get(code) or errors.get("message") or fallback
        logger.error("Zarinpal rejected: code=%s errors=%r", code, errors)
        return GatewayError(f"{message}" + (f" (کد {code})" if code else ""))

    def request(self, order, cfg, callback_url):
        if order.total < self.MIN_TOMAN:
            raise GatewayError(f"حداقل مبلغ پرداخت آنلاین {self.MIN_TOMAN:,} تومان است.")
        data = _post_json(
            f"{self._api_base(cfg)}/request.json",
            {
                "merchant_id": cfg.zarinpal_merchant_id,
                "amount": order.total * 10,  # store works in Toman, ZarinPal in Rial
                "currency": "IRR",
                "callback_url": callback_url,
                "description": f"سفارش {order.number} — {settings.SITE_NAME}",
                "metadata": {"mobile": order.ship_to_phone or "", "order_id": str(order.pk)},
            },
            as_json=True,
        )
        payload = (data or {}).get("data") or {}
        if payload.get("code") != 100 or not payload.get("authority"):
            raise self._fail(data, "زرین‌پال درخواست پرداخت را رد کرد.")
        authority = payload["authority"]
        return authority, f"{self._start_pay_base(cfg)}/{authority}"

    def verify(self, txn, cfg, params):
        # Status=NOK means the buyer cancelled at the bank — never call verify.
        if params.get("Status") != "OK":
            return {"ok": False, "trans_id": "", "ref_id": "", "card_number": "", "raw": params}
        data = _post_json(
            f"{self._api_base(cfg)}/verify.json",
            {
                "merchant_id": cfg.zarinpal_merchant_id,
                "amount": txn.amount * 10,
                "authority": txn.authority,
            },
            as_json=True,
        )
        payload = (data or {}).get("data") or {}
        ok = payload.get("code") in (100, 101)  # 101 = already verified
        return {
            "ok": ok,
            "trans_id": str(payload.get("ref_id") or ""),
            "ref_id": str(payload.get("ref_id") or ""),
            "card_number": str(payload.get("card_pan") or ""),
            "raw": data,
        }


GATEWAYS = {
    Gateway.BITPAY: BitPayGateway(),
    Gateway.ZARINPAL: ZarinpalGateway(),
}


def start_payment(order, callback_url_builder, gateway=None):
    """Create a PaymentTransaction and return the URL to send the buyer to.

    ``gateway`` is the buyer's choice; it is validated against the gateways the
    owner has actually switched on, so a hand-crafted request cannot drive a
    disabled — or credential-less — provider. ``None`` falls back to the
    configured default.

    ``callback_url_builder(gateway)`` builds our own callback URL for that
    gateway (they differ, so the gateway is baked into the path).
    """
    cfg = PaymentGatewaySettings.load()
    available = cfg.available_gateways
    if not available:
        raise GatewayError("درگاه پرداخت آنلاین هنوز پیکربندی نشده است.")

    chosen = gateway or cfg.default_gateway
    if chosen not in available:
        raise GatewayError("درگاه انتخاب‌شده در دسترس نیست. لطفاً درگاه دیگری را انتخاب کنید.")

    client = GATEWAYS[chosen]
    callback_url = callback_url_builder(chosen)
    authority, redirect_url = client.request(order, cfg, callback_url)
    PaymentTransaction.objects.create(
        order=order,
        gateway=chosen,
        amount=order.total,
        authority=authority,
        status=PaymentTransaction.Status.PENDING,
    )
    return redirect_url


@transaction.atomic
def handle_callback(gateway, params):
    """Verify a gateway callback and confirm the order if the charge is real.

    Returns (order, success: bool) — the view decides how to redirect the
    buyer from there. Idempotent: a gateway retrying the same callback (or the
    buyer refreshing the return page) never double-charges or double-confirms.
    """
    cfg = PaymentGatewaySettings.load()
    client = GATEWAYS.get(gateway)
    if not client:
        raise GatewayError("درگاه نامعتبر است.")

    authority = params.get("Authority") or params.get("id_get") or ""
    txn = (
        PaymentTransaction.objects.select_for_update()
        .filter(gateway=gateway, authority=authority)
        .order_by("-created_at")
        .first()
    )
    if not txn:
        raise GatewayError("تراکنش یافت نشد.")

    # Lock the order too: the expiry sweep takes the same lock, so a payment
    # and a timeout cancellation can never interleave.
    order = Order.objects.select_for_update().get(pk=txn.order_id)
    if txn.status == PaymentTransaction.Status.SUCCESS:
        # Already verified — don't hit the bank again.
        return order, order.status != Order.Status.CANCELED

    result = client.verify(txn, cfg, params)
    txn.raw_response = result["raw"]
    txn.trans_id = result["trans_id"]
    txn.ref_id = result["ref_id"]
    txn.card_number = result["card_number"]
    txn.status = PaymentTransaction.Status.SUCCESS if result["ok"] else PaymentTransaction.Status.FAILED
    txn.save()

    def _notify_success():
        from apps.core.utils import site_host, to_fa
        from apps.notifications.models import SmsLog
        from apps.notifications.tasks import send_sms

        name = order.user.full_name or order.ship_to_name
        # The tracking code stays in Latin digits on purpose: the buyer reads it
        # back to support and pastes it into the tracking URL, and Persian
        # digits do not survive that round trip.
        send_sms.delay(
            order.user.phone,
            f"{settings.SITE_NAME}\n"
            f"{name} عزیز، پرداخت شما با موفقیت انجام شد.\n\n"
            f"کد رهگیری: {order.number}\n"
            f"مبلغ: {to_fa(f'{order.total:,}')} تومان\n\n"
            "پیگیری سفارش:\n"
            f"{site_host()}/order/{order.number}",
            kind=SmsLog.Kind.ORDER,
        )

    def _notify_failure():
        from apps.core.utils import site_host, to_fa
        from apps.notifications.models import SmsLog
        from apps.notifications.tasks import send_sms

        remaining = max(0, order.seconds_left) // 60
        send_sms.delay(
            order.user.phone,
            f"{settings.SITE_NAME}\nپرداخت سفارش {order.number} ناموفق بود.\n"
            f"کالاهای شما در سبد خرید محفوظ است و تا {to_fa(remaining)} دقیقه دیگر "
            f"می‌توانید از صفحه سفارش دوباره پرداخت کنید.\n{site_host()}",
            kind=SmsLog.Kind.ORDER,
        )

    def _notify_paid_after_expiry():
        from apps.notifications.models import SmsLog
        from apps.notifications.tasks import send_sms

        send_sms.delay(
            order.user.phone,
            f"{settings.SITE_NAME}\nپرداخت سفارش {order.number} دریافت شد، اما مهلت سفارش پیش از آن "
            "به پایان رسیده و بخشی از کالاها دیگر موجود نیست. برای بازگشت وجه با پشتیبانی تماس بگیرید.",
            kind=SmsLog.Kind.ORDER,
        )

    def _notify_supplier_paid():
        try:
            from apps.suppliers.tasks import notify_supplier_new_order

            notify_supplier_new_order.delay(order.pk)
        except Exception:
            pass

    from apps.orders.services import clear_cart_lines_for_order, revive_paid_order

    if result["ok"] and order.status == Order.Status.CANCELED:
        # Paid after the payment window closed: take the stock back if it is
        # still there, otherwise the money has to be returned by hand.
        if not revive_paid_order(order):
            logger.error(
                "Order %s was paid after it expired and is out of stock; refund transaction %s",
                order.number,
                txn.pk,
            )
            transaction.on_commit(_notify_paid_after_expiry)
            return order, False
        clear_cart_lines_for_order(order)
        transaction.on_commit(_notify_success)
        transaction.on_commit(_notify_supplier_paid)
    elif result["ok"] and order.status == Order.Status.PENDING_PAYMENT:
        order.status = Order.Status.CONFIRMED
        order.paid_at = timezone.now()
        order.save(update_fields=["status", "paid_at"])
        # Online carts are held until the money is real, so this is where they
        # finally get emptied — a failed or abandoned payment leaves the basket
        # exactly as the buyer left it.
        clear_cart_lines_for_order(order)
        transaction.on_commit(_notify_success)
        # The supplier is told the item sold only now — the money is real.
        transaction.on_commit(_notify_supplier_paid)
    elif not result["ok"] and order.status == Order.Status.PENDING_PAYMENT:
        transaction.on_commit(_notify_failure)

    return order, result["ok"]
