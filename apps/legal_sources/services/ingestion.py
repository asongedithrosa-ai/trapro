
"""
TRAPRO Legal Source Ingestion Service
=====================================

This module manages the ingestion of original legal and academic
documents into TRAPRO.

Responsibilities:
- Validate uploaded documents.
- Calculate SHA-256 checksums.
- Detect previously ingested documents.
- Preserve source metadata.
- Store original files.
- Create SourceDocument database records.

Document extraction is deliberately handled by a separate application.
"""

import hashlib
import mimetypes
from pathlib import Path

from django.core.exceptions import ValidationError

from apps.legal_sources.models import SourceDocument
from apps.legal_sources.services.validators import (
    validate_legal_source_file,
)


def calculate_sha256(uploaded_file):
    """
    Calculate the SHA-256 checksum of an uploaded file.

    The file is read in chunks to avoid loading large documents
    entirely into memory.

    Args:
        uploaded_file: Django UploadedFile instance.

    Returns:
        str: Hexadecimal SHA-256 checksum.
    """

    sha256 = hashlib.sha256()

    # Start reading from the beginning of the uploaded file.
    uploaded_file.seek(0)

    # Process the document incrementally.
    for chunk in uploaded_file.chunks():
        sha256.update(chunk)

    # Restore the pointer for subsequent storage operations.
    uploaded_file.seek(0)

    return sha256.hexdigest()


def find_duplicate_source(checksum):
    """
    Find an existing source document with the same checksum.

    Args:
        checksum (str): SHA-256 checksum of the uploaded document.

    Returns:
        SourceDocument or None: Matching source, if one exists.
    """

    return SourceDocument.objects.filter(
        sha256_checksum=checksum
    ).first()


def create_source_document(
    uploaded_file,
    *,
    title,
    source_type="other",
    language="other",
    jurisdiction="",
    citation="",
    description="",
    uploaded_by=None,
    allow_duplicate=False,
):
    """
    Validate and ingest an original legal source document.

    Args:
        uploaded_file: Django UploadedFile instance.
        title (str): Human-readable document title.
        source_type (str): Legal or academic source classification.
        language (str): Document language classification.
        jurisdiction (str): Associated jurisdiction or legal system.
        citation (str): Official legal citation, if available.
        description (str): Optional document description.
        uploaded_by: Django user responsible for the upload.
        allow_duplicate (bool): Whether identical content may be stored
            as a separate source record.

    Returns:
        SourceDocument: Newly created source document record.

    Raises:
        ValidationError: If validation fails or a duplicate is rejected.
    """

    # Reject missing titles before attempting file storage.
    if not title or not title.strip():
        raise ValidationError("A document title is required.")

    # Validate the file before processing or storing it.
    validate_legal_source_file(uploaded_file)

    # Preserve the original filename and determine its extension.
    original_filename = Path(uploaded_file.name).name
    file_extension = Path(original_filename).suffix.lower()

    # Calculate a checksum to identify identical file contents.
    checksum = calculate_sha256(uploaded_file)

    # Check whether this exact file has already been ingested.
    existing_source = find_duplicate_source(checksum)

    if existing_source and not allow_duplicate:
        raise ValidationError(
            "This document has already been ingested. "
            f"Existing source ID: {existing_source.id}. "
            "Set allow_duplicate=True only if a separate source "
            "record is intentionally required."
        )

    # Determine the MIME type from the filename as an initial hint.
    # This is not treated as authoritative format verification.
    mime_type, _ = mimetypes.guess_type(original_filename)

    # Construct the database record before writing the physical file.
    source_document = SourceDocument(
        title=title.strip(),
        original_filename=original_filename,
        file_extension=file_extension,
        mime_type=mime_type or "",
        file_size=uploaded_file.size,
        sha256_checksum=checksum,
        source_type=source_type,
        language=language,
        jurisdiction=jurisdiction,
        citation=citation,
        description=description,
        uploaded_by=uploaded_by,
    )

    # Validate model fields and choice values before storage.
    source_document.full_clean(exclude=["original_file"])

    # Save the original file independently of extraction processing.
    try:
        source_document.original_file.save(
            original_filename,
            uploaded_file,
            save=False,
        )

        # Persist the source metadata and stored-file reference.
        source_document.save()

    except Exception:
        # If database persistence fails after file storage, remove the
        # newly stored file to avoid leaving an orphaned upload.
        if source_document.original_file.name:
            source_document.original_file.storage.delete(
                source_document.original_file.name
            )

        raise

    return source_document
