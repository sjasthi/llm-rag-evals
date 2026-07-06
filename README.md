# LLM RAG Evaluation Project

An ICS 499 capstone web application for comparing Retrieval-Augmented
Generation (RAG) configurations and evaluation methods using Metro State
documents.

The application is also a research instrument. Its final purpose is to produce
repeatable evidence about what different RAG evaluation metrics measure, where
they are useful, where they disagree, and how document-collection size and
composition affect retrieval and evaluation results.

## Current Status

FP6 implements browser document administration and normalized multi-format
ingestion. Administrators can upload and list TXT, text-based PDF, and DOCX
files, then replace or delete browser-uploaded documents. Replacement uses
another file of the same type. PHP validates upload status, size, extension, and MIME type; stores files
under random server-controlled names; and calls the Python ingestion bridge.
Python extracts and validates text, then sends every supported format through
the same chunking, MySQL, and ChromaDB workflow. The interface reports status,
chunk counts, and actionable parser errors. Uploaded files remain in ignored
runtime storage.

The FP5 core remains operational. The 27 local
Metro State documents are split into 77 chunks, tracked in MySQL, embedded with
the free local `all-MiniLM-L6-v2` model, and persisted in ChromaDB. The query
helper supports Chroma semantic retrieval with lexical reranking as well as the
earlier keyword baseline. `rag/answer.py` completes the non-GUI RAG round trip
by sending retrieved context to Gemini, returning a grounded answer with
sources, and saving the response and retrieved contexts in MySQL.

The PHP Ask interface now uses that verified workflow through a server-side
JSON endpoint. Users can submit a question in the browser, view the grounded
answer and ranked source excerpts, and see the model, latency, and saved
response ID.

FP7 will create a manually reviewed dataset of at least 25 evaluation
questions, compare metrics on the same stored responses, study failure cases
and corpus-size effects, and present research findings in the dashboard/report.

## Research Direction

The project is not intended to declare one evaluation metric universally best.
It will compare the specific usefulness and limitations of normalized matching,
semantic similarity, expected-source accuracy, refusal correctness,
faithfulness/groundedness, answer relevance, latency, cost, and human review.

The initial research dataset will contain at least 25 reviewed questions across
the current Metro State categories, including answerable and unanswerable
questions. A controlled experiment will compare a smaller or more focused
document collection with the full collection to observe how added documents and
similar distractors affect retrieval and metric behavior. See the
[research plan](docs/research-plan.md) for the detailed questions, experiments,
interpretation rules, and FP6-FP10 roadmap.

## Technology Stack

- HTML, CSS, JavaScript, jQuery, and Bootstrap
- PHP
- MySQL
- Python helper scripts for RAG ingestion and retrieval
- ChromaDB for local vector storage using `all-MiniLM-L6-v2`
- Gemini 2.5 Flash for the initial grounded answer implementation

## Prerequisites

- PHP installed and available from the terminal
- Python 3 installed and available from the terminal
- MySQL 8 installed and running
- PHP PDO MySQL extension enabled
- PHP Fileinfo extension enabled for MIME validation
- PHP `proc_open` enabled so the Ask endpoint can run the Python helper

Ingestion and retrieval do not require an API key. The grounded answer command
requires a Gemini API key stored in the ignored `.env` file.

## Open the Frontend

From the project root, run:

```powershell
cd "C:\path\to\LLM RAG Evaluation Project"
php -S 127.0.0.1:8000
```

Then open this URL in a browser:

```text
http://127.0.0.1:8000/
```

Expected result:

- The RAG Evaluation Workspace page loads.
- The dashboard shows the current Metro State source document count.
- The dashboard shows the number of document categories.
- The page identifies the stack as PHP + MySQL + ChromaDB.
- The Ask section accepts questions and displays a Gemini answer with sources.
- The Documents section uploads, lists, replaces, and deletes supported documents.

To stop the PHP server, return to the terminal and press `Ctrl+C`.

The browser Ask form posts to `api/ask.php`. The endpoint validates the
question, runs the project virtual environment's `rag/answer.py --json`, and
returns structured answer/source data without exposing the Gemini key to the
browser.

The Documents form uses `api/documents.php`. Uploaded files must be UTF-8 TXT,
text-based PDF, or DOCX and no larger than 10 MB. Scanned PDFs without
extractable text and encrypted PDFs are rejected. Replacement and deletion are
limited to browser-uploaded documents, and replacement must keep the same file type.

## FP6 Setup

Run these commands from the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r rag\requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with the local MySQL connection values and set `GEMINI_API_KEY` or
`LLM_API_KEY` for answer generation. Start MySQL, then create the schema and
ingest both storage layers:

```powershell
python rag\ingest.py --init-schema
```

The first run downloads the local embedding model. Expected final output:

```text
Prepared 77 chunks from 27 text documents (chunk size 800, overlap 100).
MySQL now contains 27 documents and 77 chunks.
ChromaDB collection now contains 77 embedded chunks.
```

Rerunning the same command replaces the existing chunk records instead of
creating duplicates.

The Python requirements include `pypdf` and `python-docx`. On Windows, ensure
these lines are enabled in the PHP installation's active `php.ini`:

```ini
extension=pdo_mysql
extension=fileinfo
```

## FP5 Verification Commands

Check the semantic retrieval path:

```powershell
python rag\query.py "When does Fall 2026 registration begin?" --top-k 3
```

The first result should be chunk 0 from
`data/metrostate_documents/academic_calendar/fall_2026.txt` and should state
that registration begins Monday, March 23, 2026. Chroma distance is shown with
each result; lower distance indicates a closer vector match. The lexical score
is used to rerank Chroma candidates when exact terms and phrases matter.

Check the retained keyword baseline:

```powershell
python rag\query.py "When does Fall 2026 registration begin?" --retrieval keyword --top-k 3
```

Run the complete retrieval-to-answer flow:

```powershell
python rag\answer.py "When does Fall 2026 registration begin?"
```

The command retrieves Chroma context, asks Gemini to answer only from that
context, displays the sources, and saves the answer, settings, latency, and
retrieved chunk links in MySQL. Use `--dry-run` to inspect the prompt without an
API call, `--no-save` to skip persistence, or `--json` for machine-readable
output.

The live FP5 verification confirmed both behaviors: an answerable registration
question returned March 23, 2026 with the correct calendar source, and an
unsupported question returned the configured “not enough information” refusal.

Check PHP syntax:

```powershell
php -l index.php
php -l config\env.php
php -l config\database.php
```

Run the Python unit tests:

```powershell
python -m unittest discover -s tests -v
```

The current suite contains 17 tests covering TXT/PDF/DOCX loading, empty and
binary input rejection, metadata-preserving chunking, stable IDs, retrieval
reranking, grounded prompts, refusal instructions, answer orchestration, and a
frontend regression check for safe document-list element creation.

## Database Schema

The initial MySQL schema is stored in:

```text
database/schema.sql
```

It defines tables for:

- documents
- document chunks
- evaluation questions
- model settings
- evaluation runs
- RAG responses
- retrieved contexts
- evaluation scores

`rag/ingest.py --init-schema` imports this schema and safely applies the FP5 and
FP6 ingestion columns to an earlier database. FP6 adds the original uploaded
filename while preserving the server-controlled storage path separately.

## Configuration

Copy `.env.example` to `.env` for local database values and the Gemini key.

Do not commit `.env`.

Current safe example values are stored in:

```text
.env.example
```

## Planning Documents

- [Requirements](requirements.md)
- [Final project scope](docs/final-project-scope.md)
- [FP3-FP10 project plan](docs/fp3-project-plan.md)
- [UX design](docs/ux-design.md)
- [Code structure and conventions](docs/code-structure.md)
- [Recommended implementation approach](docs/implementation-approach.md)
- [RAG evaluation research plan](docs/research-plan.md)

## Source Documents

The initial Metro State document dataset is stored in
`data/metrostate_documents/`. These files were copied from the Student Compass
reference repository's `documents/` folder and will be used for ingestion,
retrieval, and evaluation work.

Current local source set:

- 27 text documents
- 8 document categories

FP6 adds browser upload and server-side parsing for TXT, text-based PDF, and
DOCX documents. Uploaded files and generated vector data remain local runtime
data and must not be committed.

## Security

Do not commit API keys, database passwords, private Metro State documents, or
uploaded user files. Use local environment configuration for secrets. The
upload endpoint enforces extension/MIME agreement, a 10 MB limit, randomized
storage names, parser validation, and server-side-only processing.
