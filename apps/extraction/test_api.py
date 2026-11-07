"""
TRAPRO Extraction API Tests
===========================

Test document extraction through the REST API, including authentication,
document ownership, staff permissions, extraction failures, and persistence.
"""

import tempfile
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from rest_framework import status
from rest_framework.test import APIClient

from apps.extraction.models import (
    ExtractionRun,
    ExtractedContent,
    ContentSegment,
)
from apps.extraction.services.extraction_pipeline import EXTRACTORS
from apps.legal_sources.models import SourceDocument
from apps.legal_sources.services.ingestion import create_source_document


class SourceExtractionAPITests(TestCase):
    """Test the document extraction API endpoint."""

    @classmethod
    def setUpClass(cls):
        """Create isolated storage for uploaded test documents."""

        super().setUpClass()

        cls.media_directory = tempfile.TemporaryDirectory()

        cls.settings_override = override_settings(
            MEDIA_ROOT=cls.media_directory.name
        )

        cls.settings_override.enable()

    @classmethod
    def tearDownClass(cls):
        """Restore settings and remove temporary uploaded files."""

        cls.settings_override.disable()
        cls.media_directory.cleanup()

        super().tearDownClass()

    def setUp(self):
        """Create an authenticated user and API client."""

        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            username="trapro_extraction_test",
            password="test-password-123",
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.extraction_url_prefix = (
            "/api/v1/extraction/sources/"
        )

    def create_test_source(self, uploaded_by=None):
        """
        Create a valid TXT legal source document for extraction tests.

        The source is created through the established ingestion service
        so that normal validation and metadata handling are preserved.
        """

        if uploaded_by is None:
            uploaded_by = self.user

        uploaded_file = SimpleUploadedFile(
            name="cameroon_extraction_test.txt",
            content=(
                b"Contract law governs agreements between parties.\n\n"
                b"Civil liability concerns obligations arising from harm."
            ),
            content_type="text/plain",
        )

        return create_source_document(
            uploaded_file,
            title="Cameroon Legal Extraction Test",
            source_type="legislation",
            language="en",
            jurisdiction="Cameroon",
            uploaded_by=uploaded_by,
        )

    def get_extraction_url(self, source):
        """Build the extraction endpoint for a source document."""

        return (
            f"{self.extraction_url_prefix}"
            f"{source.pk}/run/"
        )

    def test_owner_can_extract_own_source_document(self):
        """An authenticated document owner can initiate extraction."""

        source = self.create_test_source()

        response = self.client.post(
            self.get_extraction_url(source)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertIn("extraction", response.data)

        self.assertEqual(
            response.data["extraction"]["source_id"],
            str(source.pk),
        )

        self.assertEqual(
            response.data["extraction"]["method"],
            "plain_text",
        )

        self.assertEqual(
            response.data["extraction"]["status"],
            "completed",
        )

        extraction_run = ExtractionRun.objects.get(
            source_document=source
        )

        self.assertEqual(extraction_run.created_by, self.user)
        self.assertEqual(extraction_run.status, "completed")

        self.assertTrue(
            ExtractedContent.objects.filter(
                extraction_run=extraction_run
            ).exists()
        )

        self.assertTrue(
            ContentSegment.objects.filter(
                extracted_content__extraction_run=extraction_run
            ).exists()
        )

    def test_user_cannot_extract_another_users_source(self):
        """An ordinary user cannot access another user's document."""

        user_model = get_user_model()

        another_user = user_model.objects.create_user(
            username="trapro_other_owner",
            password="test-password-123",
        )

        source = self.create_test_source(
            uploaded_by=another_user
        )

        response = self.client.post(
            self.get_extraction_url(source)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertFalse(
            ExtractionRun.objects.filter(
                source_document=source
            ).exists()
        )

    def test_staff_user_can_extract_another_users_source(self):
        """An authorised staff member can extract another user's source."""

        user_model = get_user_model()

        another_user = user_model.objects.create_user(
            username="trapro_staff_test_owner",
            password="test-password-123",
        )

        staff_user = user_model.objects.create_user(
            username="trapro_extraction_staff",
            password="test-password-123",
            is_staff=True,
        )

        source = self.create_test_source(
            uploaded_by=another_user
        )

        staff_client = APIClient()
        staff_client.force_authenticate(user=staff_user)

        response = staff_client.post(
            self.get_extraction_url(source)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        extraction_run = ExtractionRun.objects.get(
            source_document=source
        )

        self.assertEqual(
            extraction_run.created_by,
            staff_user,
        )

        self.assertEqual(
            extraction_run.status,
            "completed",
        )

    def test_unauthenticated_user_cannot_extract_source(self):
        """Unauthenticated requests must be rejected."""

        source = self.create_test_source()

        unauthenticated_client = APIClient()

        response = unauthenticated_client.post(
            self.get_extraction_url(source)
        )

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )

        self.assertFalse(
            ExtractionRun.objects.filter(
                source_document=source
            ).exists()
        )

    def test_unsupported_format_returns_bad_request(self):
        """Unsupported extraction formats return HTTP 400 and are recorded."""

        source = self.create_test_source()

        # Simulate a source document with an unsupported file extension.
        # The original upload remains unchanged; only its metadata is altered.
        source.file_extension = ".rtf"
        source.original_filename = "unsupported_document.rtf"

        source.save(
            update_fields=[
                "file_extension",
                "original_filename",
            ]
        )

        response = self.client.post(
            self.get_extraction_url(source)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        failed_run = ExtractionRun.objects.get(
            source_document=source
        )

        self.assertEqual(failed_run.status, "failed")
        self.assertEqual(failed_run.method, "other")

        self.assertIn(
            ".rtf",
            failed_run.error_message,
        )

    def test_runtime_failure_returns_server_error_and_is_recorded(self):
        """Unexpected extractor failures return HTTP 500 and remain recorded."""

        source = self.create_test_source()

        # Replace the TXT extractor temporarily to simulate a processing
        # failure while keeping the real extraction pipeline operational.
        with patch.dict(
            EXTRACTORS,
            {
                ".txt": Mock(
                    side_effect=RuntimeError(
                        "Simulated API extraction failure"
                    )
                )
            },
        ):
            response = self.client.post(
                self.get_extraction_url(source)
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

        failed_run = ExtractionRun.objects.get(
            source_document=source
        )

        self.assertEqual(failed_run.status, "failed")

        self.assertEqual(
            failed_run.error_message,
            "Simulated API extraction failure",
        )

        # A failed extraction must not remove the original legal source.
        self.assertTrue(
            SourceDocument.objects.filter(
                pk=source.pk
            ).exists()
        )

    def get_extraction_detail_url(self, extraction_run):
        """Build the detail endpoint for an extraction run."""

        return (
            f"/api/v1/extraction/runs/"
            f"{extraction_run.pk}/"
        )

    def test_owner_can_retrieve_own_extraction_results(self):
        """A source owner can retrieve the complete extraction results."""

        source = self.create_test_source()

        # First initiate extraction through the existing POST endpoint.
        post_response = self.client.post(
            self.get_extraction_url(source)
        )

        self.assertEqual(
            post_response.status_code,
            status.HTTP_201_CREATED,
        )

        extraction_run = ExtractionRun.objects.get(
            source_document=source
        )

        # Retrieve the results through the new GET endpoint.
        response = self.client.get(
            self.get_extraction_detail_url(extraction_run)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            str(response.data["id"]),
            str(extraction_run.pk),
        )

        self.assertEqual(
            str(response.data["source_id"]),
            str(source.pk),
        )

        self.assertEqual(
            response.data["source_title"],
            source.title,
        )

        self.assertEqual(
            response.data["status"],
            "completed",
        )

        # Verify that the extracted content is included.
        self.assertIsNotNone(
            response.data["extracted_content"]
        )

        extracted_content = response.data["extracted_content"]

        self.assertTrue(
            extracted_content["raw_text"]
        )

        self.assertTrue(
            extracted_content["normalized_text"]
        )

        self.assertGreater(
            extracted_content["character_count"],
            0,
        )

        self.assertGreater(
            extracted_content["word_count"],
            0,
        )

        # Verify that the extracted segments are included.
        self.assertGreater(
            len(extracted_content["segments"]),
            0,
        )

        # Verify that segment ordering is preserved.
        ordinals = [
            segment["ordinal"]
            for segment in extracted_content["segments"]
        ]

        self.assertEqual(
            ordinals,
            sorted(ordinals),
        )

        # Internal exception information must never be exposed.
        self.assertNotIn(
            "error_message",
            response.data,
        )

    def test_user_cannot_retrieve_another_users_extraction(self):
        """An ordinary user cannot retrieve another user's extraction."""

        user_model = get_user_model()

        another_user = user_model.objects.create_user(
            username="trapro_detail_other_owner",
            password="test-password-123",
        )

        source = self.create_test_source(
            uploaded_by=another_user
        )

        # Create an extraction run as the actual source owner.
        from apps.extraction.services.extraction_pipeline import run_extraction

        extraction_run = run_extraction(
            source,
            created_by=another_user,
        )

        # The current authenticated user is not the source owner.
        response = self.client.get(
            self.get_extraction_detail_url(extraction_run)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_staff_user_can_retrieve_another_users_extraction(self):
        """Staff can retrieve extraction results belonging to other users."""

        user_model = get_user_model()

        another_user = user_model.objects.create_user(
            username="trapro_detail_staff_owner",
            password="test-password-123",
        )

        staff_user = user_model.objects.create_user(
            username="trapro_detail_staff",
            password="test-password-123",
            is_staff=True,
        )

        source = self.create_test_source(
            uploaded_by=another_user
        )

        # Create an extraction run for the other user's source.
        from apps.extraction.services.extraction_pipeline import run_extraction

        extraction_run = run_extraction(
            source,
            created_by=another_user,
        )

        staff_client = APIClient()
        staff_client.force_authenticate(user=staff_user)

        response = staff_client.get(
            self.get_extraction_detail_url(extraction_run)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            str(response.data["id"]),
            str(extraction_run.pk),
        )

        self.assertIsNotNone(
            response.data["extracted_content"]
        )

    def test_failed_extraction_returns_null_content(self):
        """A failed extraction is retrievable without exposing its error."""

        source = self.create_test_source()

        # Change the extension to simulate an unsupported source format.
        source.file_extension = ".rtf"
        source.original_filename = "failed_extraction_test.rtf"

        source.save(
            update_fields=[
                "file_extension",
                "original_filename",
            ]
        )

        # The POST endpoint records the failed run and returns HTTP 400.
        post_response = self.client.post(
            self.get_extraction_url(source)
        )

        self.assertEqual(
            post_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        failed_run = ExtractionRun.objects.get(
            source_document=source
        )

        self.assertEqual(
            failed_run.status,
            "failed",
        )

        # Retrieve the failed extraction through the GET endpoint.
        response = self.client.get(
            self.get_extraction_detail_url(failed_run)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["status"],
            "failed",
        )

        self.assertIsNone(
            response.data["extracted_content"]
        )

        # Internal diagnostic details must remain private.
        self.assertNotIn(
            "error_message",
            response.data,
        )

    def test_unauthenticated_user_cannot_retrieve_extraction(self):
        """Unauthenticated users cannot retrieve extraction results."""

        source = self.create_test_source()

        from apps.extraction.services.extraction_pipeline import run_extraction

        extraction_run = run_extraction(
            source,
            created_by=self.user,
        )

        unauthenticated_client = APIClient()

        response = unauthenticated_client.get(
            self.get_extraction_detail_url(extraction_run)
        )

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )

    def test_nonexistent_extraction_run_returns_not_found(self):
        """Unknown extraction UUIDs return HTTP 404."""

        nonexistent_run_id = (
            "12345678-1234-5678-1234-567812345678"
        )

        response = self.client.get(
            f"/api/v1/extraction/runs/{nonexistent_run_id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
