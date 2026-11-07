"""
TRAPRO Extraction API Serializers
=================================

This module defines read-only serializers for presenting extraction
results through the REST API.

The serializers expose:
    1. Extraction run metadata.
    2. Metadata about the original legal source document.
    3. Extracted raw and normalized text.
    4. Ordered content segments and their source locators.

Internal exception messages are deliberately excluded from API responses.
"""

from rest_framework import serializers

from apps.extraction.models import (
    ContentSegment,
    ExtractedContent,
    ExtractionRun,
)


class ContentSegmentSerializer(serializers.ModelSerializer):
    """
    Serialize an individual segment produced during document extraction.

    Each segment retains its ordinal position and locator so that the
    extracted text can be traced back to its original document location.
    """

    class Meta:
        model = ContentSegment

        fields = [
            "id",
            "segment_type",
            "ordinal",
            "locator",
            "text",
            "confidence",
        ]

        # Extraction results are read-only through this serializer.
        read_only_fields = fields


class ExtractedContentSerializer(serializers.ModelSerializer):
    """
    Serialize the extracted text and its associated content segments.

    Segments are returned in the ordering defined by the ContentSegment
    model, preserving the original extraction sequence.
    """

    # Include all segments associated with this extracted content.
    segments = ContentSegmentSerializer(many=True, read_only=True)

    class Meta:
        model = ExtractedContent

        fields = [
            "id",
            "raw_text",
            "normalized_text",
            "detected_language",
            "character_count",
            "word_count",
            "created_at",
            "segments",
        ]

        # Extracted content cannot be modified through this endpoint.
        read_only_fields = fields


class ExtractionRunDetailSerializer(serializers.ModelSerializer):
    """
    Serialize a complete extraction run and its resulting content.

    Source document fields are exposed as read-only metadata rather than
    returning the original uploaded file or its internal storage path.

    Failed extraction runs may not have an ExtractedContent record.
    In that case, extracted_content is returned as null.
    """

    # Expose selected source document metadata.
    source_id = serializers.UUIDField(
        source="source_document.id",
        read_only=True,
    )

    source_title = serializers.CharField(
        source="source_document.title",
        read_only=True,
    )

    source_original_filename = serializers.CharField(
        source="source_document.original_filename",
        read_only=True,
    )

    source_language = serializers.CharField(
        source="source_document.language",
        read_only=True,
    )

    source_jurisdiction = serializers.CharField(
        source="source_document.jurisdiction",
        read_only=True,
    )

    # Use a method field to safely handle runs without extracted content.
    extracted_content = serializers.SerializerMethodField()

    class Meta:
        model = ExtractionRun

        fields = [
            "id",
            "source_id",
            "source_title",
            "source_original_filename",
            "source_language",
            "source_jurisdiction",
            "method",
            "status",
            "software_name",
            "software_version",
            "configuration",
            "created_at",
            "started_at",
            "completed_at",
            "extracted_content",
        ]

        # All fields in this detail response are read-only.
        read_only_fields = fields

    def get_extracted_content(self, obj):
        """
        Return serialized content when extraction produced a result.

        A failed extraction may have no related ExtractedContent object.
        Return None instead of allowing that missing relation to cause
        an API error.
        """

        try:
            content = obj.extracted_content
        except ExtractedContent.DoesNotExist:
            return None

        return ExtractedContentSerializer(
            content,
            context=self.context,
        ).data
