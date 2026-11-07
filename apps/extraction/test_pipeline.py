
"""
TRAPRO Extraction Pipeline Tests
================================

These tests verify the shared extraction pipeline.

Coverage:
    1. PDF extraction and page-level provenance.
    2. Excel worksheet and row-level preservation.
    3. CSV headers and multiline legal contexts.
    4. Database persistence.
    5. Unsupported-format handling.
    6. Extraction failure recording.

Temporary media storage is used to ensure that tests do not
modify actual project documents or media files.
"""

import tempfile
from io import BytesIO
from unittest.mock import Mock, patch

import pymupdf
from docx import Document
from openpyxl import Workbook

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.extraction.models import (
    ExtractionRun,
    ExtractedContent,
)

from apps.extraction.services.extraction_pipeline import (
    EXTRACTORS,
    run_extraction,
)

from apps.legal_sources.models import SourceDocument
from apps.legal_sources.services.ingestion import create_source_document


class ExtractionPipelineTests(TestCase):
    """Test the complete extraction and persistence workflow."""

    def setUp(self):
        """Configure isolated media storage for each test."""

        self.temp_media = tempfile.TemporaryDirectory()

        self.media_settings = override_settings(
            MEDIA_ROOT=self.temp_media.name
        )

        self.media_settings.enable()

        self.addCleanup(self.media_settings.disable)
        self.addCleanup(self.temp_media.cleanup)

    def make_pdf(self):
        """Generate a small valid PDF entirely in memory."""

        document = pymupdf.open()

        page = document.new_page()

        page.insert_text(
            (72, 72),
            "TRAPRO Extraction Test",
        )

        page.insert_text(
            (72, 100),
            "Contract law and civil liability.",
        )

        pdf_bytes = document.tobytes()

        document.close()

        return pdf_bytes

    def make_excel(self):
        """Generate a small Excel workbook in memory."""

        workbook = Workbook()

        worksheet = workbook.active
        worksheet.title = "Terminology"

        worksheet.append(["Term", "Frequency"])
        worksheet.append(["Contract", 25])
        worksheet.append(["Civil liability", 12])

        output = BytesIO()

        workbook.save(output)
        workbook.close()

        return output.getvalue()

    def make_source(self, filename, content, content_type):
        """Create a source document using the normal ingestion service."""

        uploaded_file = SimpleUploadedFile(
            filename,
            content,
            content_type=content_type,
        )

        return create_source_document(
            uploaded_file,
            title=f"Pipeline Test: {filename}",
            source_type="other",
            language="en",
            allow_duplicate=True,
        )

    def test_pdf_extraction_and_database_persistence(self):
        """Verify PDF extraction, content storage, and page provenance."""

        source = self.make_source(
            "pipeline_test.pdf",
            self.make_pdf(),
            "application/pdf",
        )

        run = run_extraction(source)

        self.assertEqual(run.status, "completed")
        self.assertEqual(run.method, "pdf_text")

        self.assertTrue(
            ExtractionRun.objects.filter(pk=run.pk).exists()
        )

        content = ExtractedContent.objects.get(
            extraction_run=run
        )

        self.assertIn(
            "Contract law and civil liability",
            content.normalized_text,
        )

        self.assertGreater(content.character_count, 0)
        self.assertGreater(content.word_count, 0)

        self.assertEqual(content.segments.count(), 1)

        segment = content.segments.first()

        self.assertEqual(segment.segment_type, "page")
        self.assertEqual(
            segment.locator["page_number"],
            1,
        )

    def test_excel_extraction_preserves_rows_and_sheets(self):
        """Verify Excel worksheet and row metadata are persisted."""

        source = self.make_source(
            "pipeline_test.xlsx",
            self.make_excel(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        run = run_extraction(source)

        self.assertEqual(run.status, "completed")
        self.assertEqual(run.method, "spreadsheet")

        content = run.extracted_content

        self.assertEqual(content.segments.count(), 4)

        row_segments = content.segments.filter(
            segment_type="row"
        )

        sheet_segments = content.segments.filter(
            segment_type="sheet"
        )

        self.assertEqual(row_segments.count(), 3)
        self.assertEqual(sheet_segments.count(), 1)

        first_row = row_segments.first()

        self.assertEqual(
            first_row.locator["worksheet"],
            "Terminology",
        )

        self.assertEqual(
            first_row.locator["row_number"],
            1,
        )

    def test_csv_preserves_multiline_legal_context(self):
        """Verify quoted multiline CSV fields remain one record."""

        csv_content = (
            'Term,Frequency,Context\n'
            'Contract,25,"The contract creates legal obligations.\n'
            'It establishes rights between the parties.\n'
            'It may also define remedies."\n'
            'Civil liability,12,"Civil liability arises from a wrongful act."\n'
        )

        source = self.make_source(
            "pipeline_test.csv",
            csv_content.encode("utf-8"),
            "text/csv",
        )

        run = run_extraction(source)

        self.assertEqual(run.status, "completed")
        self.assertEqual(run.method, "csv")

        content = run.extracted_content

        self.assertEqual(content.segments.count(), 3)

        contract_segment = content.segments.get(
            ordinal=2
        )

        self.assertIn(
            "It establishes rights between the parties.",
            contract_segment.text,
        )

        self.assertIn(
            "It may also define remedies.",
            contract_segment.text,
        )

        self.assertEqual(
            contract_segment.locator["row_number"],
            2,
        )

    def test_docx_extraction_preserves_paragraphs_and_tables(self):
        """Verify DOCX extraction and database persistence."""

        source = self.make_source(
            "pipeline_test.docx",
            self.make_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        run = run_extraction(source)

        self.assertEqual(run.status, "completed")
        self.assertEqual(run.method, "docx")

        content = run.extracted_content

        # Verify extracted document content.
        self.assertIn(
            "Contractual obligations must be performed in good faith.",
            content.normalized_text,
        )

        self.assertIn(
            "Civil liability",
            content.normalized_text,
        )

        self.assertIn(
            "The terminology table supports legal analysis.",
            content.normalized_text,
        )

        # Verify paragraph and table-row preservation.
        paragraph_segments = content.segments.filter(
            segment_type="paragraph"
        )

        row_segments = content.segments.filter(
            segment_type="row"
        )

        table_segments = content.segments.filter(
            segment_type="table"
        )

        self.assertEqual(paragraph_segments.count(), 4)
        self.assertEqual(row_segments.count(), 3)
        self.assertEqual(table_segments.count(), 1)

        # Verify table row metadata.
        contract_row = row_segments.get(
            ordinal=5
        )

        self.assertEqual(
            contract_row.locator["table_number"],
            1,
        )

        self.assertEqual(
            contract_row.locator["row_number"],
            2,
        )

        self.assertIn(
            "Contract",
            contract_row.text,
        )

        # Verify extraction software metadata.
        self.assertEqual(
            run.software_name,
            "python-docx",
        )

    def test_txt_extraction_preserves_paragraphs_and_provenance(self):
        """
        Verify TXT extraction, paragraph persistence, and line provenance.
        """

        # Create a plain-text legal document with two paragraphs.
        txt_content = (
            "Contractual obligations must be performed in good faith.\n"
            "The parties must respect their agreements.\n"
            "\n"
            "Civil liability arises from a wrongful act.\n"
            "It may result in an obligation to compensate."
        )

        source = self.make_source(
            "pipeline_test.txt",
            txt_content.encode("utf-8"),
            "text/plain",
        )

        # Execute the shared extraction pipeline.
        run = run_extraction(source)

        # Verify the extraction outcome.
        self.assertEqual(run.status, "completed")
        self.assertEqual(run.method, "plain_text")

        # Verify the persisted extracted content.
        content = run.extracted_content

        self.assertEqual(content.raw_text, txt_content)
        self.assertIn(
            "Contractual obligations",
            content.normalized_text,
        )
        self.assertIn(
            "Civil liability arises",
            content.normalized_text,
        )

        # Verify paragraph segmentation.
        self.assertEqual(content.segments.count(), 2)

        first_paragraph = content.segments.get(ordinal=1)
        second_paragraph = content.segments.get(ordinal=2)

        self.assertEqual(
            first_paragraph.segment_type,
            "paragraph",
        )

        self.assertEqual(
            first_paragraph.locator["paragraph_number"],
            1,
        )

        self.assertEqual(
            first_paragraph.locator["start_line"],
            1,
        )

        self.assertEqual(
            first_paragraph.locator["end_line"],
            2,
        )

        self.assertEqual(
            second_paragraph.locator["paragraph_number"],
            2,
        )

        self.assertEqual(
            second_paragraph.locator["start_line"],
            4,
        )

        self.assertEqual(
            second_paragraph.locator["end_line"],
            5,
        )

        # Verify extraction software and encoding metadata.
        self.assertEqual(
            run.software_name,
            "Python Standard Library",
        )

        self.assertEqual(
            run.configuration["file_format"],
            "txt",
        )

        self.assertEqual(
            run.configuration["encoding"],
            "utf-8-sig",
)

        # Verify persisted text statistics.
        self.assertEqual(
            content.character_count,
            len(content.normalized_text),
        )

        self.assertEqual(
            content.word_count,
            len(content.normalized_text.split()),
        )

    def test_unsupported_format_creates_failed_run(self):
        """Verify unsupported formats are recorded before raising."""

        source = self.make_source(
            "pipeline_test.pdf",
            self.make_pdf(),
            "application/pdf",
        )

        # Simulate an unsupported original filename.
        source.original_filename = "pipeline_test.rtf"

        source.save(
            update_fields=["original_filename"]
        )

        with self.assertRaisesMessage(
            ValueError,
            "Unsupported extraction format",
        ):
            run_extraction(source)

        failed_run = ExtractionRun.objects.get(
            source_document=source
        )

        self.assertEqual(failed_run.status, "failed")
        self.assertEqual(failed_run.method, "other")

        self.assertIn(
            ".rtf",
            failed_run.error_message,
        )

    def test_extraction_failure_is_recorded(self):
        """Verify runtime failures are saved and re-raised."""

        source = self.make_source(
            "pipeline_test.pdf",
            self.make_pdf(),
            "application/pdf",
        )

        # Simulate an extractor failure without corrupting
        # the actual PDF or changing the production extractor.
        with patch.dict(
            EXTRACTORS,
            {
                ".pdf": Mock(
                    side_effect=RuntimeError(
                        "Simulated extraction failure"
                    )
                )
            },
        ):

            with self.assertRaisesMessage(
                RuntimeError,
                "Simulated extraction failure",
            ):
                run_extraction(source)

        failed_run = ExtractionRun.objects.get(
            source_document=source
        )

        self.assertEqual(failed_run.status, "failed")

        self.assertEqual(
            failed_run.error_message,
            "Simulated extraction failure",
        )

        # A failed extraction must not delete the original source.
        self.assertTrue(
            SourceDocument.objects.filter(
                pk=source.pk
            ).exists()
        )

    def make_docx(self):
        """Generate a small legal DOCX document entirely in memory."""

        document = Document()

        document.add_heading(
            "TRAPRO DOCX Pipeline Test",
            level=0,
        )

        document.add_paragraph(
            "Contractual obligations must be performed in good faith."
        )

        document.add_heading(
            "Legal Terminology",
            level=1,
        )

        table = document.add_table(
            rows=1,
            cols=2,
        )

        table.style = "Table Grid"

        headers = table.rows[0].cells
        headers[0].text = "Legal Term"
        headers[1].text = "Domain"

        records = [
            ("Contract", "Contract Law"),
            ("Civil liability", "Civil Liability"),
        ]

        for term, domain in records:
            cells = table.add_row().cells
            cells[0].text = term
            cells[1].text = domain

        document.add_paragraph(
            "The terminology table supports legal analysis."
        )

        output = BytesIO()

        document.save(output)

        return output.getvalue()
