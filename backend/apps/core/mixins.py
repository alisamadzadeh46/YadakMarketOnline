"""Reusable view mixins."""

from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.response import Response


class ProtectedDeleteMixin:
    """Answer 409 instead of a server error when a row is still referenced.

    Brands and categories are ``PROTECT``-ed by their products: deleting one
    that is still in use raises ``ProtectedError``, which DRF does not handle
    and turns into an HTTP 500. The panel needs a clear, actionable message.
    """

    protected_delete_message = "این مورد هنوز در جای دیگری استفاده شده و قابل حذف نیست."

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError as exc:
            in_use = len({obj.pk for obj in exc.protected_objects})
            return Response(
                {"detail": self.protected_delete_message, "in_use": in_use},
                status=status.HTTP_409_CONFLICT,
            )
