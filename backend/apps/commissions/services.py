"""Commission calculation — the single place that decides what the owner earns."""

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from .models import (
    CategoryCommissionRate,
    CommissionEntry,
    CommissionSetting,
    OrderSupplierShare,
)


def _category_rates():
    """{category_id: rate} — one query, reused across every line of an order."""
    return dict(CategoryCommissionRate.objects.values_list("category_id", "rate"))


def _commissionable_lines(order, setting):
    """Return ``[(item, net_amount, rate), ...]`` for every line of an order.

    The commission is taken on the goods only: VAT and shipping are part of the
    order total but not of the sale, so they never enter the base. A coupon
    discount is spread across the lines it applied to (every line for a
    site-wide coupon, one supplier's lines for a supplier coupon) in proportion
    to their value instead of hitting a single product.
    """
    items = list(order.items.select_related("product"))
    if sum(item.unit_price * item.quantity for item in items) <= 0:
        return []

    def discounted(item):
        return order.discount_supplier_id is None or item.product.supplier_id == order.discount_supplier_id

    discounted_gross = sum(item.unit_price * item.quantity for item in items if discounted(item))
    discount = min(order.discount_amount or 0, discounted_gross)
    net_ratio = Decimal(discounted_gross - discount) / Decimal(discounted_gross) if discounted_gross else Decimal(1)
    overrides = _category_rates()
    role_rate = setting.rate_for_user(order.user)
    return [
        (
            item,
            Decimal(item.unit_price * item.quantity) * (net_ratio if discounted(item) else Decimal(1)),
            overrides.get(item.product.category_id, role_rate),
        )
        for item in items
    ]


def _effective_rate(commission, base):
    return (Decimal(commission) * 100 / Decimal(base)).quantize(Decimal("0.01")) if base else Decimal("0.00")


def calculate_for_order(order, setting=None):
    """Return (base_amount, commission_amount, effective_rate) for an order."""
    setting = setting or CommissionSetting.load()
    lines = _commissionable_lines(order, setting)
    if not lines:
        return 0, 0, Decimal("0.00")

    base_total = sum(int(net) for _item, net, _rate in lines)
    commission_total = sum(net * rate / Decimal(100) for _item, net, rate in lines)
    amount = int(commission_total.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return base_total, amount, _effective_rate(amount, base_total)


@transaction.atomic
def record_commission(order, status=None):
    """Record the commission row for an order (idempotent).

    Called on every save of a live order. The figures are fixed when the row is
    created; later calls only move a pending row forward, so a rate change
    never rewrites a sale that was already recognised. A void row (the order
    was canceled and has come back) is recognised afresh. Returns the entry, or
    None when the feature is switched off or no beneficiary is configured yet.
    """
    setting = CommissionSetting.load()
    if not setting.is_active or not setting.beneficiary_id:
        return None
    if order.user_id == setting.beneficiary_id:
        return None  # the beneficiary buying from themselves earns nothing

    base, amount, rate = calculate_for_order(order, setting)
    if amount <= 0:
        return None

    entry, created = CommissionEntry.objects.get_or_create(
        order=order,
        defaults={
            "beneficiary_id": setting.beneficiary_id,
            "buyer": order.user,
            "buyer_role": order.user.role,
            "base_amount": base,
            "effective_rate": rate,
            "amount": amount,
            "status": status or CommissionEntry.Status.EARNED,
        },
    )
    if created:
        return entry

    new_status = status or CommissionEntry.Status.EARNED
    if entry.status == CommissionEntry.Status.VOID:
        # A canceled order that came back is a new sale, priced at today's rates.
        entry.status = new_status
        entry.base_amount, entry.amount, entry.effective_rate = base, amount, rate
        entry.save(update_fields=["status", "base_amount", "amount", "effective_rate"])
    elif entry.status == CommissionEntry.Status.PENDING and new_status != entry.status:
        # Pending → earned: only the status moves, the figures stay as recorded.
        entry.status = new_status
        entry.save(update_fields=["status"])
    return entry


def void_commission(order, reason="سفارش لغو شد"):
    """A canceled order must not leave earnings behind."""
    CommissionEntry.objects.filter(order=order).exclude(status=CommissionEntry.Status.PAID).update(
        status=CommissionEntry.Status.VOID, note=reason
    )
    OrderSupplierShare.objects.filter(order=order).exclude(status=OrderSupplierShare.Status.PAID).update(
        status=OrderSupplierShare.Status.VOID, note=reason
    )


@transaction.atomic
def record_supplier_shares(order, status=None, setting=None):
    """Snapshot the owner-vs-supplier split for each supplier in the order.

    Uses the same lines as ``calculate_for_order`` (same discount spreading,
    same per-category rate resolution) but groups them by ``product.supplier`` so every
    supplier gets their own row: how much they sold, what the site owner took,
    and what is left for them. Idempotent, with the same rules as
    ``record_commission``: an earned or paid row is never recalculated, a
    pending row only changes status, and a void row is recognised afresh.
    """
    setting = setting or CommissionSetting.load()
    if not setting.is_active or not setting.beneficiary_id:
        return []

    # supplier_id -> [gross, commission]
    buckets = {}
    for item, net, rate in _commissionable_lines(order, setting):
        supplier_id = item.product.supplier_id
        if not supplier_id:
            continue  # ownerless product — no supplier to pay
        bucket = buckets.setdefault(supplier_id, [Decimal(0), Decimal(0)])
        bucket[0] += net
        bucket[1] += net * rate / Decimal(100)

    entries = []
    default_status = status or OrderSupplierShare.Status.EARNED
    for supplier_id, (line_gross, commission) in buckets.items():
        g = int(line_gross.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        c = int(commission.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        c = min(c, g)  # never take more than the sale
        figures = {
            "gross_amount": g,
            "owner_commission": c,
            "supplier_net": g - c,
            "effective_rate": _effective_rate(c, g),
        }
        share, created = OrderSupplierShare.objects.get_or_create(
            order=order,
            supplier_id=supplier_id,
            defaults={**figures, "status": default_status},
        )
        if not created and share.status == OrderSupplierShare.Status.VOID:
            for field, value in figures.items():
                setattr(share, field, value)
            share.status = default_status
            share.save(update_fields=[*figures, "status"])
        elif not created and share.status == OrderSupplierShare.Status.PENDING and default_status != share.status:
            share.status = default_status
            share.save(update_fields=["status"])
        entries.append(share)
    return entries


def mark_paid(entry):
    entry.status = CommissionEntry.Status.PAID
    entry.paid_at = timezone.now()
    entry.save(update_fields=["status", "paid_at"])
    return entry
