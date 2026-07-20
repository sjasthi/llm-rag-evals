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
another file of the same type. PHP validates upload status, size, extension,
and MIME type; stores files
under random server-controlled names; and calls the Python ingestion bridge.
Python extracts and validates text, then sends every supported format through
the same chunking, MySQL, and ChromaDB workflow. The interface reports status,
chunk counts, and actionable parser errors. Uploaded files remain in ignored
runtime storage. Dashboard document/category counts update from the indexed
database records after each upload, replacement, deletion, or manual refresh.

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

FP7 is implemented and verified. The repository includes an
idempotent, versioned 25-question reviewed dataset with expected answers, sources,
evidence, accepted variants, required facts, category, difficulty, and
answerability metadata. The redesigned task-focused browser explains the full
Sources -> Dataset -> Experiments -> Findings workflow. Dataset cards expose
cited evidence and manual review controls, while Experiments shows dataset/run
coverage, limited or failed run explanations, compact run navigation, and an
automatically populated response inspector. The additive
schema stores evaluator definitions plus heterogeneous raw per-response results.
Eight local evaluators are registered: exact/contains, required-fact coverage,
token F1, ROUGE-L, embedding semantic similarity, BERTScore, expected-source
accuracy, and refusal correctness. A controlled runner generates each reviewed answer once, saves its
exact contexts, and applies evaluators to that saved response. The first live
three-question baseline completed successfully with 24 stored evaluator results.
The 25 questions are reviewed test cases available to experiments; only three
unique questions were executed in this bounded proof run. A complete
25-question baseline remains a deliberate later experiment, not an FP7 claim.

FP8 and FP9 application support is now implemented and locally verified. Five
advanced definitions join the eight baselines: a versioned structured
LLM-as-judge rubric plus RAGAS Faithfulness, Response Relevancy, Context
Precision, and Context Recall. Immutable evaluator attempts preserve raw
provider output, configuration, usage, runtime, cost, skips, and failures, while
a latest-attempt canonical row keeps browser reads simple. New controlled runs
freeze dataset/settings/document-manifest provenance and can compare Chroma
with genuine MySQL FULLTEXT retrieval or use reproducible category subsets.

The Experiments browser now explains four independent evidence layers
(baseline, advanced, human, and operations), shows every score's basis,
calculation, scale, threshold status, and limitation, exposes attempt
variability, and supports versioned evidence-backed human response reviews.
Findings compares run coverage/configuration and summarizes each evaluator
independently; it does not combine unlike metrics into a mystery grade.

No paid advanced evaluation was executed during implementation. The advanced
runner's dry-run and compatibility path are verified, but real RAGAS/judge
scores and empirical FP9 conclusions require an explicitly authorized,
cost-bounded run. See the detailed
[FP8/FP9 implementation record](docs/fp8-fp9-implementation.md).

## Research Direction

The project is not intended to declare one evaluation metric universally best.
It will compare the specific usefulness and limitations of normalized matching,
semantic similarity, expected-source accuracy, refusal correctness,
faithfulness/groundedness, answer relevance, latency, cost, and human review.

Dataset version 1.0 contains 25 reviewed questions across the current Metro
State categories, including answerable and unanswerable questions. A controlled
experiment will compare a smaller or more focused
document collection with the full collection to observe how added documents and
similar distractors affect retrieval and metric behavior. See the
[research plan](docs/research-plan.md) for the detailed questions, experiments,
interpretation rules, and FP6-FP10 roadmap.
The [evaluation strategy](docs/evaluation-strategy.md) defines the proposed ten
evaluator types, controlled protocol, trade-off questions, and FP7 resume point.

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

MySQL and PHP are separate processes. Start the installed MySQL server first;
opening the PHP application does not start MySQL automatically. Then, from the
project root, run:

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
- Overview explains the Sources -> Dataset -> Experiments -> Findings lifecycle
  and shows live corpus, category, reviewed-question, and evaluator counts.
- Playground accepts questions and displays a Gemini answer with ranked sources.
- Dataset shows the sampled gold test set, cited evidence, filters, and manual
  review status. `Reviewed` means source-verified; it does not mean the question
  has already been sent through an experiment.
- Experiments shows each run's coverage against the 25-question dataset, saved
  responses, generated/reference answers, evaluator signals, and retrieved
  evidence. The newest available response opens automatically.
- Sources uploads, lists, replaces, and deletes supported documents.
- Findings shows live run/configuration comparisons, interpretation rules, and
  the score contract and observed same-metric range for all 13 evaluators.

To stop the PHP server, return to the terminal and press `Ctrl+C`.

The browser Ask form posts to `api/ask.php`. The endpoint validates the
question, runs the project virtual environment's `rag/answer.py --json`, and
returns structured answer/source data without exposing the Gemini key to the
browser.

The Documents form uses `api/documents.php`. Uploaded files must be UTF-8 TXT,
text-based PDF, or DOCX and no larger than 10 MB. Scanned PDFs without
extractable text and encrypted PDFs are rejected. Replacement and deletion are
limited to browser-uploaded documents, and replacement must keep the same file
type. Deletion removes the uploaded file, MySQL record/chunks, and matching
ChromaDB vectors; the 27 bundled Metro State documents are protected.

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

Check genuine MySQL chunk retrieval:

```powershell
python rag\query.py "When does Fall 2026 registration begin?" --retrieval mysql --top-k 3
```

Check the retained filesystem keyword troubleshooting baseline:

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

The current suite contains 34 tests covering TXT/PDF/DOCX loading, empty and
binary input rejection, metadata-preserving chunking, stable IDs, retrieval
reranking, grounded prompts, refusal instructions, answer orchestration, local
evaluators, advanced evaluator mapping/applicability/cost/failure isolation,
score contracts, and frontend evaluation-layer regressions.

## FP7 Evaluation Foundation

Apply the additive schema and seed the versioned reviewed dataset:

```powershell
python rag\ingest.py --init-schema --json
python rag\evaluation.py --seed --json
```

Review questions in the browser before running paid generation. Only active
questions marked `reviewed` are selected by the runner. A bounded proof run is:

```powershell
python rag\run_evaluation.py --dataset-id 5 --limit 3 --json
```

Use the dataset ID returned by the seed command; it may differ on another
database. To apply or reapply selected local evaluators to an existing saved
response without regenerating it:

```powershell
python rag\evaluation.py --response-id 17 --evaluators exact_contains,rouge_l,semantic_similarity,bertscore --json
```

Use the actual saved response ID. Semantic similarity uses the local
`all-MiniLM-L6-v2` model and may download model dependencies on first use.
BERTScore uses `distilbert-base-uncased`. Both models are cached after their
first load in a runner process. The current thresholds are descriptive research
starting points, not universal pass/fail standards.

### Dataset Review Versus Experiment Execution

The evaluation dataset is a representative answer key, not a response history
and not one question per source document. A reviewer or subject-matter expert
checks each expected answer against its cited authoritative evidence. The three
review states control test-case eligibility:

- `reviewed`: source-verified and eligible for controlled runs;
- `needs_revision`: the question, reference answer, or evidence needs correction;
- `draft`: still being prepared and excluded from runs.

An experiment run then selects some or all reviewed questions and generates one
saved response per selected question under fixed settings. The verified FP7
proof used `--limit 3`, so it created three responses and eight evaluator
results per response. Reviewing 25 test cases and executing three questions are
therefore separate, intentional facts.

## FP8/FP9 Advanced Evaluation and Findings

Apply current migrations and refresh all 13 versioned evaluator contracts:

```powershell
python rag\ingest.py --init-schema --json
python rag\evaluation.py --seed --json
```

Always preview advanced work first. This command reads response 17 and reports
applicable, reused, and skipped methods without calling an external model:

```powershell
python rag\run_advanced_evaluation.py --response-id 17 --dry-run --json
```

External advanced calls require the deliberate `--allow-paid` flag as well as
application and estimated-cost caps. Configure evaluator provider/model and
current per-million token prices in `.env`; zero price defaults mean "price not
configured," not "free." The runner can preserve 1-10 attempts per method and
reuses a completed active-version result unless `--force` is specified.

The RAGAS integration uses its modern collections API and pins
`ragas==0.4.3` with `langchain-community==0.4.1` for compatibility. RAGAS and
the judge operate on the already-saved answer and ordered contexts; they never
regenerate the RAG answer.

Create new controlled runs with explicit retrieval and experiment metadata:

```powershell
python rag\run_evaluation.py --dataset-id 5 --limit 1 `
  --retrieval mysql_keyword --top-k 3 `
  --experiment-key retrieval-method-v1 `
  --corpus-variant full-current --json
```

Use the actual dataset ID returned locally. New runs freeze their dataset,
retrieval/generation settings, category subset, ordered document manifest and
hash, and evaluator list. Existing FP7 runs are honestly labeled as partial
legacy provenance.

Open `#results` for the four-layer response inspector and response-review
rubric. Open `#report` for the Findings workspace. Dataset review controls
verify expected test data; the human-review form separately evaluates a saved
generated response using the shown reference and contexts.

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
- evaluator definitions and latest canonical results
- immutable evaluator result attempts
- versioned human response reviews

`rag/ingest.py --init-schema` imports the schema and applies ordered migrations.
FP8/FP9 add run provenance, immutable attempts, human reviews, and the MySQL
FULLTEXT index while preserving earlier data. Legacy runs are explicitly
labeled as partial provenance rather than assigned invented historical values.

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
- [Evaluator strategy and controlled protocol](docs/evaluation-strategy.md)
- [FP8/FP9 implementation record and reproduction guide](docs/fp8-fp9-implementation.md)

## Source Documents

The initial Metro State document dataset is stored in
`data/metrostate_documents/`. These files were copied from the Student Compass
reference repository's `documents/` folder and will be used for ingestion,
retrieval, and evaluation work.

Current local source set:

- 27 text documents
- 8 document categories

FP6 adds browser upload, live listing/counts, protected replacement/deletion,
and server-side parsing for TXT, text-based PDF, and DOCX documents. Uploaded
files and generated vector data remain local runtime data and must not be
committed.

## Security

Do not commit API keys, database passwords, private Metro State documents, or
uploaded user files. Use local environment configuration for secrets. The
upload endpoint enforces extension/MIME agreement, a 10 MB limit, randomized
storage names, parser validation, and server-side-only processing.
