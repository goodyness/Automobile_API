"""URL patterns for the CMS app."""

from django.urls import path

from apps.cms.views import (
    AdminMediaUploadView,
    AdminPublishArticleView,
    MediaListView,
    NewsDetailView,
    NewsListView,
)

# Public endpoints — mounted at /api/
urlpatterns = [
    path("news", NewsListView.as_view(), name="news-list"),
    path("news/<slug:slug>", NewsDetailView.as_view(), name="news-detail"),
    path("media", MediaListView.as_view(), name="media-list"),
]

# Admin-only endpoints — mounted at /api/admin/
admin_urlpatterns = [
    path("news", AdminPublishArticleView.as_view(), name="admin-news-create"),
    path("media/upload", AdminMediaUploadView.as_view(), name="admin-media-upload"),
]
