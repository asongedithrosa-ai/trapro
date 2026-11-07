
"""
TRAPRO Legal Sources
====================

This module defines the SourceDocument model.

A SourceDocument represents an original legal or academic source uploaded
to TRAPRO. Examples include legislation, court judgments, OHADA instruments,
academic documents, and other materials used for terminology research.

The original file is preserved independently of the extraction process.
This allows the same source to be processed multiple times using different
extraction methods without losing the original document.
"""

import uuid
from pathlib import Path

from django.conf import settings
from django.db import models


def source_upload_path(instance, filename):
    """
    Determine the storage path for an uploaded legal source.

    Each source receives its own UUID-based directory. This reduces the
    likelihood of filename collisions and separates uploaded documents.

    Args:
        instance: The SourceDocument instance being saved.
        filename: The original filename supplied during upload.

    Returns:
        str: A relative storage path for the uploaded file.

    Note:
        The original filename is also stored separately in the database
        for display and source-identification purposes.
    """

    # Extract only the filename component to avoid retaining directory
    # components that may be present in an uploaded filename.
    safe_filename = Path(filename).name

    # Organize files by source UUID for easier storage management.
    return f"legal_sources/{instance.id}/{safe_filename}"


class SourceDocument(models.Model):
    """
    Store metadata and the original file for a legal source.

    This model is responsible for source identification and provenance.
    It does not perform text extraction itself.

    Extraction attempts are represented by ExtractionRun records in
    the extraction application.
    """

    class SourceType(models.TextChoices):
        """
        Classify the legal or academic nature of a source.

        These categories help distinguish national legislation,
        judicial decisions, regional instruments, and research materials.
        """

        LEGISLATION = "legislation", "Legislation"
        JUDGMENT = "judgment", "Judicial Decision"
        OHADA = "ohada", "OHADA Instrument"
        ACADEMIC = "academic", "Academic Document"
        OTHER = "other", "Other"

    class Language(models.TextChoices):
        """
        Identify the language or language combination of a source.

        English and French are the principal working languages for
        TRAPRO's initial Cameroon-focused terminology research.
        """

        ENGLISH = "en", "English"
        FRENCH = "fr", "French"
        BILINGUAL = "bi", "Bilingual"
        OTHER = "other", "Other"

    # UUIDs provide stable identifiers that are suitable for APIs and
    # distributed processing without exposing sequential database IDs.
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # Human-readable title of the source document.
    title = models.CharField(max_length=500)

    # Store the original uploaded file.
    # File storage is handled by Django's configured storage backend.
    original_file = models.FileField(
        upload_to=source_upload_path,
    )

    # Preserve the filename supplied by the uploader.
    original_filename = models.CharField(max_length=500)

    # Store the file extension for format detection and validation.
    # This value must not be treated as proof of the actual file format.
    file_extension = models.CharField(max_length=20)

    # Store the MIME type when it can be determined.
    # MIME type detection and validation will be implemented in the
    # upload service rather than relying only on the filename.
    mime_type = models.CharField(
        max_length=150,
        blank=True,
    )

    # Record the file size in bytes.
    # This supports upload limits and storage monitoring.
    file_size = models.PositiveBigIntegerField(
        help_text="File size in bytes.",
    )

    # SHA-256 checksum used for integrity verification and duplicate
    # detection. The checksum will be calculated by the upload service.
    sha256_checksum = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="SHA-256 checksum for file integrity and duplicate detection.",
    )

    # Classify the source according to its legal or academic nature.
    source_type = models.CharField(
        max_length=30,
        choices=SourceType.choices,
        default=SourceType.OTHER,
    )

    # Identify the language of the source document.
    language = models.CharField(
        max_length=10,
        choices=Language.choices,
        default=Language.OTHER,
    )

    # Identify the jurisdiction or legal system associated with the source.
    # Examples include Cameroon and OHADA.
    jurisdiction = models.CharField(
        max_length=150,
        blank=True,
    )

    # Preserve the official citation or legal reference when available.
    citation = models.CharField(
        max_length=500,
        blank=True,
    )

    # Optional notes about the document, its origin, or its relevance.
    description = models.TextField(blank=True)

    # Associate the source with the user who uploaded it.
    # SET_NULL preserves the source record if the user is later deleted.
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_legal_sources",
    )

    # Automatically record when the source was first created.
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # Automatically update the timestamp when source metadata changes.
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """
        Define default ordering and human-readable model names.
        """

        ordering = ["-uploaded_at"]
        verbose_name = "Legal Source Document"
        verbose_name_plural = "Legal Source Documents"

    def __str__(self):
        """
        Return the source title for Django admin and other displays.
        """

        return self.title
