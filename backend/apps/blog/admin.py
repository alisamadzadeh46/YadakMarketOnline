"""Blog admin with an inline SEO score computed from the Yoast-like analyzer."""

from django.contrib import admin
from django.utils import timezone

from apps.seo.analyzer import analyze

from .models import BlogCategory, Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "seo_score", "views", "published_at")
    list_filter = ("status", "category")
    search_fields = ("title", "body")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("seo_score", "views")
    fieldsets = (
        (
            None,
            {"fields": ("title", "slug", "category", "author", "cover", "excerpt", "body", "status", "published_at")},
        ),
        ("سئو", {"fields": ("focus_keyword", "meta_title", "meta_description", "seo_score")}),
    )

    def save_model(self, request, obj, form, change):
        if obj.author_id is None:
            obj.author = request.user
        if obj.status == Post.Status.PUBLISHED and not obj.published_at:
            obj.published_at = timezone.now()
        # Recompute the SEO score every save so editors get instant feedback.
        result = analyze(
            title=obj.title,
            meta_title=obj.meta_title,
            meta_description=obj.meta_description,
            focus_keyword=obj.focus_keyword,
            slug=obj.slug,
            body=obj.body,
        )
        obj.seo_score = result["score"]
        super().save_model(request, obj, form, change)


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
