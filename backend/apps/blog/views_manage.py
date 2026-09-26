"""Supplier-facing blog CRUD with automatic SEO scoring on every save."""

import uuid

from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsSiteAdmin
from apps.seo.analyzer import analyze

from .models import BlogCategory, Post
from .tasks import notify_subscribers


class PostWriteSerializer(serializers.ModelSerializer):
    seo_score = serializers.IntegerField(read_only=True)

    class Meta:
        model = Post
        fields = (
            "id",
            "title",
            "slug",
            "category",
            "cover",
            "excerpt",
            "body",
            "status",
            "published_at",
            "focus_keyword",
            "meta_title",
            "meta_description",
            "seo_score",
            "views",
            "created_at",
        )
        read_only_fields = ("views", "created_at")
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}

    def _score(self, instance):
        result = analyze(
            title=instance.title,
            meta_title=instance.meta_title,
            meta_description=instance.meta_description,
            focus_keyword=instance.focus_keyword,
            slug=instance.slug,
            body=instance.body,
        )
        instance.seo_score = result["score"]

    def _finalize(self, instance, was_published):
        """Set publish timestamp, refresh the SEO score and notify subscribers
        exactly once on the draft -> published transition."""
        just_published = instance.status == Post.Status.PUBLISHED and not was_published
        if just_published and not instance.published_at:
            instance.published_at = timezone.now()
        self._score(instance)
        instance.save()
        if just_published:
            notify_subscribers.delay(instance.id)
        return instance

    def create(self, validated_data):
        validated_data.setdefault("author", self.context["request"].user)
        instance = super().create(validated_data)
        return self._finalize(instance, was_published=False)

    def update(self, instance, validated_data):
        was_published = bool(instance.published_at)
        instance = super().update(instance, validated_data)
        return self._finalize(instance, was_published=was_published)


class ManagePostViewSet(viewsets.ModelViewSet):
    """CRUD over all posts (draft + published) for the content editor."""

    queryset = Post.objects.all().select_related("category")
    serializer_class = PostWriteSerializer
    permission_classes = [IsSiteAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]


class MediaUploadView(APIView):
    """Editor media upload: POST multipart {file} -> {url}.

    Used by the rich-text editor for inline images/videos in post bodies.
    """

    permission_classes = [IsSiteAdmin]
    parser_classes = [MultiPartParser, FormParser]

    ALLOWED = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".webm"}
    MAX_BYTES = 20 * 1024 * 1024  # 20 MB

    def post(self, request):
        f = request.FILES.get("file")
        if not f:
            return Response({"detail": "فایلی ارسال نشده است."}, status=400)
        ext = ("." + f.name.rsplit(".", 1)[-1].lower()) if "." in f.name else ""
        if ext not in self.ALLOWED:
            return Response({"detail": "فرمت فایل مجاز نیست."}, status=400)
        if f.size > self.MAX_BYTES:
            return Response({"detail": "حجم فایل بیش از حد مجاز (۲۰MB) است."}, status=400)
        path = default_storage.save(f"blog/uploads/{uuid.uuid4().hex}{ext}", f)
        return Response(
            {
                "url": request.build_absolute_uri(default_storage.url(path)),
                "is_video": ext in {".mp4", ".webm"},
            },
            status=201,
        )


class BlogCategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ("id", "name", "slug")
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}


class ManageBlogCategoryViewSet(viewsets.ModelViewSet):
    queryset = BlogCategory.objects.all()
    serializer_class = BlogCategoryWriteSerializer
    permission_classes = [IsSiteAdmin]
    pagination_class = None
