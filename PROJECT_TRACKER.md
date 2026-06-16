# Project Tracker

Last updated: June 15, 2026

Use this file as the first thing to read when returning to the project. It
records where the project stands, what has already been completed, and what each
future FP should deliver.

## Current State

- Current iteration: FP3
- Active branch workflow: push directly to `main` after FP3 branch is merged
- Official repo: `https://github.com/sjasthi/llm-rag-evals`
- Local project path: `C:\Users\andre\Desktop\ICS499 Capstone\LLM RAG Evaluation Project`
- PHP dev server URL: `http://127.0.0.1:8000/`
- PHP installed through winget: PHP 8.4
- FP3 work has been committed and pushed to `fp3-starter`.
- Next workflow should use `main` because the professor does not want to merge branches for each checkpoint.

## Current Architecture Decision

Use the assigned stack unless the professor approves a different direction:

- Frontend: HTML, CSS, JavaScript, jQuery, Bootstrap
- Server: PHP
- Structured database: MySQL
- Vector database: ChromaDB
- LLM provider: configurable provider such as OpenAI/ChatGPT, Gemini, Claude, or another approved model
- RAG helper layer: Python service or scripts for ChromaDB, embeddings, retrieval, and optional RAGAS

Do not add React, cloud storage, streaming responses, or full
authentication unless those choices clearly support the project goal or the
professor confirms they are required.

Assume development will happen locally, with standard PHP/MySQL hosting as the
fallback if the professor asks to view it through a hosted environment. Local
file storage is preferred unless the professor requires a different storage
path. Full authentication should be avoided unless required.

## Completed So Far

### Repository Setup

- Initialized the local project folder as a Git repository.
- Added the professor's repo as `origin`.
- Created local branch `fp3-starter` from `origin/main`.
- Pushed FP3 branch after collaborator access was granted.
- Preserved the existing requirements file and renamed it to lowercase `requirements.md`.

### FP3 Deliverables

- Added `index.php` starter page.
- Added project CSS in `assets/css/styles.css`.
- Added small jQuery/Bootstrap helper in `assets/js/app.js`.
- Added `.gitignore`.
- Added `.env.example`.
- Updated `README.md`.
- Added `docs/fp3-project-plan.md`.
- Added `docs/ux-design.md`.
- Added `docs/code-structure.md`.
- Added `docs/implementation-approach.md`.
- Added `docs/final-project-scope.md`.
- Added `docs/questions-for-professor.md`.
- Added `docs/frontend-design-prompt.md`.
- Added `docs/final-report-outline.md`.

### Design Direction

- Redesigned the starter page away from a generic AI/SaaS style.
- Current visual direction is a restrained university research-tool interface:
  maroon/gold accents, serif headings, bordered information blocks, tables, and
  honest planned-status language.

### Verification

- `index.php` passes PHP syntax validation with PHP 8.4.
- Local server returned HTTP 200 for the page and CSS.
- `git diff --check` passed.

## Immediate Next Steps

1. Review the current `index.php` in the browser and decide whether the FP3
   visual direction is acceptable.
2. Replace any placeholder responsibility wording with language preferred by the
   professor if needed.
3. Ask the professor the high-priority questions in `docs/questions-for-professor.md`.
4. Merge FP3 work into `main`.
5. Push `main` to the official repo.
6. Continue future checkpoint work directly on `main` unless the professor asks for branches.

Suggested future commit flow:

```powershell
git add .
git commit -m "Describe the checkpoint work"
git push origin main
```

## Professor Questions To Resolve Before FP4

Ask these first:

1. Will Metro State documents be provided, or should public documents be collected manually?
2. Approximately how many documents are required? Is 20 a good target?
3. Is a 50-question gold dataset required?
4. May any LLM provider be used, such as OpenAI/ChatGPT, Gemini, or Claude?
5. Are API costs covered by the school/course, or paid individually?
6. Should PHP call a small Python helper/service for ChromaDB ingestion and retrieval while MySQL stores structured app data?
7. May PHP remain the main app while Python handles ChromaDB and optional RAGAS evaluation?
8. For FP3, is a responsive `index.php` with planning and UX docs enough, or should forms already work?

## FP Roadmap

### FP3: Planning, UX, Structure, Starter Page

Goal: Make the project direction clear and show a starter interface.

Already done:

- Requirements are present in `requirements.md`.
- FP3-FP10 plan is drafted.
- UX design is documented.
- Code structure is documented.
- Starter `index.php` exists and runs.
- Professor-question list exists.
- Implementation approach exists.

Remaining:

- Confirm professor expectations.
- Ensure FP3 work is available on `main`.
- Fill in any required due dates or rubric-specific details.

FP3 acceptance target:

- The professor can open the repo, see the plan, understand the intended final
  system, and view a starter page.

### FP4: Database and Document Foundation

Goal: Build the storage foundation and document-management skeleton.

Implement:

- MySQL database creation script.
- ChromaDB setup plan for vector storage.
- Database connection helper in PHP.
- `.env` loading or safe config strategy.
- Tables for:
  - documents
  - document_chunks
  - evaluation_questions
  - rag_responses
  - evaluation_runs
  - evaluation_scores
  - model_settings
- Local ChromaDB storage directory for embeddings/vector retrieval.
- Basic admin page shell.
- Document list page using sample seeded records.
- Local storage directory for uploaded files.

Recommended files:

- `config/database.php`
- `config/env.php`
- `database/schema.sql`
- `database/seeds/sample_questions.sql`
- `rag/` or `services/rag/` for Python ChromaDB helper code
- `includes/header.php`
- `includes/footer.php`
- `pages/documents.php`
- `pages/admin.php`

Verification:

- Database schema imports successfully.
- PHP can connect to MySQL.
- A page can read and display document rows from MySQL.
- ChromaDB can be initialized locally from the helper script.

### FP5: Document Parsing, Chunking, and Embeddings

Goal: Prove the RAG ingestion pipeline.

Implement:

- Upload or import TXT documents first.
- Store document metadata in MySQL.
- Extract document text.
- Chunk text using configurable chunk size and overlap.
- Generate embeddings through the selected LLM provider.
- Store chunk text, embeddings, and source metadata in ChromaDB.
- Store document metadata and processing status in MySQL.
- Show chunk count per document.
- Add replace-document behavior that removes old chunks and inserts new chunks.

Keep initial scope small:

- Start with TXT files.
- Add PDF/DOCX only after TXT works.
- Use 3-5 public Metro State documents first.

Verification:

- Upload/import a document.
- Confirm chunks are written to MySQL.
- Confirm chunks and embeddings are stored in ChromaDB.
- Replacing a document deletes old chunks and inserts new chunks.

### FP6: Retrieval and Ask Page

Goal: Let a user ask a question and receive a grounded answer with sources.

Implement:

- Ask page with question form.
- Embed the user question.
- Query ChromaDB for similar chunks.
- Retrieve top-k chunks.
- Build a prompt using only retrieved context.
- Call the selected LLM provider server-side.
- Display:
  - answer
  - source document names
  - retrieved chunk excerpts
  - model/settings used
- Add suggested questions below the input.

Verification:

- Ask a question answerable from the uploaded documents.
- Confirm the answer cites source chunks.
- Ask an unanswerable question and confirm the app avoids unsupported claims.

### FP7: Gold Dataset and Basic Evaluation

Goal: Create a repeatable evaluation set and run simple scoring.

Implement:

- Add approximately 50 Metro State questions if required.
- Store expected answers and expected source documents.
- Evaluation runner page.
- Run all or selected questions through the RAG pipeline.
- Store generated answer, retrieved sources, latency, and settings.
- Implement basic metrics:
  - exact/contains match
  - semantic similarity
  - source match
  - answer length/empty-answer checks

Verification:

- Run a small evaluation set, such as 5 questions.
- Store results in MySQL.
- Display per-question scores.

### FP8: Parameter Comparison

Goal: Show how RAG settings affect answer quality.

Implement:

- Configurable settings:
  - chunk size
  - chunk overlap
  - top-k
  - temperature
  - model/provider
- Evaluation run grouping by settings.
- Comparison table showing:
  - average score
  - source accuracy
  - latency
  - estimated API cost
  - number of questions
- Add LLM-as-judge if time and API cost allow.
- Optional: add offline Python/RAGAS evaluation if approved.

Recommended first experiments:

- top-k: 3, 5, 8
- chunk size: 300, 600, 900
- temperature: 0.0, 0.3

Verification:

- Run at least two configurations.
- Dashboard clearly shows which setting performed better.

### FP9: Dashboard, Reports, Testing, and Polish

Goal: Make the application understandable and demo-ready.

Implement:

- Dashboard summary cards/tables.
- Report page explaining:
  - best configuration
  - weakest questions
  - common failure cases
  - recommendation for managers/developers
- Input validation and error handling.
- Security review:
  - no API keys in repo
  - API calls server-side only
  - prepared statements
  - upload restrictions
- Accessibility review:
  - labels
  - keyboard navigation
  - color contrast
- Setup documentation.

Verification:

- Fresh setup works from README instructions.
- At least one full evaluation run can be demonstrated.
- No secrets are tracked by Git.

### FP10: Final Stabilization and Presentation

Goal: Deliver the final project and explain the findings.

Implement:

- Final bug fixes.
- Final seed/demo data.
- Final screenshots or presentation visuals.
- Final report.
- Final README and setup guide.
- Tag or mark final release.

Demo script:

1. Show document list.
2. Ask a question and show answer with sources.
3. Run or display an evaluation.
4. Compare two configurations.
5. Explain which configuration performed best and why.
6. Explain project limitations and future improvements.

## Minimal Final Product Definition

The project is complete enough if it can:

1. Store Metro State documents.
2. Chunk and embed document text.
3. Retrieve relevant chunks for a question.
4. Generate an answer from retrieved chunks.
5. Show sources.
6. Run a repeatable evaluation set.
7. Compare at least two RAG configurations or evaluation methods.
8. Present results in a table/dashboard.
9. Explain which approach performed better.

Everything beyond that is optional.

## Things To Avoid Unless Required

- React frontend.
- Flask as the main app.
- Google Cloud Storage.
- Multi-user authentication.
- Streaming chat responses.
- Multi-agent RAG.
- Large document sets.
- Production-grade deployment beyond the course hosting/demo requirement.
- Running every possible parameter combination.

## Useful Commands

Start PHP server:

```powershell
php -S 127.0.0.1:8000
```

If `php` is not on PATH, use the installed PHP executable:

```powershell
& "C:\Users\andre\AppData\Local\Microsoft\WinGet\Packages\PHP.PHP.8.4_Microsoft.Winget.Source_8wekyb3d8bbwe\php.exe" -S 127.0.0.1:8000
```

Check PHP syntax:

```powershell
php -l index.php
```

Check Git status:

```powershell
git status --short --branch
```

Check whitespace before committing:

```powershell
git diff --check
```

## Current Files To Review

- `index.php`
- `requirements.md`
- `README.md`
- `docs/fp3-project-plan.md`
- `docs/final-project-scope.md`
- `docs/ux-design.md`
- `docs/code-structure.md`
- `docs/implementation-approach.md`
- `docs/questions-for-professor.md`
- `docs/frontend-design-prompt.md`
- `docs/final-report-outline.md`
- `.env.example`
- `.gitignore`
