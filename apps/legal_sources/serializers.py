
"""
TRAPRO Legal Source API Serializers
===================================

This module validates incoming API data for legal source documents.

The serializer handles API-level validation. Actual file integrity,
duplicate detection, and storage remain the responsibility of the
legal source ingestion service.
"""

from rest_framework import serializers

from apps.legal_sources.models import SourceDocument


class SourceDocumentUploadSerializer(serializers.Serializer):
    """
    Validate metadata and file data submitted when uploading a source.

    The serializer deliberately does not save the document itself.
    The ingestion service handles document creation and file storage.
    """

    # Human-readable title of the legal or academic document.
    title = serializers.CharField(max_length=500)

    # Original file supplied by the user.
    original_file = serializers.FileField()

    # Classification of the legal or academic source.
    source_type = serializers.ChoiceField(
        choices=SourceDocument.SourceType.choices,
        default=SourceDocument.SourceType.OTHER,
    )

    # Language classification of the source document.
    language = serializers.ChoiceField(
        choices=SourceDocument.Language.choices,
        default=SourceDocument.Language.OTHER,
    )

    # Legal jurisdiction associated with the document.
    jurisdiction = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
        default="",
    )

    # Official legal citation or reference, when available.
    citation = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        default="",
    )

    # Additional information about the source.
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    # Explicitly allow a duplicate only when requested.
    allow_duplicate = serializers.BooleanField(default=False)
