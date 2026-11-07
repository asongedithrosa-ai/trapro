
"""
TRAPRO Excel Extraction Service
===============================

This module extracts structured content from Excel workbooks.

Supported formats:
    - .xlsx: Modern Excel workbooks, using openpyxl.
    - .xls:  Legacy Excel workbooks, using xlrd.

The extractor preserves:
    - Worksheet names and visibility.
    - Row and cell positions.
    - Cell values and formulas.
    - Cached formula results when available.
    - Workbook and worksheet provenance.

Important:
    openpyxl does not calculate Excel formulas. It can read formulas
    and cached results stored in the workbook, but it cannot guarantee
    that cached results are current.

    The original uploaded workbook must remain unchanged.
"""

from pathlib import Path
from typing import Any

import openpyxl
import xlrd

from apps.extraction.services.base import (
    ExtractedSegment,
    ExtractionResult,
)


def _is_empty(value: Any) -> bool:
    """
    Determine whether a cell contains no meaningful value.

    Empty strings and None are treated as empty. Numeric zero and
    Boolean False are retained because they are valid cell values.
    """

    return value is None or value == ""


def _format_value(value: Any) -> str:
    """
    Convert a cell value into a readable string.

    This function deliberately does not modify the original cell value.
    """

    if value is None:
        return ""

    return str(value)


def _extract_xlsx(file_path: str) -> ExtractionResult:
    """
    Extract content from a modern .xlsx workbook.

    The workbook is loaded twice:
        1. data_only=False retrieves formulas.
        2. data_only=True retrieves cached formula results.

    Formula results may be unavailable if the workbook has not been
    recalculated and saved by Excel or another compatible application.
    """

    # Load formulas without modifying the original workbook.
    formula_workbook = openpyxl.load_workbook(
        file_path,
        data_only=False,
        read_only=False,
    )

    # Load cached values stored for formulas.
    value_workbook = openpyxl.load_workbook(
        file_path,
        data_only=True,
        read_only=False,
    )

    segments: list[ExtractedSegment] = []
    worksheet_texts: list[str] = []

    try:
        # Process every worksheet, including hidden worksheets.
        for worksheet_name in formula_workbook.sheetnames:

            formula_sheet = formula_workbook[worksheet_name]
            value_sheet = value_workbook[worksheet_name]

            # Preserve worksheet visibility for traceability.
            worksheet_visibility = formula_sheet.sheet_state

            row_texts: list[str] = []

            # Iterate over cells that contain values or formulas.
            for row in formula_sheet.iter_rows():

                cell_texts: list[str] = []
                row_cells: list[dict[str, Any]] = []

                for formula_cell in row:

                    # Retrieve the matching cell containing cached values.
                    value_cell = value_sheet[formula_cell.coordinate]

                    formula_or_value = formula_cell.value
                    cached_value = value_cell.value

                    # Skip cells that contain no value or formula.
                    if _is_empty(formula_or_value):
                        continue

                    # Determine whether the cell contains an Excel formula.
                    is_formula = (
                        isinstance(formula_or_value, str)
                        and formula_or_value.startswith("=")
                    )

                    # For formulas, retain both formula and cached result.
                    # For ordinary cells, formula_or_value is the cell value.
                    extracted_value = (
                        cached_value
                        if is_formula and cached_value is not None
                        else formula_or_value
                    )

                    # Convert the extracted value to readable text.
                    readable_value = _format_value(extracted_value)

                    # Preserve the cell's formula/value information.
                    cell_metadata = {
                        "cell_reference": formula_cell.coordinate,
                        "row_number": formula_cell.row,
                        "column_number": formula_cell.column,
                        "is_formula": is_formula,
                        "formula": (
                            formula_or_value if is_formula else None
                        ),
                        "cached_value": (
                            cached_value if is_formula else None
                        ),
                        "cached_value_available": (
                            cached_value is not None if is_formula else None
                        ),
                        "extracted_value": extracted_value,
                        "data_type": formula_cell.data_type,
                    }

                    row_cells.append(cell_metadata)

                    # Add the readable value to the row's text.
                    if readable_value:
                        cell_texts.append(readable_value)

                # Skip rows that have no meaningful content.
                if not row_cells:
                    continue

                row_text = " | ".join(cell_texts)
                row_texts.append(row_text)

                # Create a traceable row-level extraction segment.
                segments.append(
                    ExtractedSegment(
                        segment_type="row",
                        text=row_text,
                        locator={
                            "workbook": Path(file_path).name,
                            "worksheet": worksheet_name,
                            "worksheet_visibility": worksheet_visibility,
                            "row_number": row[0].row,
                            "cells": row_cells,
                        },
                    )
                )

            # Preserve worksheet-level text for the full extraction result.
            worksheet_text = "\n".join(row_texts)

            if worksheet_text:
                worksheet_texts.append(
                    f"Worksheet: {worksheet_name}\n{worksheet_text}"
                )

            # Create a worksheet-level segment.
            segments.append(
                ExtractedSegment(
                    segment_type="sheet",
                    text=worksheet_text,
                    locator={
                        "workbook": Path(file_path).name,
                        "worksheet": worksheet_name,
                        "worksheet_visibility": worksheet_visibility,
                    },
                )
            )

    finally:
        # Always close both workbooks after extraction.
        formula_workbook.close()
        value_workbook.close()

    # Combine worksheet content into the complete extraction result.
    raw_text = "\n\n".join(worksheet_texts)

    return ExtractionResult(
        raw_text=raw_text,
        normalized_text=raw_text,
        segments=segments,
        software_name="openpyxl",
        software_version=openpyxl.__version__,
        configuration={
            "file_format": "xlsx",
            "extract_formulas": True,
            "extract_cached_formula_values": True,
            "preserve_worksheet_structure": True,
            "include_hidden_worksheets": True,
        },
    )


def _extract_xls(file_path: str) -> ExtractionResult:
    """
    Extract content from a legacy .xls workbook.

    xlrd provides access to cell values and worksheet structure.
    Formula source text is generally not available through xlrd,
    so formula preservation is more limited than for .xlsx files.
    """

    # Open the legacy workbook without modifying it.
    workbook = xlrd.open_workbook(
        file_path,
        on_demand=True,
    )

    segments: list[ExtractedSegment] = []
    worksheet_texts: list[str] = []

    try:
        # Process each worksheet in the workbook.
        for worksheet in workbook.sheets():

            row_texts: list[str] = []

            # Iterate over rows containing data.
            for row_number in range(worksheet.nrows):

                cell_texts: list[str] = []
                row_cells: list[dict[str, Any]] = []

                # Iterate over columns in the current row.
                for column_number in range(worksheet.ncols):

                    cell = worksheet.cell(
                        row_number,
                        column_number,
                    )

                    # Convert the cell value to readable text.
                    readable_value = _format_value(cell.value)

                    # Skip empty cells.
                    if _is_empty(cell.value):
                        continue

                    # Excel uses one-based row/column references.
                    excel_row = row_number + 1
                    excel_column = column_number + 1

                    # Preserve cell position and value metadata.
                    cell_metadata = {
                        "row_number": excel_row,
                        "column_number": excel_column,
                        "cell_type": cell.ctype,
                        "value": cell.value,
                    }

                    row_cells.append(cell_metadata)
                    cell_texts.append(readable_value)

                # Skip rows without meaningful content.
                if not row_cells:
                    continue

                row_text = " | ".join(cell_texts)
                row_texts.append(row_text)

                # Create a traceable row-level segment.
                segments.append(
                    ExtractedSegment(
                        segment_type="row",
                        text=row_text,
                        locator={
                            "workbook": Path(file_path).name,
                            "worksheet": worksheet.name,
                            "row_number": row_number + 1,
                            "cells": row_cells,
                        },
                    )
                )

            # Combine the worksheet's rows.
            worksheet_text = "\n".join(row_texts)

            if worksheet_text:
                worksheet_texts.append(
                    f"Worksheet: {worksheet.name}\n{worksheet_text}"
                )

            # Create a worksheet-level segment.
            segments.append(
                ExtractedSegment(
                    segment_type="sheet",
                    text=worksheet_text,
                    locator={
                        "workbook": Path(file_path).name,
                        "worksheet": worksheet.name,
                    },
                )
            )

    finally:
        # Release workbook resources.
        workbook.release_resources()

    # Combine all worksheet content.
    raw_text = "\n\n".join(worksheet_texts)

    return ExtractionResult(
        raw_text=raw_text,
        normalized_text=raw_text,
        segments=segments,
        software_name="xlrd",
        software_version=xlrd.__version__,
        configuration={
            "file_format": "xls",
            "preserve_worksheet_structure": True,
            "preserve_cell_positions": True,
            "formula_source_available": False,
        },
    )


def extract_excel(file_path: str) -> ExtractionResult:
    """
    Extract structured content from an Excel workbook.

    Args:
        file_path:
            Path to the Excel workbook.

    Returns:
        ExtractionResult:
            Extracted workbook text, row and worksheet segments,
            cell metadata, and extraction software information.

    Raises:
        FileNotFoundError:
            If the workbook does not exist.
        ValueError:
            If the file extension is unsupported.
    """

    # Confirm that the source file exists.
    source_path = Path(file_path)

    if not source_path.is_file():
        raise FileNotFoundError(
            f"Excel workbook not found: {file_path}"
        )

    # Determine the file format from its extension.
    extension = source_path.suffix.lower()

    # Route modern Excel files to the openpyxl extractor.
    if extension == ".xlsx":
        return _extract_xlsx(str(source_path))

    # Route legacy Excel files to the xlrd extractor.
    if extension == ".xls":
        return _extract_xls(str(source_path))

    # Reject unsupported file formats.
    raise ValueError(
        "Unsupported Excel format. "
        "Only .xlsx and .xls files are supported."
    )
