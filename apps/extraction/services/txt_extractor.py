"""
Plain-text extraction service for TRAPRO.

Preserves paragraph boundaries and line-level provenance
while extracting text from UTF-8 and common legacy encodings.
"""

import platform
from pathlib import Path

from apps.extraction.services.base import (
    ExtractedSegment,
    ExtractionResult,
)


def _decode_text_file(file_path):
    """
    Decode a text file using common encodings.

    UTF-8 with BOM is checked first, followed by UTF-8,
    Windows-1252, and Latin-1.
    """

    raw_bytes = Path(file_path).read_bytes()

    encodings = [
        "utf-8-sig",
        "utf-8",
        "cp1252",
        "latin-1",
    ]

    for encoding in encodings:
        try:
            return raw_bytes.decode(encoding), encoding
        except UnicodeDecodeError:
            continue

    # Latin-1 can decode every possible byte value.
    # This fallback is retained for defensive completeness.
    return raw_bytes.decode("latin-1"), "latin-1"


def extract_txt(file_path):
    """
    Extract plain text while preserving paragraph boundaries.

    Consecutive non-empty lines belong to the same paragraph.
    Blank lines separate paragraphs.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Text file not found: {file_path}"
        )

    if path.suffix.lower() != ".txt":
        raise ValueError(
            f"Unsupported text file extension: {path.suffix}"
        )

    raw_text, encoding = _decode_text_file(path)

    # Standardise Windows and old Mac line endings.
    normalised_source = raw_text.replace(
        "\r\n", "\n"
    ).replace("\r", "\n")

    lines = normalised_source.split("\n")

    segments = []
    paragraph_parts = []
    paragraph_start_line = None
    paragraph_number = 0

    def save_paragraph(end_line):
        """Save the current paragraph as an extraction segment."""

        nonlocal paragraph_number

        if not paragraph_parts:
            return

        paragraph_number += 1

        paragraph_text = "\n".join(paragraph_parts)

        segments.append(
            ExtractedSegment(
                segment_type="paragraph",
                text=paragraph_text,
                locator={
                    "paragraph_number": paragraph_number,
                    "start_line": paragraph_start_line,
                    "end_line": end_line,
                },
            )
        )

        paragraph_parts.clear()

    for line_number, line in enumerate(lines, start=1):

        if line.strip():
            if paragraph_start_line is None:
                paragraph_start_line = line_number

            paragraph_parts.append(line.strip())

        else:
            save_paragraph(line_number - 1)
            paragraph_start_line = None

    # Save the final paragraph if the file does not end
    # with a blank line.
    save_paragraph(len(lines))

    normalized_text = "\n\n".join(
        segment.text for segment in segments
    )

    return ExtractionResult(
        raw_text=raw_text,
        normalized_text=normalized_text,
        segments=segments,
        software_name="Python Standard Library",
        software_version=platform.python_version(),
        configuration={
            "file_format": "txt",
            "encoding": encoding,
            "preserve_paragraphs": True,
            "preserve_line_numbers": True,
            "newline_normalization": True,
        },
    )