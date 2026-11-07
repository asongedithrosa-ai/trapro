
"""
TRAPRO Legal Source File Validators
===================================

This module validates uploaded source documents before ingestion.

Validation covers:
- Supported file extensions.
- File size limits.
- Basic file-signature checks.
- Empty-file detection.

These checks are an initial security layer. They do not replace
comprehensive malware scanning or production-grade content inspection.
"""

from pathlib import Path

from django.core.exceptions import ValidationError


# Maximum permitted upload size for the initial development configuration.
# This value can later be moved into environment-based settings.
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


# File extensions accepted by the initial TRAPRO ingestion pipeline.
SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".xls",
    ".csv",
    ".txt",
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".tif",
    ".bmp",
    ".webp",
}


# Known file signatures used for basic format verification.
# These signatures are not a substitute for parsing the complete file.
FILE_SIGNATURES = {
    ".pdf": [b"%PDF-"],
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".tiff": [b"II*\x00", b"MM\x00*"],
    ".tif": [b"II*\x00", b"MM\x00*"],
    ".bmp": [b"BM"],
    ".webp": [b"RIFF"],
    ".docx": [b"PK\x03\x04"],
    ".xlsx": [b"PK\x03\x04"],
}


def validate_file_extension(filename):
    """
    Ensure that the uploaded filename has a supported extension.

    Args:
        filename (str): Original name of the uploaded file.

    Raises:
        ValidationError: If the extension is unsupported.
    """

    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file extension: {extension or 'none'}."
        )


def validate_file_size(uploaded_file):
    """
    Ensure that an uploaded file does not exceed the size limit.

    Args:
        uploaded_file: Django UploadedFile instance.

    Raises:
        ValidationError: If the file is empty or too large.
    """

    if uploaded_file.size <= 0:
        raise ValidationError("The uploaded file is empty.")

    if uploaded_file.size > MAX_UPLOAD_SIZE:
        raise ValidationError(
            "The uploaded file exceeds the maximum permitted size of 50 MB."
        )


def validate_file_signature(uploaded_file):
    """
    Perform basic signature checks for formats with known signatures.

    CSV and TXT are not checked using binary signatures because they
    are text-based formats and require separate content inspection.

    Args:
        uploaded_file: Django UploadedFile instance.

    Raises:
        ValidationError: If a recognized signature does not match.
    """

    extension = Path(uploaded_file.name).suffix.lower()
    expected_signatures = FILE_SIGNATURES.get(extension)

    # Text formats have no single reliable binary signature.
    if not expected_signatures:
        return

    # Read only the initial bytes required for signature verification.
    uploaded_file.seek(0)
    file_header = uploaded_file.read(16)
    uploaded_file.seek(0)

    if not any(
        file_header.startswith(signature)
        for signature in expected_signatures
    ):
        raise ValidationError(
            f"The file content does not match its .{extension.lstrip('.')} extension."
        )


def validate_legal_source_file(uploaded_file):
    """
    Run all initial validation checks on an uploaded source document.

    Args:
        uploaded_file: Django UploadedFile instance.

    Raises:
        ValidationError: If any validation check fails.
    """

    validate_file_extension(uploaded_file.name)
    validate_file_size(uploaded_file)
    validate_file_signature(uploaded_file)

    # Restore the file pointer so downstream ingestion can read it.
    uploaded_file.seek(0)
