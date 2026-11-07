
"""
TRAPRO Shared Extraction Pipeline
=================================

This module coordinates file extraction and database persistence.

Responsibilities:
    1. Identify the source document's file format.
    2. Create an ExtractionRun record.
    3. Dispatch the source file to the correct extractor.
    4. Store the extracted text and metadata.
    5. Store traceable page, row, and worksheet segments.
    6. Record successful, partial, and failed extraction outcomes.

The original SourceDocument and its uploaded file are never modified
or deleted by this pipeline.

Supported formats:
    - PDF
    - XLSX
    - XLS
    - CSV
    - DOCX
    - TXT

Other formats will be supported as their extraction services
are implemented.
"""

import logging

from pathlib import Path

from django.db import transaction
from django.utils import timezone

from apps.extraction.models import (
    ExtractionRun,
    ExtractedContent,
    ContentSegment,
)

from apps.extraction.services.pdf_extractor import extract_pdf
from apps.extraction.services.excel_extractor import extract_excel
from apps.extraction.services.csv_extractor import extract_csv
from apps.extraction.services.docx_extractor import extract_docx
from apps.extraction.services.txt_extractor import extract_txt


# Configure a module-level logger for extraction events.
logger = logging.getLogger(__name__)


# Map supported file extensions to their extraction methods.
EXTRACTION_METHODS = {
    ".pdf": "pdf_text",
    ".xlsx": "spreadsheet",
    ".xls": "spreadsheet",
    ".csv": "csv",
    ".docx": "docx",
    ".txt": "plain_text",
}


# Map supported file extensions to their extraction functions.
EXTRACTORS = {
    ".pdf": extract_pdf,
    ".xlsx": extract_excel,
    ".xls": extract_excel,
    ".csv": extract_csv,
    ".docx": extract_docx,
    ".txt": extract_txt,
}


def _get_source_extension(source_document) -> str:
    """
    Determine the source document's file extension.

    The original filename is preferred because it represents the
    name supplied during ingestion.

    Returns:
        A lowercase extension such as '.pdf' or '.xlsx'.
    """

    # Prefer the original filename recorded during ingestion.
    original_filename = (
        source_document.original_filename
        or source_document.original_file.name
    )

    # Extract and normalize the file extension.
    return Path(original_filename).suffix.lower()


def _get_source_file_path(source_document) -> str:
    """
    Retrieve the local filesystem path of the uploaded source file.

    The current implementation assumes Django's local file storage.

    If TRAPRO later uses remote storage, this function will need to
    be adapted to provide a temporary local file for extraction.
    """

    # Obtain the path from Django's FileField.
    return source_document.original_file.path


def run_extraction(
    source_document,
    *,
    created_by=None,
) -> ExtractionRun:
    """
    Run extraction for an existing SourceDocument.

    Args:
        source_document:
            An existing SourceDocument database instance.

        created_by:
            Optional Django user who initiated the extraction.

    Returns:
        ExtractionRun:
            The database record representing the completed extraction.

    Raises:
        ValueError:
            If the file format is unsupported.

        Exception:
            If extraction fails. The failed ExtractionRun is retained
            in the database before the exception is re-raised.
    """

    # Identify the file format before creating the extraction run.
    extension = _get_source_extension(source_document)

    # Retrieve the extraction method for the file format.
    extraction_method = EXTRACTION_METHODS.get(extension)

    # Retrieve the extraction service for the file format.
    extractor = EXTRACTORS.get(extension)

    # Record unsupported formats as failed extraction attempts.
    if extraction_method is None or extractor is None:

        # Create a failed run so unsupported attempts are traceable.
        failed_run = ExtractionRun.objects.create(
            source_document=source_document,
            method="other",
            status="failed",
            error_message=(
                f"Unsupported extraction format: {extension}"
            ),
            created_by=created_by,
            started_at=timezone.now(),
            completed_at=timezone.now(),
        )

        # Raise a clear error for the calling application.
        raise ValueError(
            f"Unsupported extraction format: {extension}. "
            "Supported formats are PDF, XLSX, XLS, CSV, DOCX, and TXT."
        )

    # Create the extraction run before processing the source file.
    extraction_run = ExtractionRun.objects.create(
        source_document=source_document,
        method=extraction_method,
        status="processing",
        created_by=created_by,
        started_at=timezone.now(),
    )

    try:
        # Retrieve the original uploaded file's local path.
        file_path = _get_source_file_path(source_document)

        # Execute the format-specific extraction service.
        extraction_result = extractor(file_path)

        # Determine the extraction outcome.
        if extraction_result.normalized_text.strip():
            extraction_status = "completed"
        else:
            # A successful extraction with no readable text is partial.
            extraction_status = "partial"

        # Persist the extracted content and its segments atomically.
        with transaction.atomic():

            # Create the extracted-content record.
            extracted_content = ExtractedContent.objects.create(
                extraction_run=extraction_run,
                raw_text=extraction_result.raw_text,
                normalized_text=extraction_result.normalized_text,
                detected_language=(
                    extraction_result.detected_language
                ),
                character_count=extraction_result.character_count,
                word_count=extraction_result.word_count,
            )

            # Prepare database objects for all extracted segments.
            content_segments = []

            for ordinal, extracted_segment in enumerate(
                extraction_result.segments,
                start=1,
            ):

                # Create a ContentSegment without saving individually.
                content_segments.append(
                    ContentSegment(
                        extracted_content=extracted_content,
                        segment_type=(
                            extracted_segment.segment_type
                        ),
                        ordinal=ordinal,
                        locator=extracted_segment.locator,
                        text=extracted_segment.text,
                        confidence=extracted_segment.confidence,
                    )
                )

            # Save all segments efficiently in a single operation.
            if content_segments:
                ContentSegment.objects.bulk_create(
                    content_segments
                )

            # Update the extraction run with software metadata.
            extraction_run.software_name = (
                extraction_result.software_name
            )

            extraction_run.software_version = (
                extraction_result.software_version
            )

            extraction_run.configuration = (
                extraction_result.configuration
            )

            # Record the final extraction status.
            extraction_run.status = extraction_status

            # Record when processing finished.
            extraction_run.completed_at = timezone.now()

            # Persist the completed extraction run.
            extraction_run.save(
                update_fields=[
                    "software_name",
                    "software_version",
                    "configuration",
                    "status",
                    "completed_at",
                ]
            )

        # Log successful extraction for operational monitoring.
        logger.info(
            "Extraction completed for source %s using %s.",
            source_document.pk,
            extraction_method,
        )

        # Return the database record to the calling application.
        return extraction_run

    except Exception as exc:

        # Record the extraction failure without deleting the source.
        extraction_run.status = "failed"

        # Store a readable error message for troubleshooting.
        extraction_run.error_message = str(exc)

        # Record when the failed attempt ended.
        extraction_run.completed_at = timezone.now()

        # Persist the failure details.
        extraction_run.save(
            update_fields=[
                "status",
                "error_message",
                "completed_at",
            ]
        )

        # Log the exception with its traceback.
        logger.exception(
            "Extraction failed for source %s.",
            source_document.pk,
        )

        # Re-raise the original exception for the caller to handle.
        raise
