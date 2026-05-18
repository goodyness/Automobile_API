"""Serializers for the CMS app."""

from rest_framework import serializers

from apps.cms.models import Article, MediaItem


class MediaItemSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = MediaItem
        fields = ["url", "caption", "uploaded_at"]

    def get_url(self, obj):
        request = self.context.get("request")
        if obj.image:
            url = obj.image.url
            return request.build_absolute_uri(url) if request else url
        return None


class ArticleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ["title", "slug", "author", "published_at"]


class ArticleDetailSerializer(serializers.ModelSerializer):
    media_items = MediaItemSerializer(many=True, read_only=True)

    class Meta:
        model = Article
        fields = ["title", "slug", "body", "author", "published_at", "media_items"]


class ArticleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ["id", "title", "slug", "body", "author", "published_at"]
        read_only_fields = ["id", "slug", "published_at"]

    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Title is required.")
        if len(value) > 200:
            raise serializers.ValidationError("Title must not exceed 200 characters.")
        return value

    def validate_body(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Body is required.")
        if len(value) > 50000:
            raise serializers.ValidationError("Body must not exceed 50,000 characters.")
        return value

    def validate_author(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Author is required.")
        if len(value) > 100:
            raise serializers.ValidationError("Author must not exceed 100 characters.")
        return value
