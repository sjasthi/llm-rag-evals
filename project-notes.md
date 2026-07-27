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

- Add ingests only the new document.
- Delete removes the selected MySQL document/chunks and exact Chroma vector IDs,
  then verifies that the source has no vectors left.
- A duplicate filename presents **Replace existing** or **Cancel upload**.
  Replacement ingests the new version first and deletes the old version only
  after success. A successful corpus change clears any visible Chat source
  preview so it must be retrieved again.
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
