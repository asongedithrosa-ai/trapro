# TRAPRO Extraction API Documentation

**Project:** TRAPRO â€“ Legal Knowledge Platform
**Subsystem:** Legal Source Ingestion and Content Extraction
**API Version:** v1
**Base URL:** `/api/v1/`
**Status:** Initial implementation
**Last Updated:** 7 November 2026

---

## 1. Purpose

The TRAPRO Extraction subsystem receives legal and academic source documents, validates and preserves their original files, extracts textual content, and stores the extracted content together with structural information and provenance metadata.

It provides the foundation for subsequent legal terminology processing, including:

- Legal terminology candidate identification.
- Frequency analysis and keyword extraction.
- N-gram and collocation analysis.
- Concordance and contextual analysis.
- Concept identification and terminology standardisation.

The extraction subsystem does not independently determine the legal meaning or equivalence of terminology. Those responsibilities belong to subsequent terminology and knowledge-management subsystems.

## 2. Architecture

The current implementation consists of two Django applications.

### 2.1 Legal sources application

Application: `apps.legal_sources`

Responsibilities:

- Accept uploaded legal and academic documents.
- Validate file extensions, sizes and file signatures.
- Calculate SHA-256 checksums.
- Detect duplicate documents.
- Preserve original uploaded files.
- Store source metadata and ownership information.

Main components:

| Component | Responsibility |
|---|---|
| `models.py` | SourceDocument data model |
| `serializers.py` | Upload request validation |
| `views.py` | Source upload API |
| `services/validators.py` | File validation |
| `services/ingestion.py` | Document ingestion and storage |
| `urls.py` | API route definitions |

### 2.2 Extraction application

Application: `apps.extraction`

Responsibilities:

- Initiate extraction runs.
- Select the appropriate extractor based on file extension.
- Extract and normalise text.
- Preserve document structure and segment locations.
- Store extraction results and metadata.
- Record successful, partial and failed extraction runs.
- Provide authenticated access to extraction results.

Main components:

| Component | Responsibility |
|---|---|
| `models.py` | ExtractionRun, ExtractedContent and ContentSegment |
| `serializers.py` | Extraction result serialization |
| `views.py` | Extraction API endpoints |
| `services/base.py` | Shared extraction result structures |
| `services/extraction_pipeline.py` | Extraction orchestration |
| `services/pdf_extractor.py` | PDF extraction |
| `services/excel_extractor.py` | Excel extraction |
| `services/csv_extractor.py` | CSV extraction |
| `services/docx_extractor.py` | DOCX extraction |
| `services/txt_extractor.py` | Plain-text extraction |
| `urls.py` | Extraction route definitions |

## 3. Extraction workflow

The current workflow is:

1. An authenticated user uploads a source document.
2. The ingestion service validates the document.
3. The system calculates its SHA-256 checksum.
4. Duplicate detection is performed unless duplicates are explicitly allowed.
5. The original file is preserved in media storage.
6. A SourceDocument record is created.
7. The user initiates extraction for that source.
8. The extraction pipeline identifies the file extension.
9. The appropriate extraction service processes the document.
10. Extracted text and structural segments are saved.
11. The extraction run is marked completed, partial or failed.
12. The user retrieves the extraction results through the detail endpoint.

**Processing model:** Extraction is synchronous in the current implementation. The API request waits for extraction to finish.

## 4. Supported document formats

### 4.1 Ingestion support

The source ingestion validator accepts:

| Format | Extension |
|---|---|
| PDF | `.pdf` |
| Microsoft Word | `.docx` |
| Microsoft Excel | `.xlsx`, `.xls` |
| Comma-separated values | `.csv` |
| Plain text | `.txt` |
| Images | `.png`, `.jpg`, `.jpeg`, `.tiff`, `.tif`, `.bmp`, `.webp` |

The current maximum upload size is 50 MB.

### 4.2 Extraction support

The extraction pipeline currently supports:

| Format | Extraction method | Implementation |
|---|---|---|
| PDF | `pdf_text` | PyMuPDF |
| Excel XLSX/XLS | `spreadsheet` | Excel extraction service |
| CSV | `csv` | CSV extraction service |
| DOCX | `docx` | Python DOCX extraction service |
| TXT | `plain_text` | Python standard library |

Image files are accepted during ingestion, but image OCR extraction has not yet been implemented.

A file being accepted during upload does not necessarily mean that its format is currently supported by the extraction pipeline.

## 5. API conventions

All API routes are versioned under:

`/api/v1/`

Requests that access protected endpoints require an authenticated user.

The current API uses Django REST Framework authentication and permission handling configured by the Django project.

Responses use JSON unless the endpoint specifically accepts multipart form data.

UUIDs identify source documents and extraction runs.

## 6. Source document upload

### Endpoint

`POST /api/v1/sources/upload/`

### Purpose

Uploads and registers a legal or academic source document.

### Authentication

Required.

### Content type

`multipart/form-data`

### Request fields

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | String | Yes | Document title |
| `original_file` | File | Yes | Original source document |
| `source_type` | String | No | Source classification |
| `language` | String | No | Document language |
| `jurisdiction` | String | No | Applicable jurisdiction |
| `citation` | String | No | Legal or academic citation |
| `description` | String | No | Additional source description |
| `allow_duplicate` | Boolean | No | Explicitly permits duplicate content |

Available source classifications:

- `legislation`
- `judgment`
- `ohada`
- `academic`
- `other`

Available language values:

- `en`
- `fr`
- `bi`
- `other`

### Successful response

HTTP `201 Created`

The response contains source metadata, including:

- `id`
- `title`
- `original_filename`
- `file_extension`
- `mime_type`
- `file_size`
- `sha256_checksum`
- `source_type`
- `language`
- `jurisdiction`
- `citation`
- `description`
- `uploaded_at`

The response does not expose the internal media storage path.

### Error handling

| HTTP status | Meaning |
|---|---|
| 400 | Invalid upload, unsupported extension, invalid file signature, duplicate or other validation error |
| 401 / 403 | Authentication or permission failure |
| 500 | Unexpected server-side failure |

Identical document contents are rejected by default. The `allow_duplicate` option permits an intentional duplicate.

## 7. Initiating document extraction

### Endpoint

`POST /api/v1/extraction/sources/{source_id}/run/`

### Purpose

Initiates extraction for an already registered source document.

### Authentication

Required.

### URL parameter

`source_id`: UUID of the source document.

### Request body

No additional request body is required.

### Successful response

HTTP `201 Created`

The response contains:

- `id`: Extraction run UUID.
- `source_id`: Source document UUID.
- `source_title`: Source document title.
- `method`: Extraction method.
- `status`: Extraction status.
- `software_name`: Extraction software.
- `software_version`: Software version.
- `created_at`: Run creation timestamp.
- `started_at`: Extraction start timestamp.
- `completed_at`: Extraction completion timestamp.

### Extraction statuses

| Status | Meaning |
|---|---|
| `pending` | Extraction has not started |
| `processing` | Extraction is in progress |
| `completed` | Extraction completed with normalised content |
| `partial` | Extraction completed without usable normalised text |
| `failed` | Extraction failed |

### Error handling

| HTTP status | Meaning |
|---|---|
| 400 | Unsupported extraction format or invalid extraction input |
| 401 / 403 | Authentication or permission failure |
| 404 | Source does not exist or is inaccessible to the user |
| 500 | Unexpected extraction failure |

Unsupported formats are recorded as failed extraction runs before the input error is returned.

Unexpected extraction failures are also recorded. The API returns a generic error rather than exposing internal exception details.

## 8. Retrieving extraction results

### Endpoint

`GET /api/v1/extraction/runs/{run_id}/`

### Purpose

Retrieves an extraction run, its source metadata and its extracted content.

### Authentication

Required.

### URL parameter

`run_id`: UUID of the extraction run.

### Successful response

HTTP `200 OK`

The response contains the following top-level fields:

| Field | Description |
|---|---|
| `id` | Extraction run UUID |
| `source_id` | Source document UUID |
| `source_title` | Source document title |
| `source_original_filename` | Original uploaded filename |
| `source_language` | Source language metadata |
| `source_jurisdiction` | Source jurisdiction |
| `method` | Extraction method |
| `status` | Extraction status |
| `software_name` | Extraction software |
| `software_version` | Software version |
| `configuration` | Extraction configuration |
| `created_at` | Run creation timestamp |
| `started_at` | Extraction start timestamp |
| `completed_at` | Extraction completion timestamp |
| `extracted_content` | Extracted content object or null |

### Extracted content structure

When content is available, `extracted_content` contains:

| Field | Description |
|---|---|
| `id` | Extracted content UUID |
| `raw_text` | Text as initially extracted |
| `normalized_text` | Normalised text |
| `detected_language` | Detected language, if available |
| `character_count` | Normalised character count |
| `word_count` | Normalised word count |
| `created_at` | Content creation timestamp |
| `segments` | Ordered structural content segments |

Each segment contains:

| Field | Description |
|---|---|
| `id` | Segment UUID |
| `segment_type` | Type of structural segment |
| `ordinal` | Segment order |
| `locator` | JSON provenance information |
| `text` | Segment text |
| `confidence` | Optional extraction confidence |

Supported segment types include:

- `page`
- `paragraph`
- `table`
- `row`
- `sheet`
- `image_region`
- `section`
- `other`

The locator stores structural information such as page numbers, paragraph numbers, worksheet names, row numbers and line positions, depending on the extractor.

### Failed extraction response

A failed extraction run can still be retrieved.

When no ExtractedContent record exists, `extracted_content` is returned as `null`.

Internal exception details and the model's `error_message` field are not exposed by the retrieval API.

### Access control

- Ordinary authenticated users can retrieve extraction runs associated with their own uploaded source documents.
- Staff and superusers can retrieve extraction runs associated with other users' documents.
- Inaccessible and nonexistent runs return HTTP `404`, avoiding disclosure of another user's resources.

## 9. Data model and relationships

The extraction subsystem currently uses three principal models.

### 9.1 ExtractionRun

Represents an individual attempt to extract content from a SourceDocument.

Important relationships:

- Many extraction runs may belong to one source document.
- An extraction run records its creator.
- An extraction run has one associated ExtractedContent record at most.

### 9.2 ExtractedContent

Stores the text produced by an extraction run.

Important fields include:

- Raw text.
- Normalised text.
- Detected language.
- Character count.
- Word count.
- Creation timestamp.

Each ExtractedContent record belongs to exactly one ExtractionRun.

### 9.3 ContentSegment

Stores individual structural segments of extracted content.

Examples include PDF pages, DOCX paragraphs, spreadsheet rows and CSV records.

Each segment belongs to one ExtractedContent record.

Segment ordering is preserved through the `ordinal` field. The database enforces uniqueness of the combination of extracted content and ordinal.

### 9.4 Relationship overview

```text
SourceDocument
      |
      | 1
      |
      | N
ExtractionRun
      |
      | 1
      |
      | 0..1
ExtractedContent
      |
      | 1
      |
      | N
ContentSegment
```
## 10. Provenance and traceability

Provenance is important for legal research because extracted terminology must remain traceable to its original documentary context.

TRAPRO preserves:

- The original source document.
- Its SHA-256 checksum.
- Source metadata and jurisdiction.
- Extraction method and software version.
- Extraction configuration.
- Extraction timestamps.
- Raw and normalised text.
- Ordered structural segments.
- Segment-level locator metadata.

These records provide a foundation for connecting future terminology candidates to their original legal sources and contexts.

Extraction provenance does not, by itself, establish the legal validity of a candidate term or its translation.

## 11. Security and data integrity

Current safeguards include:

1. Authentication on source upload and extraction endpoints.
2. Ownership-based access control.
3. Staff and superuser access privileges.
4. File extension and size validation.
5. File signature checks for supported binary formats.
6. SHA-256 content checksums.
7. Duplicate detection.
8. Original file preservation.
9. Generic API error responses for unexpected failures.
10. Exclusion of internal exception messages and storage paths from public API responses.

The API should not be treated as a public anonymous upload service.

## 12. Current limitations

The following capabilities are not yet implemented:

- OCR for scanned PDF documents and image files.
- Image-region text extraction.
- Asynchronous/background extraction processing.
- Extraction retry and job scheduling mechanisms.
- Remote object storage compatibility for the current file-path-based pipeline.
- Advanced language detection and multilingual normalisation.
- Legal terminology candidate generation.
- Terminology validation and expert review.
- Automatic concept identification and legal equivalence assessment.
- Source-sharing and collaborative access policies.

The current extraction pipeline processes documents synchronously and relies on local file paths.

## 13. Planned integration with the terminology subsystem

The next subsystem will consume extracted content to identify terminology candidates.

The planned processing sequence is:

1. Select completed extraction runs.
2. Retrieve normalised text and structural segments.
3. Apply language-specific text preprocessing.
4. Generate word lists and frequency statistics.
5. Identify multi-word expressions and n-grams.
6. Generate concordance/KWIC contexts.
7. Store candidate terms with source and segment provenance.
8. Support candidate review and validation.

The terminology subsystem must preserve the distinction between a legal concept and the language-specific terms used to express that concept.

English and French will be initial working languages, while the data model should accommodate additional languages and jurisdictions.

The initial glossary content will be based on the thesis's Chapter 4 entries.

## 14. Verification and test coverage

The current implementation has been verified using Django's test framework.

Latest verification:

| Verification | Result |
|---|---|
| Full Django test suite | 31 tests passed |
| Extraction API tests | 12 tests passed |
| Extraction pipeline tests | 7 tests passed |
| Legal source API tests | 3 tests passed |
| Legal source ingestion tests | 9 tests passed |
| Django system check | No issues |

The full suite includes tests for:

- PDF extraction and page provenance.
- Excel worksheets and rows.
- CSV multiline records.
- DOCX paragraphs and tables.
- TXT paragraphs and line provenance.
- Failed and unsupported extraction runs.
- Source upload and duplicate detection.
- Authentication and ownership restrictions.
- Extraction result retrieval.
- Protection of internal error details.

The test suite deliberately simulates runtime extraction failures. Corresponding error log tracebacks are expected during those tests and do not indicate test failure.

## 15. API route summary

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/sources/upload/` | Upload and register a source |
| POST | `/api/v1/extraction/sources/{source_id}/run/` | Initiate extraction |
| GET | `/api/v1/extraction/runs/{run_id}/` | Retrieve extraction results |

---

**Document status:** Initial API documentation for the implemented TRAPRO ingestion and extraction subsystem.

**Maintenance rule:** Update this document whenever an API contract, permission rule, extraction method, response structure or subsystem responsibility changes.
