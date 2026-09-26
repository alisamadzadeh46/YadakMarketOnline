"""Public slide list, newsletter subscribe, contact form + supplier CRUD."""

from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.accounts.permissions import IsSiteAdmin

from .models import ContactMessage, NewsletterSubscriber, Slide
from .serializers import SlideSerializer


class PublicSlideViewSet(viewsets.ReadOnlyModelViewSet):
    """Active slides for the home page hero."""

    queryset = Slide.objects.filter(is_active=True)
    serializer_class = SlideSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class ManageSlideViewSet(viewsets.ModelViewSet):
    """Supplier CRUD over all slides (multipart for image upload)."""

    queryset = Slide.objects.all()
    serializer_class = SlideSerializer
    permission_classes = [IsSiteAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = None


class NewsletterSubscribeView(APIView):
    """POST {email} — idempotent subscribe from the site footer."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        if not email or "@" not in email:
            return Response({"detail": "ایمیل معتبر نیست."}, status=400)
        obj, created = NewsletterSubscriber.objects.get_or_create(email=email)
        if not obj.is_active:
            obj.is_active = True
            obj.save(update_fields=["is_active"])
        # Re-subscribing is a success, not a failure — the address IS on the
        # list either way, so never phrase it like a rejection.
        return Response(
            {"detail": "عضویت شما در خبرنامه ثبت شد." if created else "این ایمیل از قبل در خبرنامه ثبت شده است ✓"},
            status=status.HTTP_201_CREATED if created else 200,
        )


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ("id", "name", "phone", "email", "subject", "message", "is_read", "created_at")
        read_only_fields = ("is_read", "created_at")


class ContactSubmitView(APIView):
    """Public contact-us form."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "پیام شما دریافت شد؛ به‌زودی پاسخ می‌دهیم."}, status=201)


class ManageContactViewSet(viewsets.ReadOnlyModelViewSet):
    """Supplier inbox for contact messages."""

    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [IsSiteAdmin]

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        msg = self.get_object()
        msg.is_read = True
        msg.save(update_fields=["is_read"])
        return Response(ContactMessageSerializer(msg).data)


class ManageSubscribersView(APIView):
    """Supplier view of newsletter subscribers (count + latest)."""

    permission_classes = [IsSiteAdmin]

    def get(self, request):
        qs = NewsletterSubscriber.objects.filter(is_active=True)
        return Response(
            {
                "count": qs.count(),
                "latest": list(qs.values("email", "created_at")[:50]),
            }
        )
