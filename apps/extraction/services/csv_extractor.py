
"""
TRAPRO CSV Extraction Service
=============================

This module extracts structured content from CSV files.

CSV files are commonly used to export terminology research data,
including AntConc word lists, n-grams, clusters, and concordance
(KWIC) results.

The extractor preserves:
    - Original CSV text.
    - Detected text encoding.
    - Detected delimiter.
    - Header rows.
    - Data row positions.
    - Column positions.
    - Row-level extraction segments.

Important:
    CSV is a text format. It does not contain Excel formulas,
    worksheets, formatting, or calculated values as native features.
"""

import csv
import io
from pathlib import Path
from typing import Any

from apps.extraction.services.base import (
    ExtractedSegment,
    ExtractionResult,
)


# Common encodings used by CSV exports from research tools and Excel.
SUPPORTED_ENCODINGS = (
    "utf-8-sig",
    "utf-8",
    "cp1252",
    "latin-1",
)


# Common delimiters used in structured CSV and spreadsheet exports.
SUPPORTED_DELIMITERS = (
    ",",
    ";",
    "\t",
    "|",
)


def _read_csv_text(file_path: str) -> tuple[str, str]:
    """
    Read CSV content using a sequence of supported encodings.

    Returns:
        A tuple containing:
            - The decoded CSV text.
            - The encoding that successfully decoded the file.

    Raises:
        FileNotFoundError:
            If the CSV file does not exist.
        UnicodeError:
            If the file cannot be decoded.
    """

    # Read the file as bytes so that the encoding can be detected safely.
    with open(file_path, "rb") as csv_file:
        file_bytes = csv_file.read()

    # Attempt to decode the file using supported encodings.
    for encoding in SUPPORTED_ENCODINGS:

        try:
            # Decode the bytes into readable text.
            decoded_text = file_bytes.decode(encoding)

            # Return the decoded text and its encoding.
            return decoded_text, encoding

        except UnicodeDecodeError:
            # Try the next supported encoding.
            continue

    # Raise an error if no supported encoding works.
    raise UnicodeError(
        "Unable to decode the CSV file using supported encodings."
    )


def _detect_delimiter(csv_text: str) -> str:
    """
    Detect the most likely CSV delimiter.

    csv.Sniffer is used first. If detection fails, the function
    falls back to counting common delimiters in the first lines.

    Returns:
        The detected delimiter.
    """

    # Limit delimiter detection to the first few lines.
    sample = csv_text[:8192]

    try:
        # Let Python's CSV module infer the delimiter.
        dialect = csv.Sniffer().sniff(
            sample,
            delimiters="".join(SUPPORTED_DELIMITERS),
        )

        return dialect.delimiter

    except csv.Error:
        # Use a simple fallback when automatic detection fails.
        first_lines = sample.splitlines()[:10]

        delimiter_counts = {
            delimiter: sum(
                line.count(delimiter)
                for line in first_lines
            )
            for delimiter in SUPPORTED_DELIMITERS
        }

        # Select the delimiter occurring most frequently.
        detected_delimiter = max(
            delimiter_counts,
            key=delimiter_counts.get,
        )

        # A file with no detectable delimiter is treated as plain CSV.
        if delimiter_counts[detected_delimiter] == 0:
            return ","

        return detected_delimiter


def _format_row(values: list[str]) -> str:
    """
    Convert a CSV row into readable text.

    Empty cells are retained in the original row metadata but
    omitted from the readable text representation.
    """

    # Convert non-empty cell values into readable strings.
    readable_values = [
        str(value)
        for value in values
        if value is not None and value != ""
    ]

    # Join the values using a separator that preserves readability.
    return " | ".join(readable_values)


def extract_csv(file_path: str) -> ExtractionResult:
    """
    Extract structured content from a CSV file.

    Args:
        file_path:
            Path to the CSV file.

    Returns:
        ExtractionResult:
            Extracted text, row-level segments, encoding metadata,
            delimiter metadata, and extraction software information.

    Raises:
        FileNotFoundError:
            If the CSV file does not exist.
        ValueError:
            If the file extension is unsupported.
        UnicodeError:
            If the file cannot be decoded.
    """

    # Confirm that the source file exists.
    source_path = Path(file_path)

    if not source_path.is_file():
        raise FileNotFoundError(
            f"CSV file not found: {file_path}"
        )

    # Ensure that the extractor only handles CSV files.
    if source_path.suffix.lower() != ".csv":
        raise ValueError(
            "Unsupported file format. "
            "Only .csv files are supported."
        )

    # Decode the CSV content using a supported encoding.
    csv_text, detected_encoding = _read_csv_text(
        str(source_path)
    )

    # Detect the delimiter used in the CSV file.
    detected_delimiter = _detect_delimiter(csv_text)

    # Wrap the decoded CSV text in a file-like object.
    # newline="" allows Python's CSV parser to handle
    # newline characters correctly, including those inside
    # quoted multiline fields.

    csv_stream = io.StringIO(
        csv_text,
        newline="",
    )

    # Parse the CSV content while respecting quoted fields,
    # embedded line breaks, and CSV quoting rules.

    csv_reader = csv.reader(
        csv_stream,
        delimiter=detected_delimiter,
        quotechar='"',
        strict=True,
    )

    # Store the extracted row segments.
    segments: list[ExtractedSegment] = []

    # Store readable text for the complete CSV document.
    row_texts: list[str] = []

    # Store the header row when one exists.
    header_row: list[str] | None = None

    # Enumerate rows using one-based row numbers.
    for row_number, row_values in enumerate(
        csv_reader,
        start=1,
    ):

        # Skip rows containing only empty cells.
        if not row_values or all(
            value == ""
            for value in row_values
        ):
            continue

        # Treat the first non-empty row as the header row.
        if header_row is None:
            header_row = row_values

        # Convert the current row into readable text.
        row_text = _format_row(row_values)

        # Preserve the row's readable text.
        row_texts.append(row_text)

        # Build metadata for every cell in the current row.
        row_cells: list[dict[str, Any]] = []

        for column_number, cell_value in enumerate(
            row_values,
            start=1,
        ):

            # Use the header name when available.
            column_name = (
                header_row[column_number - 1]
                if header_row
                and column_number <= len(header_row)
                else None
            )

            # Preserve the cell's position and content.
            row_cells.append(
                {
                    "row_number": row_number,
                    "column_number": column_number,
                    "column_name": column_name,
                    "value": cell_value,
                }
            )

        # Create a traceable row-level extraction segment.
        segments.append(
            ExtractedSegment(
                segment_type="row",
                text=row_text,
                locator={
                    "file": source_path.name,
                    "row_number": row_number,
                    "delimiter": detected_delimiter,
                    "encoding": detected_encoding,
                    "cells": row_cells,
                },
            )
        )

    # Combine all row text into the complete document.
    raw_text = "\n".join(row_texts)

    # Return the structured extraction result.
    return ExtractionResult(
        raw_text=raw_text,
        normalized_text=raw_text,
        segments=segments,
        software_name="Python csv",
        software_version="standard library",
        configuration={
            "file_format": "csv",
            "encoding": detected_encoding,
            "delimiter": detected_delimiter,
            "preserve_headers": True,
            "preserve_row_positions": True,
            "preserve_column_positions": True,
        },
    )
