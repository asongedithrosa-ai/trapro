
"""
TRAPRO Legal Sources URL Configuration
======================================
"""

from django.urls import path

from apps.legal_sources.views import SourceDocumentUploadView


urlpatterns = [
    # Upload a new legal or academic source document.
    path(
        "upload/",
        SourceDocumentUploadView.as_view(),
        name="source-document-upload",
    ),
]
