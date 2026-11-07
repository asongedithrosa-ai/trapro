
"""
TRAPRO Legal Source API Views
=============================

This module exposes REST API endpoints for managing legal source
documents.

Document ingestion is delegated to the existing ingestion service.
"""

from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.legal_sources.models import SourceDocument
from apps.legal_sources.serializers import SourceDocumentUploadSerializer
from apps.legal_sources.services.ingestion import create_source_document


class SourceDocumentUploadView(APIView):
    """
    Accept and ingest a legal or academic source document.

    The endpoint accepts multipart/form-data requests containing the
    original file and its associated metadata.

    Authentication is required to prevent unauthorised document uploads.
    """

    # Only authenticated users may upload legal source documents.
    permission_classes = [IsAuthenticated]

    # Support browser-based multipart uploads and form submissions.
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        """
        Validate and ingest an uploaded source document.

        Returns:
            HTTP 201: Source document successfully created.
            HTTP 400: Invalid metadata, unsupported file, or duplicate.
            HTTP 401: Authentication required.
        """

        # Validate the incoming request data.
        serializer = SourceDocumentUploadSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Retrieve validated data without duplicating validation logic.
        validated_data = serializer.validated_data

        try:
            # Delegate file validation, checksum calculation, duplicate
            # detection, metadata creation, and storage to the service.
            source_document = create_source_document(
                uploaded_file=validated_data["original_file"],
                title=validated_data["title"],
                source_type=validated_data["source_type"],
                language=validated_data["language"],
                jurisdiction=validated_data["jurisdiction"],
                citation=validated_data["citation"],
                description=validated_data["description"],
                uploaded_by=request.user,
                allow_duplicate=validated_data["allow_duplicate"],
            )

        except DjangoValidationError as exc:
            # Convert Django validation exceptions into a consistent
            # REST API response.
            if hasattr(exc, "message_dict"):
                errors = exc.message_dict
            else:
                errors = {"detail": exc.messages}

            return Response(
                {"errors": errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Return the newly created source document's identifying
        # information without exposing its physical storage path.
        return Response(
            {
                "message": "Legal source document uploaded successfully.",
                "source": {
                    "id": str(source_document.id),
                    "title": source_document.title,
                    "original_filename": source_document.original_filename,
                    "file_extension": source_document.file_extension,
                    "mime_type": source_document.mime_type,
                    "file_size": source_document.file_size,
                    "sha256_checksum": source_document.sha256_checksum,
                    "source_type": source_document.source_type,
                    "language": source_document.language,
                    "jurisdiction": source_document.jurisdiction,
                    "citation": source_document.citation,
                    "description": source_document.description,
                    "uploaded_at": source_document.uploaded_at.isoformat(),
                },
            },
            status=status.HTTP_201_CREATED,
        )
