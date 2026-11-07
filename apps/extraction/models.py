
"""
TRAPRO Document Extraction
==========================

This module defines the models responsible for recording document
extraction attempts and preserving their results.

The extraction application is deliberately separated from legal source
management. A single source document may have multiple extraction runs,
for example, a PDF text extraction followed by an OCR retry.

The models preserve:
    - Extraction method and processing status.
    - Extraction software and configuration.
    - Raw and normalized text.
    - Source-location information for extracted segments.
    - OCR confidence information where available.

These records provide the foundation for terminology candidate generation
and later human review.
"""

import uuid

from django.conf import settings
from django.db import models


class ExtractionRun(models.Model):
    """
    Represent one attempt to extract content from a source document.

    Each run records the method, processing status, software information,
    configuration, timestamps, and any error encountered.

    A new run should be created when the same source is processed again
    using a different method or configuration.
    """

    class ExtractionMethod(models.TextChoices):
        """
        Identify the extraction method used for a processing run.

        Additional methods can be introduced as new extraction adapters
        are implemented.
        """

        PDF_TEXT = "pdf_text", "PDF Text Extraction"
        OCR = "ocr", "Optical Character Recognition"
        SPREADSHEET = "spreadsheet", "Spreadsheet Extraction"
        CSV = "csv", "CSV Extraction"
        DOCX = "docx", "Word Document Extraction"
        PLAIN_TEXT = "plain_text", "Plain Text Extraction"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        """
        Represent the lifecycle of an extraction run.

        PARTIAL indicates that some content was extracted successfully,
        but the complete source could not be processed.
        """

        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        PARTIAL = "partial", "Partially Completed"
        FAILED = "failed", "Failed"

    # UUID provides a stable identifier for the extraction run.
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # Link the extraction attempt to its original legal source.
    # Multiple runs may be associated with the same source document.
    source_document = models.ForeignKey(
        "legal_sources.SourceDocument",
        on_delete=models.CASCADE,
        related_name="extraction_runs",
    )

    # Identify the extraction adapter used for this run.
    method = models.CharField(
        max_length=30,
        choices=ExtractionMethod.choices,
        default=ExtractionMethod.OTHER,
    )

    # Track the current processing state.
    # The extraction service will update this field during processing.
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    # Record the name of the extraction software or library.
    # Examples may include PyMuPDF, Tesseract, or another supported engine.
    software_name = models.CharField(
        max_length=150,
        blank=True,
    )

    # Record the software version to support reproducibility.
    software_version = models.CharField(
        max_length=100,
        blank=True,
    )

    # Preserve the configuration used for the extraction run.
    # JSON allows different extraction adapters to record different settings.
    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extraction settings used for this run.",
    )

    # Store diagnostic information when extraction fails or is incomplete.
    # Avoid placing secrets or sensitive credentials in this field.
    error_message = models.TextField(blank=True)

    # Identify the user who initiated the extraction run, when applicable.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="extraction_runs",
    )

    # Record when the extraction run was created.
    created_at = models.DateTimeField(auto_now_add=True)

    # Record when actual processing begins.
    # This is set by the extraction service.
    started_at = models.DateTimeField(null=True, blank=True)

    # Record when processing reaches a terminal state.
    # This is set by the extraction service.
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        """
        Define default ordering for extraction history.
        """

        ordering = ["-created_at"]

    def __str__(self):
        """
        Return a readable representation of the extraction run.
        """

        return f"{self.source_document.title} - {self.status}"


class ExtractedContent(models.Model):
    """
    Store the text produced by an extraction run.

    Raw text represents the initial output of the extraction engine.
    Normalized text represents the cleaned version used for downstream
    terminology processing.

    Keeping these values separate prevents normalization from destroying
    the original extraction result.
    """

    # UUID provides a stable identifier for the extracted content.
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # Each extraction run produces at most one main content record.
    # A OneToOneField prevents multiple main content records for the
    # same run. Individual pages or other units are stored as segments.
    extraction_run = models.OneToOneField(
        ExtractionRun,
        on_delete=models.CASCADE,
        related_name="extracted_content",
    )

    # Preserve the text exactly as initially returned by the extractor.
    raw_text = models.TextField(
        blank=True,
        help_text="Text as initially returned by the extraction engine.",
    )

    # Store cleaned text for terminology analysis.
    # Normalization rules will be implemented in a separate service.
    normalized_text = models.TextField(
        blank=True,
        help_text="Cleaned text used for terminology processing.",
    )

    # Store the language detected by the extraction or language-detection
    # process. This is separate from the source's declared language.
    detected_language = models.CharField(
        max_length=20,
        blank=True,
    )

    # Store basic statistics to support processing diagnostics.
    character_count = models.PositiveBigIntegerField(default=0)
    word_count = models.PositiveBigIntegerField(default=0)

    # Record when this content record was created.
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """
        Return a readable representation of the extracted content.
        """

        return f"Extracted content: {self.extraction_run}"


class ContentSegment(models.Model):
    """
    Represent a traceable portion of extracted content.

    A segment may correspond to a PDF page, paragraph, spreadsheet row,
    worksheet, table, image region, or another source structure.

    The locator field stores format-specific location metadata.
    This makes it possible to trace terminology contexts back to their
    original source locations.
    """

    class SegmentType(models.TextChoices):
        """
        Identify the structural type of a content segment.
        """

        PAGE = "page", "Page"
        PARAGRAPH = "paragraph", "Paragraph"
        TABLE = "table", "Table"
        ROW = "row", "Row"
        SHEET = "sheet", "Sheet"
        IMAGE_REGION = "image_region", "Image Region"
        SECTION = "section", "Section"
        OTHER = "other", "Other"

    # UUID provides a stable identifier for each segment.
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # Link the segment to the extracted content from which it originated.
    extracted_content = models.ForeignKey(
        ExtractedContent,
        on_delete=models.CASCADE,
        related_name="segments",
    )

    # Identify the structural type of this segment.
    segment_type = models.CharField(
        max_length=30,
        choices=SegmentType.choices,
        default=SegmentType.OTHER,
    )

    # Record the segment's position within the extracted content.
    # The extraction service is responsible for assigning this order.
    ordinal = models.PositiveIntegerField(
        help_text="Position of the segment within the source.",
    )

    # Store structured source-location information.
    #
    # Examples:
    # PDF: {"page_number": 14, "paragraph_number": 3}
    # Excel: {"sheet_name": "Contract Terms", "row_number": 12}
    # Image: {"image_number": 2, "region_number": 5}
    locator = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured source location information.",
    )

    # Preserve the text belonging to this segment.
    text = models.TextField()

    # Store OCR confidence when provided by the OCR engine.
    # The extraction service should validate that the value is between
    # 0 and 1 before saving it.
    confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="OCR confidence, if available, between 0 and 1.",
    )

    class Meta:
        """
        Define segment ordering and enforce unique positions.

        Each segment must have a unique ordinal within its extracted
        content record.
        """

        ordering = ["ordinal"]

        constraints = [
            models.UniqueConstraint(
                fields=["extracted_content", "ordinal"],
                name="unique_extracted_segment_order",
            ),
        ]

    def __str__(self):
        """
        Return a readable representation of the segment.
        """

        return f"{self.segment_type} {self.ordinal}"
