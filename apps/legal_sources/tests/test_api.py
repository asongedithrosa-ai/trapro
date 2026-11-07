
"""
TRAPRO Legal Source API Tests
=============================

Test the legal source upload endpoint, authentication,
metadata persistence, and duplicate detection.
"""

import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework import status
from rest_framework.test import APIClient


class SourceDocumentUploadAPITests(TestCase):
    """Test the legal source document upload API."""

    @classmethod
    def setUpClass(cls):
        """Create an isolated media directory for uploaded test files."""
        super().setUpClass()

        cls.media_directory = tempfile.TemporaryDirectory()

        cls.settings_override = override_settings(
            MEDIA_ROOT=cls.media_directory.name
        )
        cls.settings_override.enable()

    @classmethod
    def tearDownClass(cls):
        """Remove temporary media files after the tests."""
        cls.settings_override.disable()
        cls.media_directory.cleanup()

        super().tearDownClass()

    def setUp(self):
        """Create an authenticated test user and API client."""
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            username="trapro_api_test",
            password="test-password-123",
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.upload_url = "/api/v1/sources/upload/"

    def create_test_file(self):
        """Return a fresh TXT upload for each test request."""
        return SimpleUploadedFile(
            name="cameroon_legal_test.txt",
            content=b"Test legal source content for TRAPRO.",
            content_type="text/plain",
        )

    def test_authenticated_upload_creates_source_document(self):
        """An authenticated user can upload a valid legal source."""
        response = self.client.post(
            self.upload_url,
            {
                "title": "Cameroon Legal Test Document",
                "original_file": self.create_test_file(),
                "source_type": "legislation",
                "language": "en",
                "jurisdiction": "Cameroon",
                "citation": "TRAPRO-TEST-001",
                "description": "API upload integration test.",
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertIn("source", response.data)

        self.assertEqual(
            response.data["source"]["title"],
            "Cameroon Legal Test Document",
        )

        self.assertEqual(
            response.data["source"]["language"],
            "en",
        )

        self.assertEqual(
            response.data["source"]["jurisdiction"],
            "Cameroon",
        )

        self.assertTrue(response.data["source"]["id"])

        self.assertEqual(
            response.data["source"]["file_extension"],
            ".txt",
        )

    def test_duplicate_upload_is_rejected(self):
        """Identical document contents are rejected by default."""

        first_response = self.client.post(
            self.upload_url,
            {
                "title": "First Legal Document",
                "original_file": self.create_test_file(),
                "source_type": "legislation",
                "language": "en",
            },
            format="multipart",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )

        second_response = self.client.post(
            self.upload_url,
            {
                "title": "Duplicate Legal Document",
                "original_file": self.create_test_file(),
                "source_type": "legislation",
                "language": "en",
            },
            format="multipart",
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_unauthenticated_upload_is_rejected(self):
        """Unauthenticated users cannot upload legal sources."""

        unauthenticated_client = APIClient()

        response = unauthenticated_client.post(
            self.upload_url,
            {
                "title": "Unauthorised Upload",
                "original_file": self.create_test_file(),
            },
            format="multipart",
        )

        self.assertIn(response.status_code, [401, 403])
