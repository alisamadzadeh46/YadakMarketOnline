from django.db.models import F
from rest_framework import permissions, viewsets
from rest_framework.response import Response

from .models import BlogCategory, Post
from .serializers import (
    BlogCategorySerializer,
    PostDetailSerializer,
    PostListSerializer,
)


class BlogCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BlogCategory.objects.all()
    serializer_class = BlogCategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class PostViewSet(viewsets.ReadOnlyModelViewSet):
    """Public blog: only published posts, newest first."""

    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        qs = Post.objects.filter(status=Post.Status.PUBLISHED).select_related("category", "author")
        params = self.request.query_params
        # Dynamic category filter (accepts slug or numeric id).
        category = params.get("category")
        if category:
            qs = qs.filter(category__id=category) if category.isdigit() else qs.filter(category__slug=category)
        search = params.get("search")
        if search:
            from django.db.models import Q

            qs = qs.filter(Q(title__icontains=search) | Q(body__icontains=search))
        # Whitelisted sort options for the blog toolbar.
        ordering = params.get("ordering")
        allowed = {"-published_at", "published_at", "-views", "views"}
        return qs.order_by(ordering if ordering in allowed else "-published_at")

    def get_serializer_class(self):
        return PostDetailSerializer if self.action == "retrieve" else PostListSerializer

    def retrieve(self, request, *args, **kwargs):
        """Count ONE view per unique visitor IP — refreshes and React's
        double-fired dev requests can never inflate the counter."""
        from .models import PostView

        instance = self.get_object()
        ip = (
            request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR")
            or "0.0.0.0"
        )
        _, first_visit = PostView.objects.get_or_create(post=instance, ip=ip)
        if first_visit:
            Post.objects.filter(pk=instance.pk).update(views=F("views") + 1)
            instance.refresh_from_db(fields=["views"])
        return Response(self.get_serializer(instance).data)
