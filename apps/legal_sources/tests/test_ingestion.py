
"""
TRAPRO Legal Source Ingestion Tests
===================================

These tests verify the document-ingestion workflow, including:
- Successful document ingestion.
- Original-file preservation.
- SHA-256 checksum consistency.
- Duplicate detection.
- Intentional duplicate ingestion.
- Rejection of unsupported or invalid files.
- Upload-size enforcement.

Temporary media storage is used so tests do not leave documents
inside the project's actual media directory.
"""

import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.legal_sources.models import SourceDocument
from apps.legal_sources.services.ingestion import (
    calculate_sha256,
    create_source_document,
)


class LegalSourceIngestionTests(TestCase):
    """Test the legal-source document-ingestion service."""

    def setUp(self):
        """
        Configure isolated media storage for each test.

        This prevents test uploads from mixing with real project files.
        """

        self.temp_media = tempfile.TemporaryDirectory()

        self.media_settings = override_settings(
            MEDIA_ROOT=self.temp_media.name
        )
        self.media_settings.enable()

        self.addCleanup(self.media_settings.disable)
        self.addCleanup(self.temp_media.cleanup)

        # Use a small valid PDF header for basic ingestion tests.
        self.pdf_content = (
            b"%PDF-1.4\n"
            b"TRAPRO test document\n"
            b"%%EOF"
        )

    def make_pdf(self, filename="test_law.pdf"):
        """Create a fresh in-memory PDF upload for testing."""

        return SimpleUploadedFile(
            filename,
            self.pdf_content,
            content_type="application/pdf",
        )

    def test_successful_document_ingestion(self):
        """Verify that a valid PDF creates a source record."""

        source = create_source_document(
            self.make_pdf(),
            title="Test Legal Document",
            source_type="legislation",
            language="en",
            jurisdiction="Cameroon",
        )

        self.assertIsInstance(source, SourceDocument)
        self.assertEqual(source.title, "Test Legal Document")
        self.assertEqual(source.file_extension, ".pdf")
        self.assertEqual(source.file_size, len(self.pdf_content))

    def test_original_file_is_preserved(self):
        """Verify that the uploaded file exists in media storage."""

        source = create_source_document(
            self.make_pdf(),
            title="Preservation Test",
        )

        stored_path = Path(source.original_file.path)

        self.assertTrue(stored_path.exists())
        self.assertEqual(
            stored_path.read_bytes(),
            self.pdf_content,
        )

    def test_sha256_checksum_is_correct(self):
        """Verify checksum consistency against Python's hashlib."""

        uploaded_file = self.make_pdf()

        expected_checksum = hashlib.sha256(
            self.pdf_content
        ).hexdigest()

        actual_checksum = calculate_sha256(uploaded_file)

        self.assertEqual(actual_checksum, expected_checksum)

        source = create_source_document(
            self.make_pdf(),
            title="Checksum Test",
        )

        self.assertEqual(
            source.sha256_checksum,
            expected_checksum,
        )

    def test_duplicate_document_is_rejected(self):
        """Verify that identical content cannot be ingested twice by default."""

        create_source_document(
            self.make_pdf(),
            title="Original Document",
        )

        with self.assertRaises(ValidationError):
            create_source_document(
                self.make_pdf(),
                title="Duplicate Document",
            )

        self.assertEqual(SourceDocument.objects.count(), 1)

    def test_intentional_duplicate_is_allowed(self):
        """Verify that separate records can be created when explicitly allowed."""

        create_source_document(
            self.make_pdf(),
            title="First Institutional Copy",
        )

        duplicate = create_source_document(
            self.make_pdf(),
            title="Second Institutional Copy",
            allow_duplicate=True,
        )

        self.assertIsInstance(duplicate, SourceDocument)
        self.assertEqual(SourceDocument.objects.count(), 2)

    def test_unsupported_extension_is_rejected(self):
        """Verify that unsupported file extensions are rejected."""

        uploaded_file = SimpleUploadedFile(
            "malicious.exe",
            b"Some executable content",
        )

        with self.assertRaises(ValidationError):
            create_source_document(
                uploaded_file,
                title="Unsupported File",
            )

        self.assertEqual(SourceDocument.objects.count(), 0)

    def test_invalid_pdf_signature_is_rejected(self):
        """Verify that a text file renamed as PDF is rejected."""

        uploaded_file = SimpleUploadedFile(
            "fake.pdf",
            b"This is not a PDF document.",
        )

        with self.assertRaises(ValidationError):
            create_source_document(
                uploaded_file,
                title="Invalid PDF",
            )

        self.assertEqual(SourceDocument.objects.count(), 0)

    def test_empty_file_is_rejected(self):
        """Verify that zero-byte documents cannot be ingested."""

        uploaded_file = SimpleUploadedFile(
            "empty.pdf",
            b"",
        )

        with self.assertRaises(ValidationError):
            create_source_document(
                uploaded_file,
                title="Empty Document",
            )

    def test_oversized_file_is_rejected(self):
        """Verify that the configured upload-size limit is enforced."""

        uploaded_file = self.make_pdf()

        # Reduce the limit for this test instead of allocating 50 MB.
        with patch(
            "apps.legal_sources.services.validators.MAX_UPLOAD_SIZE",
            5,
        ):
            with self.assertRaises(ValidationError):
                create_source_document(
                    uploaded_file,
                    title="Oversized Document",
                )

        self.assertEqual(SourceDocument.objects.count(), 0)
