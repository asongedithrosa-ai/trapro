# TRAPRO — Legal Knowledge Platform

**TRAPRO** is a multilingual legal knowledge platform being developed to support the extraction, organisation, analysis, standardisation, and retrieval of legal terminology and knowledge within Cameroon’s bijural legal landscape.

The project is grounded in the research presented in the thesis:

*Extraction and Standardisation of Contract and Civil Liability Terminology in Cameroon’s Bijural Landscape.*

The initial development phase establishes the legal-source ingestion and document-extraction foundation upon which subsequent terminology-management and knowledge-representation subsystems will be built.

---

## 1. Project vision

TRAPRO aims to provide a structured environment for managing legal terminology and legal knowledge across languages and jurisdictions.

Its long-term objectives include:

- Extracting relevant content from legal and academic documents.
- Identifying and analysing legal terminology candidates.
- Supporting terminology validation and standardisation.
- Preserving the relationship between legal concepts and their language-specific expressions.
- Representing legal concepts, definitions, relationships, and provenance.
- Supporting English and French initially, with room for additional languages.
- Supporting Cameroon initially, with an architecture designed to accommodate other African jurisdictions.
- Providing traceability between terminology records and their original legal sources.

The platform is intended to evolve from a research-based legal glossary into a scalable legal knowledge-management system.

## 2. Research foundation

The initial research foundation includes:

- Cabré’s Communicative Theory of Terminology.
- Šarčević’s Functional Equivalence approach.
- Cameroon civil-law and common-law legal contexts.
- Contract and civil liability terminology.
- Relevant legislation, judgments, OHADA instruments, and academic sources.
- Corpus-based terminology analysis, including frequency lists, multi-word expressions, concordances, and contextual analysis.

The initial glossary content will be based on the detailed entries in Chapter 4 of the underlying thesis.

A central design principle is that a legal concept must remain distinct from the terms used to express it in different languages. Translation alone must not be treated as proof of legal equivalence.

## 3. Current development status

<details>
<summary>Implemented functionality</summary>

### Legal source ingestion

- Source document registration and storage.
- UUID-based source identification.
- File extension and size validation.
- File signature validation for supported formats where applicable.
- SHA-256 checksum calculation.
- Duplicate source detection.
- Source metadata management.
- Authenticated source upload.

### Document extraction

- PDF text extraction.
- DOCX text extraction.
- Excel workbook extraction (`.xlsx` and `.xls`).
- CSV extraction.
- Plain-text extraction.
- Extraction run tracking.
- Extraction status management.
- Raw and normalised text storage.
- Structured content segments and source locators.
- Extraction software and configuration metadata.
- Extraction result retrieval.
- Ownership-based access restrictions.

### API

- Authenticated source upload endpoint.
- Authenticated extraction initiation endpoint.
- Authenticated extraction result retrieval endpoint.
- Serialisation of extraction results.
- Controlled error responses.

</details>

### Not yet implemented

The following are planned capabilities, not completed features:

- OCR for scanned documents and images.
- Background extraction processing.
- Extraction retries and job scheduling.
- Remote object storage integration.
- Advanced multilingual language detection and normalisation.
- Terminology candidate generation.
- Terminology validation and expert review.
- Legal concept identification and equivalence assessment.
- Knowledge graph and ontology integration.
- Public terminology search and professional platform features.
- Frontend application.

## 4. Technology stack

| Component | Technology |
|---|---|
| Backend framework | Django 5.2 |
| API framework | Django REST Framework |
| Primary database target | PostgreSQL |
| Development database option | SQLite |
| Environment configuration | django-environ |
| Cross-origin resource sharing | django-cors-headers |
| PDF extraction | PyMuPDF |
| Excel extraction | openpyxl, xlrd |
| Word document extraction | python-docx |
| Backend language | Python |
| Version control | Git and GitHub |

The frontend framework has not yet been introduced. React or Next.js will be considered during the frontend development phase.

## 5. Project architecture

The current backend separates legal source management from document extraction.

```text
TRAPRO/
│
├── apps/
│   ├── __init__.py
│   │
│   ├── legal_sources/
│   │   ├── migrations/
│   │   ├── services/
│   │   │   ├── ingestion.py
│   │   │   └── validators.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── admin.py
│   │
│   └── extraction/
│       ├── migrations/
│       ├── services/
│       │   ├── base.py
│       │   ├── csv_extractor.py
│       │   ├── docx_extractor.py
│       │   ├── excel_extractor.py
│       │   ├── extraction_pipeline.py
│       │   ├── pdf_extractor.py
│       │   └── txt_extractor.py
│       ├── models.py
│       ├── serializers.py
│       ├── views.py
│       ├── urls.py
│       └── test_pipeline.py
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── documentation/
│   └── extraction_api.md
│
├── infrastructure/
│
├── tests/
│   └── fixtures/
│       └── extraction/
│
├── media/
├── .env.example
├── .gitignore
├── manage.py
└── requirements.txt
```
### 5.1 Legal sources subsystem
Responsible for:
- Receiving source documents.
- Validating uploaded files.
- Recording source metadata.
- Calculating checksums.
- Detecting duplicate documents.
- Managing original source files.

### 5.2 Extraction subsystem
Responsible for:
- Selecting the appropriate extraction method.
- Processing supported document formats.
- Recording extraction runs.
- Storing extracted content.
- Preserving structural segments and locators.
- Recording extraction metadata and status.

### 5.3 Planned terminology subsystem
The next major subsystem will consume extracted content to:
1. Select completed extraction runs.
2. Retrieve normalised text and structural segments.
3. Perform language-specific preprocessing.
4. Generate word lists and frequency statistics.
5. Identify multi-word expressions and n-grams.
6. Generate concordance and KWIC contexts.
7. Register terminology candidates with source provenance.
8. Support review and validation.

## 6. Requirements
Software prerequisites
- Python 3.13 or a compatible Python version supported by the project dependencies.
- pip.
- Git.
- PostgreSQL for PostgreSQL-based development or deployment.
- Windows PowerShell, or an equivalent terminal.
Python dependencies
Dependencies are declared in requirements.txt.

##### The current dependency list includes:
- Django
- Django REST Framework
- django-cors-headers
- django-environ
- psycopg
- PyMuPDF
- openpyxl
- xlrd
- python-docx

## 7. Local installation
The following instructions use Windows PowerShell or command prompt(cmd).

##### Step 1: Clone the repository
```
git clone https://github.com/asongedithrosa-ai/trapro.git
cd trapro

```
##### Step 2: Create a virtual environment
```
python -m venv .venv
```
##### Step 3: Activate the virtual environment
```.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the virtual environment's Python executable directly:

```
 .\.venv\Scripts\python.exe --version 

```

#### Step 4: Install dependencies
```
python -m pip install -r requirements.txt

```

If the virtual environment is not activated:
```
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

```

##### Step 5: Create the environment file
- Copy the example configuration:
- Copy-Item .env.example .env

- Edit .env and configure the secret key, database credentials, and allowed hosts.
- Never commit .env or publish database credentials and secret keys.


## 8. Environment configuration
TRAPRO supports PostgreSQL and SQLite through the DB_ENGINE environment variable.
SQLite development configuration
The example environment file provides SQLite as its default database option.
```
DB_ENGINE=sqlite

SECRET_KEY=replace-with-a-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1


SQLite stores its database in the project root as db.sqlite3.
PostgreSQL configuration
For PostgreSQL, configure the following variables:
DB_ENGINE=postgresql

SECRET_KEY=replace-with-a-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=trapro_db
DB_USER=trapro_user
DB_PASSWORD=replace-with-database-password
DB_HOST=localhost
DB_PORT=5432
```

- Use the default sqlite or create PostgreSQL database and user before running migrations.

- Use secure, unique credentials and a properly generated Django secret key.

- The .env.example file provides the complete configuration template.


## 9. Database setup
After configuring the environment, apply database migrations:
python manage.py migrate

Create an administrator account:
```
python manage.py createsuperuser

```

Check the project configuration:
```
python manage.py check

```

Check migration consistency:
```
python manage.py makemigrations --check --dry-run

```

## 10. Run the development server
Start Django:
```
python manage.py runserver

```

The local development server will normally be available at:
http://127.0.0.1:8000/


The Django administration interface is available at:
http://127.0.0.1:8000/admin/


## 11. API documentation
The current API is versioned under:
```
/api/v1/

Available endpoints
Method	Endpoint	Purpose
POST	/api/v1/sources/upload/	Upload and register a legal source
POST	/api/v1/extraction/sources/{source_id}/run/	Initiate document extraction
GET	/api/v1/extraction/runs/{run_id}/	Retrieve extraction results
```

All three endpoints require authentication.

Ordinary users can access their own source documents and extraction runs. Staff and superusers have broader access according to the implemented permissions.
API documentation reference
See documentation/extraction_api.md for:
- Request fields and response structures.
- Authentication requirements.
- Extraction methods and statuses.
- Data models and relationships.
- Provenance and traceability.
- Access control.
- Error handling.
- Current limitations.

## 12. Supported document formats
Ingestion support
The source ingestion layer currently accepts:
- PDF
- DOCX
- XLSX
- XLS
- CSV
- TXT
- PNG
- JPG and JPEG
- TIFF and TIF
- BMP
- WEBP
Extraction support
The implemented extraction pipeline currently supports:
Format	Extraction method
PDF	Text extraction
DOCX	Word document extraction
XLSX	Spreadsheet extraction
XLS	Spreadsheet extraction
CSV	CSV extraction
TXT	Plain-text extraction

Note: Accepting an image file during ingestion does not mean that image OCR is available. OCR and image-region extraction remain planned features.

## 13. Testing
Run the complete Django test suite:
```
python manage.py test -v 2

```

Run extraction API tests:
```
python manage.py test apps.extraction.test_api -v 2

```

Run extraction pipeline tests:
```
python manage.py test apps.extraction.test_pipeline -v 2

```


Run legal source ingestion tests:
````
python manage.py test apps.legal_sources.tests.test_ingestion -v 2

````


Run legal source API tests:
```
python manage.py test apps.legal_sources.tests.test_api -v 2

```

The test suite covers source ingestion, duplicate detection, extraction methods, extraction status handling, API authentication, access restrictions, and extraction result retrieval.

Some tests deliberately simulate extraction failures. Corresponding error logs are expected when those tests pass.

## 14. Security and data management
The current implementation includes:
- Authentication on source and extraction API endpoints.
- Ownership-based access restrictions for ordinary users.
- File extension, size, and signature validation where applicable.
- SHA-256 source checksums.
- Duplicate document detection.
- Controlled API error responses.
- Separation of original source files and extracted content.
- Environment-based configuration.
Development and deployment must also follow these practices:
- Never commit .env.
- Never commit real database credentials or secret keys.
- Keep production DEBUG disabled.
- Configure production ALLOWED_HOSTS explicitly.
- Use HTTPS in production.
- Restrict database access.
- Back up original legal sources and their metadata.
- Review source-document access policies before introducing public sharing.

## 15. Development roadmap
The project will evolve through clearly separated subsystems.
Stage	Subsystem / activity	Status
1	Django project foundation and configuration	Implemented
2	Legal source ingestion	Implemented
3	Document extraction pipeline	Implemented
4	Extraction API and documentation	Implemented
5	Terminology candidate generation	Planned
6	Terminology validation and standardisation	Planned
7	Multilingual legal concept management	Planned
8	Ontology and knowledge graph integration	Planned
9	Search, retrieval, and professional features	Planned
10	Frontend application	Planned
11	Production deployment and scaling	Planned

The development process will use object-oriented analysis and design, incremental implementation, testing, version control, and subsystem documentation.

Data models and entity-relationship diagrams will be documented as the platform evolves.

## 16. Contribution and development conventions
Development should preserve the project's research foundation and architectural boundaries.

Contributors should:
1. Keep subsystem responsibilities clearly separated.
2. Document model and API changes.
3. Include meaningful comments in code.
4. Add tests for new functionality.
5. Preserve source provenance and extraction traceability.
6. Avoid treating language-specific terms as interchangeable legal concepts without validation.
7. Update relevant documentation whenever API contracts or subsystem responsibilities change.
8. Use clear, descriptive Git commit messages.
Example:
```
git add .

git commit -m "Add terminology candidate generation"

```

## 17. Project status
TRAPRO is under active development.

The current implementation establishes the backend foundation for legal-source ingestion and document extraction. Terminology analysis, standardisation, knowledge representation, and the frontend will be developed incrementally.

Repository: asongedithrosa-ai/trapro

Documentation: documentation/extraction_api.md

Project: TRAPRO — Legal Knowledge Platform