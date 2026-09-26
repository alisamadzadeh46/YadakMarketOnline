"""Pluggable SMS backends.

The rest of the app only ever calls ``get_sms_backend().send(phone, text)`` so
the provider can be swapped via the ``SMS_PROVIDER`` setting without touching
business logic. Niazpardaz (payamak-service) is the production provider; the
console backend is the safe default until real credentials are supplied.

Uses the standard library only (urllib) so there is no extra runtime dependency
to pull from a package index — important given Iran connectivity constraints.
"""

import json
import logging
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


class BaseSmsBackend:
    def send(self, phone: str, message: str) -> dict:
        """Send one SMS. Returns {"ok": bool, "provider_ref": str, "raw": ...}."""
        raise NotImplementedError


class ConsoleSmsBackend(BaseSmsBackend):
    """Logs the message instead of sending. Used in dev and when unconfigured."""

    def send(self, phone, message):
        logger.info("[SMS -> %s] %s", phone, message)
        return {"ok": True, "provider_ref": "console", "raw": None}


class NiazpardazSmsBackend(BaseSmsBackend):
    """Niazpardaz / payamak-service REST API (SendBatchSms).

    A positive ``BatchSmsId`` in the response means the message was accepted;
    negative values are documented error codes.
    """

    ENDPOINT = "http://in.payamak-service.ir/api/v2/RestWebApi/SendBatchSms"

    def send(self, phone, message):
        username = settings.NIAZPARDAZ_USERNAME
        password = settings.NIAZPARDAZ_PASSWORD
        line = settings.NIAZPARDAZ_LINE_NUMBER
        # Fail safe: if credentials are missing, don't crash the caller.
        if not (username and password and line):
            logger.warning("Niazpardaz credentials missing; using console backend.")
            return ConsoleSmsBackend().send(phone, message)

        payload = urllib.parse.urlencode(
            {
                "userName": username,
                "password": password,
                "fromNumber": line,
                "toNumbers": phone,
                "messageContent": message,
            }
        ).encode()
        try:
            req = urllib.request.Request(self.ENDPOINT, data=payload)
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read().decode("utf-8", "replace")
            # Live response shape (verified against the real API):
            # {"success": bool, "result": {"batchSmsId": N, "resultCode": N},
            #  "errorMessage": "..."}
            try:
                data = json.loads(body)
                result = data.get("result") or {}
                batch_id = result.get("batchSmsId") or data.get("BatchSmsId") or 0
                ok = bool(data.get("success")) and int(batch_id or 0) > 0
                ref = str(batch_id) if ok else f"code:{result.get('resultCode')}"
            except (ValueError, AttributeError, TypeError):
                data, ok, ref = body, False, ""
            if not ok:
                logger.warning("Niazpardaz rejected the message: %s", data)
            return {"ok": ok, "provider_ref": ref, "raw": data}
        except Exception as exc:  # noqa: BLE001 - never let SMS break the caller
            logger.error("Niazpardaz send failed: %s", exc)
            return {"ok": False, "provider_ref": "", "raw": str(exc)}


_BACKENDS = {
    "niazpardaz": NiazpardazSmsBackend,
    "console": ConsoleSmsBackend,
}


def get_sms_backend() -> BaseSmsBackend:
    provider = getattr(settings, "SMS_PROVIDER", "console")
    return _BACKENDS.get(provider, ConsoleSmsBackend)()
