"""Keep denormalized product ratings in sync with approved reviews."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Review


@receiver(post_save, sender=Review)
@receiver(post_delete, sender=Review)
def update_product_rating(sender, instance, **kwargs):
    # Any create/update/delete of a review recomputes the parent's aggregates.
    instance.product.refresh_rating()
