
"""
TRAPRO Extraction Service Foundation
====================================

This module defines the shared data structures used by all document
extractors.

PDF, Excel, and CSV extractors return a common ExtractionResult object.
This allows the extraction pipeline to process different file formats
without depending on format-specific implementation details.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractedSegment:
    """
    Represent one traceable unit of extracted document content.

    A segment may represent a PDF page, Excel worksheet row, CSV row,
    table, paragraph, or another structural unit.

    Attributes:
        segment_type: The structural category of the extracted content.
        text: The text belonging to this segment.
        locator: Format-specific metadata identifying the source location.
        confidence: Optional extraction confidence, particularly useful
            for OCR results. Values should range from 0 to 1.
    """

    segment_type: str
    text: str
    locator: dict[str, Any] = field(default_factory=dict)
    confidence: float | None = None


@dataclass
class ExtractionResult:
    """
    Represent the complete result of one document extraction operation.

    The result preserves the original extracted text separately from
    normalized text and stores individual segments for traceability.

    Attributes:
        raw_text: Text returned by the extraction engine.
        normalized_text: Text prepared for downstream processing.
        segments: Ordered structural units extracted from the source.
        software_name: Name of the extraction library or engine.
        software_version: Version of the extraction software.
        configuration: Settings used during extraction.
        detected_language: Language detected during extraction, if known.
    """

    raw_text: str = ""
    normalized_text: str = ""
    segments: list[ExtractedSegment] = field(default_factory=list)
    software_name: str = ""
    software_version: str = ""
    configuration: dict[str, Any] = field(default_factory=dict)
    detected_language: str = ""

    @property
    def character_count(self) -> int:
        """
        Return the number of characters in the normalized text.

        This property supports the character-count field in the
        ExtractedContent database model.
        """

        return len(self.normalized_text)

    @property
    def word_count(self) -> int:
        """
        Return the number of whitespace-separated words.

        This is a basic text statistic, not a linguistic token count.
        More advanced terminology tokenization can be added separately.
        """

        return len(self.normalized_text.split())
