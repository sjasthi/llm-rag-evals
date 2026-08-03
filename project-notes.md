# Original Project Notes

## Document lifecycle use cases

Basic use case: 50 documents have been RAG-indexed and the chatbot works.

1. A new process document is added (document 51).
2. An existing document is deleted (document 49).
3. An existing document is updated (document 48), combining deletion and addition.

Research questions:

- For an added document, should only document 51 be vectorized, or should all 51 documents be reprocessed?
- For a deleted document, how are only document 49's embeddings removed? Is rebuilding the remaining 49 documents required?

## Current frontend-first interpretation (July 21, 2026)

The deployed user is assumed to have the browser only—no source-code,
terminal, or database access. The primary workflow is therefore Overview ->
Chat -> Documents -> Gold Standard -> Evaluation, with Compare Runs available
as a secondary research view.

The header now verifies application-data readiness before saying the workspace
is ready. If the deployed services are unavailable, browser users receive a
retry/contact-administrator message rather than database or terminal setup
instructions.

- Add ingests only the new document.
- Delete removes the selected MySQL document/chunks and exact Chroma vector IDs,
  then verifies that the source has no vectors left.
- A duplicate filename presents **Replace existing** or **Cancel upload**.
  Replacement ingests the new version first and deletes the old version only
  after success. A successful corpus change clears any visible Chat source
  preview so it must be retrieved again.
- **Restore bundled sources** re-ingests the tracked Metro State starting
  collection with the active index settings and leaves browser uploads in
  place, so Delete All and individual bundled-source deletion are recoverable
  from the application.
- Gold Standard contains reviewed questions, expected answers, sources,
  required facts, evidence, and answerability—not model responses.
- New test run sends reviewed questions through Chat's same retrieval/answer
  function and saves the resulting answers and contexts.
- Evaluate beside one saved answer locks the all-13 scoring workflow to that
  exact answer. The local-eight full-test option remains provider-free.
- Each metric remains independent and shows the current answer value,
  cumulative average across completed tests, and separate current-test/all-test
  summaries. The thirteen unlike metrics are not merged into one grade.
- Retrieval method, top-k, model, temperature, and top-p can vary per test.
  Chunk size, overlap, and embedding model require a separately rebuilt index
  variant before a fair comparison.
- New test run now offers quick test, controlled baseline, and saved-baseline
  comparison modes. The comparison form restores the baseline's exact questions
  and settings, locks all but one chosen variable, supports category-scoped
  corpora, and saves the relationship without exposing internal IDs or CLI
  options. Evaluation also shows a live study-evidence checklist.

## Final-readiness update (August 3, 2026)

- Dataset v2.0 expands the reviewed Gold Standard from 25 to 50 source-verified
  questions. The v1.0 file is retained unchanged for historical reproducibility.
- Every saved test can be downloaded as JSON or long-form CSV for the final
  report. The export includes configuration, answers, contexts, metric results,
  immutable attempts, human reviews, and valid matched comparisons.
- The provider-free suite now contains 66 passing tests, including source/evidence
  integrity checks for all answerable v2.0 questions.
- The historical user-space MySQL database was recovered intact and backed up
  before dataset v2.0 was seeded. Database-backed health, Documents,
  Gold Standard/Evaluation, source-preview, preflight, and export smoke tests
  pass without model calls. Four historical runs, 19 responses, 62 immutable
  evaluator attempts, and the existing human review remain available.
- The local database is not registered as an automatic Windows service. After
  a reboot, the deployment operator can run
  `scripts/start-local-mysql.ps1`; browser users only need the application URL.

## Final controlled-study update (August 3, 2026)

- Runs 5, 6, 7, 8, 10, and 12 complete `final-study-v1` with the exact ordered
  dataset-v2 IDs `1,23,210,213,221`. They cover retrieval method, top-k 3/5/8,
  answer model, and 27-versus-20-document composition one variable at a time.
- The six completed conditions contain 30 responses and 250 canonical results.
  Responses 23 and 28 have all five advanced methods for a matched hard case.
- JSON/CSV export from the Evaluation page was validated for every completed
  study condition.
- Runs 9 and 11 preserve a retired-model failure and a free-tier quota failure.
- Two higher-top-k responses exposed output truncation when hidden thinking
  nearly exhausted the former 512-token cap. Future calls use 2,048 tokens,
  reject non-STOP completions, and account for thinking-token cost.
- Two bounded `--no-save` Gemini 2.5 Flash checks subsequently returned complete
  answers at top-k 5 and 8 without changing the original evidence.
- The database now has 12 runs, 51 responses, 316 canonical results, 340
  attempts, and eight current human reviews. Seven final-study reviews cover the
  five baseline answers and two incomplete outputs: six acceptable and one needs
  revision. This is descriptive single-reviewer calibration.
- A final provider-free audit found that skipped/not-applicable local results
  were validly stored but still offered for repeat execution. The six study
  runs now reuse all 40 current local result rows; failed results remain
  retryable. The 12 genuine audit repeats remain in immutable attempt history.

## Reference repositories

- <https://github.com/sjasthi/ragworks>
- <https://github.com/sjasthi/student-compass>
- Metro State starting documents: <https://github.com/sjasthi/student-compass/tree/main/documents>
- ICS 499 Summer 2026 repository: <https://github.com/sjasthi/llm-rag-evals>

Reference Markdown files supplied with the project may be reviewed, deleted,
consolidated, edited, fixed, or enhanced.

## Required stack and audience

- Front end: HTML, CSS, JavaScript, jQuery, Bootstrap
- Server: PHP
- Database: MySQL
- Demonstration corpus: Metro State documents

The project is intended to help business users and managers choose an approach
using evidence, and to help developers jump-start an implementation adapted
from the reference repositories to the required technology stack.
