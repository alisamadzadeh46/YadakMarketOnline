"""Hook the commission engine onto the order lifecycle.

We deliberately listen to Order rather than calling the service from the views:
whatever path confirms an order (supplier panel, admin, a management command)
the owner's share is recorded exactly once.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.orders.models import Order

from .models import CommissionEntry, CommissionSetting, OrderSupplierShare
from .services import record_commission, record_supplier_shares, void_commission

# Statuses that mean "the money is real".
EARNING_STATUSES = {
    Order.Status.CONFIRMED,
    Order.Status.PROCESSING,
    Order.Status.SHIPPED,
    Order.Status.DELIVERED,
}
# A credit order is live from placement through delivery, but its money only
# arrives when the credit invoice is settled.
CREDIT_LIVE_STATUSES = EARNING_STATUSES | {Order.Status.CREDIT}


def _credit_sale_is_earned(order):
    """Recognised on placement if the owner chose so, otherwise once the invoice is settled."""
    if CommissionSetting.load().accrue_on_credit_order:
        return True
    invoice = getattr(order, "credit_invoice", None)
    return bool(invoice and invoice.is_settled)


@receiver(post_save, sender=Order)
def sync_commission(sender, instance, created, **kwargs):
    if instance.status == Order.Status.CANCELED:
        void_commission(instance)
    elif instance.payment_method == Order.PaymentMethod.CREDIT:
        if instance.status not in CREDIT_LIVE_STATUSES:
            return
        # Shipping a credit order does not pay for it, so the fulfilment status
        # must not turn a pending commission into income.
        earned = _credit_sale_is_earned(instance)
        record_commission(instance, status=CommissionEntry.Status.EARNED if earned else CommissionEntry.Status.PENDING)
        record_supplier_shares(
            instance, status=OrderSupplierShare.Status.EARNED if earned else OrderSupplierShare.Status.PENDING
        )
    elif instance.status in EARNING_STATUSES:
        record_commission(instance)
        record_supplier_shares(instance)


@receiver(post_save, sender="suppliers.CreditInvoice")
def settle_pending_commission(sender, instance, **kwargs):
    """A settled credit invoice turns its pending commission into real income."""
    if instance.is_settled and instance.order_id:
        CommissionEntry.objects.filter(order_id=instance.order_id, status=CommissionEntry.Status.PENDING).update(
            status=CommissionEntry.Status.EARNED
        )
        OrderSupplierShare.objects.filter(order_id=instance.order_id, status=OrderSupplierShare.Status.PENDING).update(
            status=OrderSupplierShare.Status.EARNED
        )
