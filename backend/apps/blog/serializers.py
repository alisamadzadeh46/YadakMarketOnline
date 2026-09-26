from rest_framework import serializers

from .models import BlogCategory, Post


class BlogCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ("id", "name", "slug")


class PostListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    author_name = serializers.CharField(source="author.full_name", read_only=True)
    reading_time = serializers.IntegerField(read_only=True)

    class Meta:
        model = Post
        fields = (
            "id",
            "title",
            "slug",
            "category_name",
            "author_name",
            "cover",
            "excerpt",
            "reading_time",
            "views",
            "published_at",
        )


class PostDetailSerializer(PostListSerializer):
    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + (
            "body",
            "meta_title",
            "meta_description",
            "focus_keyword",
            "seo_score",
        )
