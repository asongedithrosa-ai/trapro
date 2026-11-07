"""
TRAPRO Document Extraction API Views
=====================================

This module exposes REST API endpoints for document extraction.

Available operations:
    1. Initiate extraction for an existing legal source document.
    2. Retrieve the detailed results of an extraction run.

The extraction process is delegated to the shared extraction pipeline.

Access is restricted to document owners and authorised staff members.
"""

import logging

from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.legal_sources.models import SourceDocument

from apps.extraction.models import ExtractionRun
from apps.extraction.serializers import ExtractionRunDetailSerializer
from apps.extraction.services.extraction_pipeline import run_extraction


# Create a module-level logger for API-level processing errors.
logger = logging.getLogger(__name__)


class SourceExtractionView(APIView):
    """
    Initiate extraction for an existing legal source document.

    A regular authenticated user may extract only documents they uploaded.
    Staff members and superusers may extract any source document.

    Extraction currently runs synchronously within the API request.
    """

    # Require authentication before allowing extraction.
    permission_classes = [IsAuthenticated]

    def post(self, request, source_id, *args, **kwargs):
        """
        Initiate extraction for the specified source document.

        Returns:
            HTTP 201: Extraction completed or partially completed.
            HTTP 400: Unsupported format or invalid extraction input.
            HTTP 401/403: Authentication required or denied.
            HTTP 404: Source does not exist or is not accessible.
            HTTP 500: Unexpected extraction failure.
        """

        # Begin with the complete set of source documents.
        source_queryset = SourceDocument.objects.all()

        # Restrict ordinary users to documents they uploaded.
        # Staff and superusers retain access to all source documents.
        if not (request.user.is_staff or request.user.is_superuser):
            source_queryset = source_queryset.filter(
                uploaded_by=request.user
            )

        # Return 404 for both nonexistent and inaccessible documents.
        # This avoids revealing the existence of another user's sources.
        source_document = get_object_or_404(
            source_queryset,
            pk=source_id,
        )

        try:
            # Delegate processing and database persistence to the
            # established extraction pipeline.
            extraction_run = run_extraction(
                source_document,
                created_by=request.user,
            )

        except ValueError:
            # The pipeline records unsupported-format attempts before
            # raising this exception. Do not create another run here.
            return Response(
                {
                    "error": {
                        "code": "extraction_input_error",
                        "detail": (
                            "The source format is unsupported or "
                            "the extraction input is invalid."
                        ),
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception:
            # The pipeline has already recorded the failed run.
            # Log the exception, but do not expose internal details,
            # filesystem paths, or tracebacks through the API.
            logger.exception(
                "API extraction failed for source %s.",
                source_document.pk,
            )

            return Response(
                {
                    "error": {
                        "code": "extraction_failed",
                        "detail": (
                            "The document could not be processed. "
                            "The failed extraction attempt has been recorded."
                        ),
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Return identifying information about the completed run.
        return Response(
            {
                "message": "Document extraction completed.",
                "extraction": {
                    "id": str(extraction_run.id),
                    "source_id": str(source_document.id),
                    "source_title": source_document.title,
                    "method": extraction_run.method,
                    "status": extraction_run.status,
                    "software_name": extraction_run.software_name,
                    "software_version": extraction_run.software_version,
                    "created_at": extraction_run.created_at.isoformat(),
                    "started_at": (
                        extraction_run.started_at.isoformat()
                        if extraction_run.started_at
                        else None
                    ),
                    "completed_at": (
                        extraction_run.completed_at.isoformat()
                        if extraction_run.completed_at
                        else None
                    ),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class ExtractionRunDetailView(APIView):
    """
    Retrieve the detailed results of an existing extraction run.

    A regular authenticated user may retrieve only extraction runs
    belonging to source documents they uploaded.

    Staff members and superusers may retrieve any extraction run.

    Internal exception messages are deliberately excluded from the
    serialized response.
    """

    # Require authentication before allowing result retrieval.
    permission_classes = [IsAuthenticated]

    def get(self, request, run_id, *args, **kwargs):
        """
        Retrieve an extraction run and its associated extracted content.

        Returns:
            HTTP 200: Extraction run and content details.
            HTTP 401/403: Authentication required or denied.
            HTTP 404: Run does not exist or is not accessible.
        """

        # Load the source document and optional extracted content
        # efficiently to avoid unnecessary database queries.
        extraction_queryset = (
            ExtractionRun.objects
            .select_related(
                "source_document",
                "extracted_content",
            )
            .prefetch_related(
                "extracted_content__segments"
            )
        )

        # Restrict ordinary users to runs associated with their
        # own uploaded source documents.
        # Staff and superusers retain access to all extraction runs.
        if not (request.user.is_staff or request.user.is_superuser):
            extraction_queryset = extraction_queryset.filter(
                source_document__uploaded_by=request.user
            )

        # Return 404 for both nonexistent and inaccessible runs.
        # This prevents users from discovering another user's records.
        extraction_run = get_object_or_404(
            extraction_queryset,
            pk=run_id,
        )

        # Serialize the extraction run, source metadata, extracted text,
        # and ordered content segments.
        serializer = ExtractionRunDetailSerializer(
            extraction_run,
            context={"request": request},
        )

        # Return the complete read-only extraction result.
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
