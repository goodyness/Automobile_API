"""
Models for the CMS app.

Article   — a technical news post, case study, or update.
MediaItem — a gallery image representing a diagnostic procedure or repair.

Requirements: 15.1, 16.1, 17.1, 18.1, 18.4
"""

from django.db import models
from django.utils.text import slugify


class Article(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    body = models.TextField()
    author = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_at"]

    def __str__(self) -> str:
        return self.title


def generate_unique_slug(title: str) -> str:
    """
    Generate a unique slug from a title.
    If the base slug already exists, append a numeric suffix (1–999).
    Requirements: 18.4, Property 11
    """
    base_slug = slugify(title)
    slug = base_slug
    counter = 1
    while Article.objects.filter(slug=slug).exists():
        if counter > 999:
            raise ValueError("Could not generate a unique slug after 999 attempts.")
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


class MediaItem(models.Model):
    VISIBILITY_PUBLIC = "public"
    VISIBILITY_PRIVATE = "private"
    VISIBILITY_CHOICES = [
        (VISIBILITY_PUBLIC, "Public"),
        (VISIBILITY_PRIVATE, "Private"),
    ]

    article = models.ForeignKey(
        Article,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="media_items",
    )
    image = models.ImageField(upload_to="gallery/")
    caption = models.CharField(max_length=300, blank=True)
    visibility = models.CharField(
        max_length=10,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PUBLIC,
    )
    file_size = models.PositiveIntegerField(help_text="File size in bytes.")
    mime_type = models.CharField(max_length=50)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return f"MediaItem #{self.pk} ({self.visibility})"
