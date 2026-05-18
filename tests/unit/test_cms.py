"""
Unit tests for CMS endpoints.
Requirements: 15.1–15.3, 16.1–16.2, 17.1–17.2, 18.1–18.5, 19.1–19.6
"""

import io

import pytest
from django.utils import timezone

from apps.cms.models import Article, MediaItem

NEWS_URL = "/api/news"
MEDIA_URL = "/api/media"
ADMIN_NEWS_URL = "/api/admin/news"
ADMIN_MEDIA_URL = "/api/admin/media/upload"


@pytest.fixture
def published_article(db):
    return Article.objects.create(
        title="ECU Repair Guide",
        slug="ecu-repair-guide",
        body="Full body text here.",
        author="Tech Team",
        status=Article.STATUS_PUBLISHED,
        published_at=timezone.now(),
    )


@pytest.fixture
def draft_article(db):
    return Article.objects.create(
        title="Draft Post",
        slug="draft-post",
        body="Draft body.",
        author="Tech Team",
        status=Article.STATUS_DRAFT,
    )


# ---------------------------------------------------------------------------
# News List (Requirement 15)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestNewsList:
    def test_returns_published_articles(self, api_client, published_article):
        res = api_client.get(NEWS_URL)
        assert res.status_code == 200
        assert res.data["count"] >= 1

    def test_draft_excluded(self, api_client, draft_article):
        res = api_client.get(NEWS_URL)
        slugs = [a["slug"] for a in res.data["results"]]
        assert draft_article.slug not in slugs

    def test_empty_list_returns_200(self, api_client):
        res = api_client.get(NEWS_URL)
        assert res.status_code == 200
        assert "results" in res.data


# ---------------------------------------------------------------------------
# Article Detail (Requirement 16)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestArticleDetail:
    def test_valid_slug_returns_200(self, api_client, published_article):
        res = api_client.get(f"{NEWS_URL}/{published_article.slug}")
        assert res.status_code == 200
        assert res.data["title"] == published_article.title

    def test_draft_slug_returns_404(self, api_client, draft_article):
        res = api_client.get(f"{NEWS_URL}/{draft_article.slug}")
        assert res.status_code == 404

    def test_missing_slug_returns_404(self, api_client):
        res = api_client.get(f"{NEWS_URL}/nonexistent-slug")
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# Media Gallery (Requirement 17)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMediaGallery:
    def test_returns_public_items(self, api_client):
        res = api_client.get(MEDIA_URL)
        assert res.status_code == 200
        assert "results" in res.data

    def test_empty_gallery_returns_200(self, api_client):
        res = api_client.get(MEDIA_URL)
        assert res.status_code == 200


# ---------------------------------------------------------------------------
# Admin Publish Article (Requirement 18)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAdminPublishArticle:
    PAYLOAD = {
        "title": "FBS-4 Sync Guide",
        "body": "Full body content here.",
        "author": "Tech Team",
    }

    def test_admin_can_publish(self, admin_client):
        res = admin_client.post(ADMIN_NEWS_URL, self.PAYLOAD, format="json")
        assert res.status_code == 201
        assert "slug" in res.data
        assert res.data["slug"] != ""

    def test_non_admin_gets_403(self, auth_client):
        res = auth_client.post(ADMIN_NEWS_URL, self.PAYLOAD, format="json")
        assert res.status_code == 403

    def test_unauthenticated_gets_401(self, api_client):
        res = api_client.post(ADMIN_NEWS_URL, self.PAYLOAD, format="json")
        assert res.status_code == 401

    def test_missing_title_returns_400(self, admin_client):
        res = admin_client.post(ADMIN_NEWS_URL, {"body": "x", "author": "y"}, format="json")
        assert res.status_code == 400

    def test_slug_collision_gets_suffix(self, admin_client):
        admin_client.post(ADMIN_NEWS_URL, self.PAYLOAD, format="json")
        res = admin_client.post(ADMIN_NEWS_URL, {**self.PAYLOAD, "title": "FBS-4 Sync Guide"}, format="json")
        assert res.status_code == 201
        assert res.data["slug"] != "fbs-4-sync-guide"
        assert res.data["slug"].startswith("fbs-4-sync-guide")


# ---------------------------------------------------------------------------
# Admin Media Upload (Requirement 19)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAdminMediaUpload:
    def _make_image(self, name="test.jpg", content_type="image/jpeg", size=1024):
        """Create a minimal in-memory image file."""
        from PIL import Image
        img = Image.new("RGB", (10, 10), color="red")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        buf.name = name
        buf.content_type = content_type
        return buf

    def test_admin_can_upload_image(self, admin_client):
        img = self._make_image()
        res = admin_client.post(
            ADMIN_MEDIA_URL,
            {"file": img, "caption": "Test image"},
            format="multipart",
        )
        assert res.status_code == 201
        assert "url" in res.data

    def test_non_admin_gets_403(self, auth_client):
        img = self._make_image()
        res = auth_client.post(ADMIN_MEDIA_URL, {"file": img}, format="multipart")
        assert res.status_code == 403

    def test_unauthenticated_gets_401(self, api_client):
        img = self._make_image()
        res = api_client.post(ADMIN_MEDIA_URL, {"file": img}, format="multipart")
        assert res.status_code == 401

    def test_no_file_returns_400(self, admin_client):
        res = admin_client.post(ADMIN_MEDIA_URL, {}, format="multipart")
        assert res.status_code == 400

    def test_wrong_file_type_returns_400(self, admin_client):
        txt = io.BytesIO(b"not an image")
        txt.name = "file.txt"
        txt.content_type = "text/plain"
        res = admin_client.post(ADMIN_MEDIA_URL, {"file": txt}, format="multipart")
        assert res.status_code == 400
