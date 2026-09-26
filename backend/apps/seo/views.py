"""SEO analysis endpoints (available to staff/supplier content editors)."""

from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsSupplierOrAdmin

from .analyzer import analyze


class SeoInputSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, default="")
    meta_title = serializers.CharField(required=False, allow_blank=True, default="")
    meta_description = serializers.CharField(required=False, allow_blank=True, default="")
    focus_keyword = serializers.CharField(required=False, allow_blank=True, default="")
    slug = serializers.CharField(required=False, allow_blank=True, default="")
    body = serializers.CharField(required=False, allow_blank=True, default="")


class SeoAnalyzeView(APIView):
    """POST content -> {score, rating, checks[], suggestions{}}."""

    permission_classes = [permissions.IsAuthenticated, IsSupplierOrAdmin]

    def post(self, request):
        serializer = SeoInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(analyze(**serializer.validated_data))
