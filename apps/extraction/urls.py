"""
TRAPRO Extraction API URLs
==========================

This module defines URL routes for document extraction operations.

Available endpoints:
    POST /sources/<source_id>/run/
        Initiate extraction for an uploaded source document.

    GET /runs/<run_id>/
        Retrieve the detailed results of an extraction run.
"""

from django.urls import path

from apps.extraction.views import (
    ExtractionRunDetailView,
    SourceExtractionView,
)


urlpatterns = [
    # Initiate extraction for an existing legal source document.
    path(
        "sources/<uuid:source_id>/run/",
        SourceExtractionView.as_view(),
        name="source-extraction-run",
    ),

    # Retrieve the results of an existing extraction run.
    path(
        "runs/<uuid:run_id>/",
        ExtractionRunDetailView.as_view(),
        name="extraction-run-detail",
    ),
]
