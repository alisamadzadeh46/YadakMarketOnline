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


@receiver(post_save, sender=Order)
def sync_commission(sender, instance, created, **kwargs):
    if instance.status in EARNING_STATUSES:
        record_commission(instance)
        record_supplier_shares(instance)
    elif instance.status == Order.Status.CREDIT:
        # Credit sales are recognised now or at settlement, owner's choice.
        setting = CommissionSetting.load()
        entry_status = (
            CommissionEntry.Status.EARNED if setting.accrue_on_credit_order else CommissionEntry.Status.PENDING
        )
        share_status = (
            OrderSupplierShare.Status.EARNED if setting.accrue_on_credit_order else OrderSupplierShare.Status.PENDING
        )
        record_commission(instance, status=entry_status)
        record_supplier_shares(instance, status=share_status)
    elif instance.status == Order.Status.CANCELED:
        void_commission(instance)


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
