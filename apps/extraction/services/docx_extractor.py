
"""
TRAPRO DOCX Extractor
=====================

Extracts structured text from Microsoft Word (.docx) documents.

Preserves:
    - Paragraphs and their original order.
    - Heading styles and hierarchy.
    - Tables, rows, and cells.
    - Document block positions.
    - Extraction metadata.

Paragraphs and tables are traversed in their original document
order to preserve the structure of legal documents.
"""

from pathlib import Path

import docx
from docx import Document

from apps.extraction.services.base import (
    ExtractedSegment,
    ExtractionResult,
)


def _get_document_blocks(document):
    """
    Yield paragraphs and tables in their original document order.

    The python-docx high-level API exposes paragraphs and tables
    separately. The underlying XML is used here to preserve
    their interleaved order.
    """

    from docx.oxml.text.paragraph import CT_P
    from docx.oxml.table import CT_Tbl
    from docx.text.paragraph import Paragraph
    from docx.table import Table

    body = document.element.body

    for child in body.iterchildren():

        if isinstance(child, CT_P):
            yield "paragraph", Paragraph(child, document)

        elif isinstance(child, CT_Tbl):
            yield "table", Table(child, document)


def extract_docx(file_path):
    """
    Extract structured content from a DOCX document.

    Args:
        file_path: Path to the original DOCX file.

    Returns:
        ExtractionResult containing text, segments,
        and extraction metadata.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"DOCX file not found: {file_path}"
        )

    if file_path.suffix.lower() != ".docx":
        raise ValueError(
            "DOCX extractor only supports .docx files."
        )

    document = Document(str(file_path))

    raw_text_parts = []
    normalized_text_parts = []
    segments = []

    paragraph_count = 0
    table_count = 0

    for block_index, (block_type, block) in enumerate(
        _get_document_blocks(document),
        start=1,
    ):

        # --------------------------------------------------
        # Paragraph extraction
        # --------------------------------------------------

        if block_type == "paragraph":

            text = block.text.strip()

            if not text:
                continue

            paragraph_count += 1

            style_name = (
                block.style.name
                if block.style is not None
                else "Normal"
            )

            heading_level = None

            if style_name.lower().startswith("heading"):
                heading_level = style_name

            locator = {
                "block_index": block_index,
                "paragraph_number": paragraph_count,
                "style": style_name,
                "heading_level": heading_level,
            }

            segments.append(
                ExtractedSegment(
                    segment_type="paragraph",
                    text=text,
                    locator=locator,
                )
            )

            raw_text_parts.append(text)
            normalized_text_parts.append(text)

        # --------------------------------------------------
        # Table extraction
        # --------------------------------------------------

        elif block_type == "table":

            table_count += 1

            table_text_parts = []

            for row_index, row in enumerate(
                block.rows,
                start=1,
            ):

                cell_values = []

                for cell in row.cells:

                    cell_text = " ".join(
                        paragraph.text.strip()
                        for paragraph in cell.paragraphs
                        if paragraph.text.strip()
                    )

                    cell_values.append(cell_text)

                row_text = " | ".join(cell_values)

                if row_text.strip():

                    table_text_parts.append(row_text)

                    segments.append(
                        ExtractedSegment(
                            segment_type="row",
                            text=row_text,
                            locator={
                                "block_index": block_index,
                                "table_number": table_count,
                                "row_number": row_index,
                                "cells": cell_values,
                            },
                        )
                    )

            if table_text_parts:

                table_text = "\n".join(table_text_parts)

                raw_text_parts.append(table_text)
                normalized_text_parts.append(table_text)

                segments.append(
                    ExtractedSegment(
                        segment_type="table",
                        text=table_text,
                        locator={
                            "block_index": block_index,
                            "table_number": table_count,
                            "row_count": len(table_text_parts),
                        },
                    )
                )

    raw_text = "\n\n".join(raw_text_parts)

    normalized_text = "\n\n".join(
        part.strip()
        for part in normalized_text_parts
        if part.strip()
    )

    return ExtractionResult(
        raw_text=raw_text,
        normalized_text=normalized_text,
        segments=segments,
        software_name="python-docx",
        software_version=docx.__version__,
        configuration={
            "file_format": "docx",
            "preserve_paragraphs": True,
            "preserve_heading_styles": True,
            "preserve_tables": True,
            "preserve_document_order": True,
            "paragraph_count": paragraph_count,
            "table_count": table_count,
        },
    )
