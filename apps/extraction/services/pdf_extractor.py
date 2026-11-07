
"""
TRAPRO PDF Extraction Service
=============================

This module extracts text from native, text-based PDF documents.

Each PDF page is represented as a separate extraction segment. Page
numbers are preserved in the locator metadata to support traceability
during terminology validation.

Scanned PDFs that contain no extractable text will require OCR, which
will be implemented as a separate extraction service.
"""

import pymupdf

from apps.extraction.services.base import (
    ExtractedSegment,
    ExtractionResult,
)


def extract_pdf(file_path: str) -> ExtractionResult:
    """
    Extract text and page-level segments from a PDF document.

    Args:
        file_path: Absolute or relative path to the source PDF.

    Returns:
        An ExtractionResult containing raw text, normalized text,
        page-level segments, and extraction software metadata.

    Raises:
        FileNotFoundError: If the specified PDF does not exist.
        pymupdf.FileDataError: If the file cannot be opened as a PDF.
        Exception: If an unexpected error occurs during extraction.
    """

    # Open the PDF using the modern PyMuPDF API.
    with pymupdf.open(file_path) as document:

        # Store extracted text and structural segments separately.
        page_texts: list[str] = []
        segments: list[ExtractedSegment] = []

        # Extract text from each page while preserving its page number.
        for page_number, page in enumerate(document, start=1):

            # Extract the page's text using PyMuPDF.
            page_text = page.get_text("text")

            # Preserve the page text for the complete document result.
            page_texts.append(page_text)

            # Create a traceable segment for the current page.
            segments.append(
                ExtractedSegment(
                    segment_type="page",
                    text=page_text,
                    locator={
                        "page_number": page_number,
                    },
                )
            )

        # Combine page text while retaining page boundaries.
        raw_text = "\n".join(page_texts)

        # Return the extraction result using the shared data structure.
        return ExtractionResult(
            raw_text=raw_text,
            normalized_text=raw_text,
            segments=segments,
            software_name="PyMuPDF",
            software_version=pymupdf.VersionBind,
            configuration={
                "extraction_mode": "native_text",
                "preserve_page_segments": True,
            },
        )
