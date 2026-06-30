# Code Structure and Conventions

## Proposed Directory Structure

```text
llm-rag-evals/
|-- index.php
|-- requirements.md
|-- README.md
|-- assets/
|   |-- css/
|   |-- js/
|   `-- images/
|-- config/
|-- includes/
|-- pages/
|-- api/
|   |-- ask.php
|   |-- documents.php
|   `-- evaluations.php
|-- database/
|   |-- migrations/
|   `-- seeds/
|-- src/
|   |-- Database/
|   |-- Documents/
|   |-- Rag/
|   `-- Evaluation/
|-- rag/
|   |-- chroma/
|   |-- answer.py
|   |-- database.py
|   |-- document_loader.py
|   |-- evaluate.py
|   |-- ingest.py
|   |-- llm.py
|   |-- query.py
|   |-- settings.py
|   |-- vector_store.py
|   `-- requirements.txt
|-- storage/
|   |-- uploads/
|   `-- logs/
|-- tests/
`-- docs/
```

Directories should be added when their first real file is implemented; empty
placeholder directories are unnecessary.

## Responsibilities

- `assets/`: browser-delivered styles, scripts, and images.
- `config/`: configuration loading; secrets remain in ignored environment files.
- `includes/`: reusable page layout such as header, navigation, and footer.
- `pages/`: page controllers/templates reached through the web interface.
- `api/`: validated PHP endpoints used by jQuery or other asynchronous
  requests, including Ask, document upload/management, and evaluation runs.
- `database/`: versioned schema changes and non-sensitive sample data.
- `src/`: application and domain logic, separated from page markup.
- `rag/`: Python helper layer for TXT/PDF/DOCX text extraction,
  MySQL/ChromaDB ingestion, embeddings, retrieval, grounded answer generation,
  and evaluation metrics/experiments.
- `storage/`: generated files, uploads, and logs; private content is not committed.
- `tests/`: automated tests and stable evaluation fixtures.
- `docs/`: planning, architecture, UX, and setup documentation.

## Coding Conventions

### PHP

- Follow PSR-12 formatting where practical.
- Use `declare(strict_types=1);` in PHP-only application files.
- Use `camelCase` for methods/variables and `PascalCase` for classes.
- Escape rendered data with `htmlspecialchars`.
- Validate input at the request boundary.
- For uploads, validate PHP upload status, extension, MIME type, size, and the
  parser result; generate server-controlled storage names.
- Use PDO prepared statements for every database query.
- Keep SQL, API calls, and business logic out of presentation templates.

### Python Document Processing

- Keep format-specific extraction in one loader module that returns normalized
  text and metadata to the common ingestion pipeline.
- Support `.txt`, text-based `.pdf`, and `.docx` first; do not silently treat a
  scanned image PDF as successfully parsed text.
- Never execute macros, embedded objects, or uploaded content.
- Preserve the original filename for display but use a server-controlled path
  for storage.
- Make replace/re-ingest idempotent so a document cannot leave duplicate MySQL
  chunks or ChromaDB vectors.
- Unit test parsers with small non-sensitive fixtures.

### Evaluation and Research

- Store raw per-question metric results rather than only aggregate scores.
- Record the exact question set, corpus variant, RAG settings, metric version,
  and judge model/prompt used for each run.
- Keep deterministic metrics separate from model-judged metrics.
- Represent metric disagreement and failure categories explicitly so results
  can be audited.
- Do not encode a universal "best" metric in application logic; recommendations
  must depend on the documented research purpose.

### HTML, CSS, and JavaScript

- Use semantic HTML and Bootstrap components before adding custom behavior.
- Use kebab-case for CSS class names and JavaScript file names.
- Place project styles and scripts in files rather than inline blocks.
- Use `const` and `let`; avoid `var`.
- Keep jQuery event handlers small and call named functions for substantial work.
- Preserve keyboard operation and visible focus states.

### Database

- Use `snake_case` for table and column names.
- Use plural table names and singular primary keys such as `document_id`.
- Include timestamps where creation/update history matters.
- Store schema changes as ordered migration files.

### Git

- Branch by task, for example `fp4/document-upload`.
- Write imperative commit messages, for example `Add FP3 starter page`.
- Keep commits focused and do not commit secrets, dependencies, or generated logs.
- Review `git diff` and run relevant checks before opening a pull request.
