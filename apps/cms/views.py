"""
Views for the CMS app.

Endpoints:
  GET  /api/news                  — Requirement 15
  GET  /api/news/:slug            — Requirement 16
  GET  /api/media                 — Requirement 17
  POST /api/admin/news            — Requirement 18
  POST /api/admin/media/upload    — Requirement 19
"""

import os

from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cms.models import Article, MediaItem, generate_unique_slug
from apps.cms.serializers import (
    ArticleCreateSerializer,
    ArticleDetailSerializer,
    ArticleListSerializer,
    MediaItemSerializer,
)
from core.pagination import StandardPagination
from core.permissions import IsAdminUser
from core.validators import validate_image_file


class NewsListView(generics.ListAPIView):
    """GET /api/news — Requirements 15.1–15.3"""

    serializer_class = ArticleListSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    def get_queryset(self):
        return Article.objects.filter(status=Article.STATUS_PUBLISHED).order_by("-published_at")


class NewsDetailView(generics.RetrieveAPIView):
    """GET /api/news/:slug — Requirements 16.1–16.2"""

    serializer_class = ArticleDetailSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        slug = self.kwargs.get("slug")
        try:
            return Article.objects.prefetch_related("media_items").get(
                slug=slug, status=Article.STATUS_PUBLISHED
            )
        except Article.DoesNotExist:
            raise NotFound(f"Article with slug '{slug}' not found.")


class MediaListView(generics.ListAPIView):
    """GET /api/media — Requirements 17.1–17.2"""

    serializer_class = MediaItemSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    def get_queryset(self):
        return MediaItem.objects.filter(
            visibility=MediaItem.VISIBILITY_PUBLIC
        ).order_by("-uploaded_at")


class AdminPublishArticleView(APIView):
    """POST /api/admin/news — Requirements 18.1–18.5"""

    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        serializer = ArticleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        title = serializer.validated_data["title"]
        slug = generate_unique_slug(title)

        article = Article.objects.create(
            title=title,
            slug=slug,
            body=serializer.validated_data["body"],
            author=serializer.validated_data["author"],
            status=Article.STATUS_PUBLISHED,
            published_at=timezone.now(),
        )

        return Response(
            ArticleCreateSerializer(article).data,
            status=status.HTTP_201_CREATED,
        )


class AdminMediaUploadView(APIView):
    """POST /api/admin/media/upload — Requirements 19.1–19.6"""

    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        file = request.FILES.get("file")
        if not file:
            return Response(
                {"detail": "A file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate file type and size
        try:
            validate_image_file(file)
        except Exception as exc:
            detail = exc.detail if hasattr(exc, "detail") else str(exc)
            if isinstance(detail, list):
                detail = detail[0]
            return Response({"detail": str(detail)}, status=status.HTTP_400_BAD_REQUEST)

        caption = request.data.get("caption", "")
        visibility = request.data.get("visibility", MediaItem.VISIBILITY_PUBLIC)
        if visibility not in (MediaItem.VISIBILITY_PUBLIC, MediaItem.VISIBILITY_PRIVATE):
            visibility = MediaItem.VISIBILITY_PUBLIC

        media_item = MediaItem.objects.create(
            image=file,
            caption=caption,
            visibility=visibility,
            file_size=file.size,
            mime_type=file.content_type,
        )

        url = request.build_absolute_uri(media_item.image.url)
        return Response(
            {
                "url": url,
                "filename": os.path.basename(media_item.image.name),
                "file_size": media_item.file_size,
                "mime_type": media_item.mime_type,
                "uploaded_at": media_item.uploaded_at,
            },
            status=status.HTTP_201_CREATED,
        )
