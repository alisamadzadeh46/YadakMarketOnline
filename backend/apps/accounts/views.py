"""Account API endpoints: registration, current user, KYC profile, addresses."""

from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import Address, ShopkeeperProfile
from .permissions import IsOwnerOrReadOnly
from .serializers import (
    AddressSerializer,
    KYCDocumentSerializer,
    RegisterSerializer,
    ShopkeeperProfileSerializer,
    UserSerializer,
)


class RegisterView(generics.CreateAPIView):
    """Open endpoint for creating a new customer or shopkeeper account."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    """Return / update the authenticated user's own profile."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ShopkeeperProfileView(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    generics.GenericAPIView,
):
    """The shop submits and views its own KYC profile (one per user)."""

    serializer_class = ShopkeeperProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return ShopkeeperProfile.objects.filter(user=self.request.user).first()

    def get(self, request, *args, **kwargs):
        profile = self.get_object()
        if not profile:
            return Response(
                {"detail": "پروفایل فروشگاه ثبت نشده است."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(self.get_serializer(profile).data)

    def post(self, request, *args, **kwargs):
        if self.get_object():
            return Response(
                {"detail": "پروفایل قبلا ثبت شده است."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def patch(self, request, *args, **kwargs):
        profile = self.get_object()
        if not profile:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class KYCDocumentUploadView(generics.CreateAPIView):
    """Upload one KYC document; multipart so files stream straight to storage."""

    serializer_class = KYCDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        profile = ShopkeeperProfile.objects.filter(user=self.request.user).first()
        if not profile:
            profile = ShopkeeperProfile.objects.create(
                user=self.request.user, shop_name=self.request.user.full_name or "فروشگاه"
            )
        serializer.save(profile=profile)


class AddressViewSet(viewsets.ModelViewSet):
    """CRUD for the authenticated user's shipping addresses."""

    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        # Users only ever see their own addresses.
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
