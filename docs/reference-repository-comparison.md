# Reference Repository Comparison

Reviewed July 20, 2026 against the public `main` branches of:

- [RAGWorks](https://github.com/sjasthi/ragworks), commit
  `f51c10e283e10fc69e979dd999b2b628cfd8edaf`
- [StudentCompass](https://github.com/sjasthi/student-compass), commit
  `d44826d9441d5872e776f7c735dc7244b5eeb42b`
- [the course starter/current upstream](https://github.com/sjasthi/llm-rag-evals),
  commit `1d049e68a80c1871186b9aade06dc2078abd27d1`

The comparison is based on repository source, tracked artifacts, documentation,
and saved evaluation outputs. It does not assume that a documented feature was
deployed or independently validated.

## Executive conclusion

This project should not be reshaped into a copy of either reference. RAGWorks
and StudentCompass are primarily student-facing RAG applications; this capstone
is an evaluation and decision-support workbench implemented in the professor's
required HTML/CSS/JavaScript/jQuery/Bootstrap, PHP, and MySQL stack.

The current project is stronger in experimental provenance, evaluator breadth,
score interpretation, immutable evidence, cost safety, human-review support,
tests, and CI. StudentCompass is stronger as a polished conversational product
and browser-operated tuning demo. RAGWorks is useful as a direct example of
multi-format ingestion and simple administrator/user separation.

## Side-by-side comparison

| Area | This capstone | RAGWorks | StudentCompass |
|---|---|---|---|
| Primary purpose | Evidence workbench for comparing RAG configurations and evaluation methods | User/admin document chatbot | Student assistant with chat, administration, and tuning screens |
| Application stack | Bootstrap/jQuery browser UI, PHP API, MySQL, Python RAG helpers, ChromaDB, Gemini | React, Flask, MySQL, ChromaDB, OpenAI | React/Vite/Tailwind, Flask, GCS, LlamaIndex, ChromaDB, Gemini |
| Required-stack fit | Exact fit | Different frontend/server stack | Different frontend/server/database-infrastructure stack |
| Corpus | 27 Metro State text sources | Metro State test documents managed outside the repository | The same 27 starting Metro State text sources |
| Reviewed questions | 25 versioned and reviewed questions, including answerability, evidence, accepted variants, and required facts | 33 hard-coded evaluation cases in the saved baseline output | 50 gold question/answer pairs in JSON |
| Evaluation breadth | 8 local/supporting evaluators plus LLM judge and 4 RAGAS definitions | Answer accuracy plus binary source accuracy | Browser cosine score across RAG/keyword/prompt-only modes; offline RAGAS faithfulness and answer relevancy with Optuna |
| Experiment integrity | Saved run configuration, question snapshots, ordered contexts, corpus/code hashes, attempts, failures, usage, and cost status | JSON result files; the developer guide warns that reruns can overwrite results | JSON/CSV outputs and best-parameter comments; no relational experiment ledger |
| Comparison method | Same-question/same-evaluator paired deltas only | Aggregate grid results | Aggregate mode/configuration tables and best-configuration callout |
| Human calibration | Versioned response-level human reviews | None found | None found |
| Document lifecycle | Browser upload, same-name staged replacement, per-source/Delete-All index removal, search/filter/sort/grouping; TXT/PDF/DOCX | Add/replace/delete in Chroma; TXT/PDF/DOCX/HTML/PPTX; initial upload asks for a local path | File and URL upload, replace/delete, GCS-to-Chroma reconciliation; TXT/PDF/DOCX/MD |
| Chat experience | Single-turn answer with suggested questions, ranked evidence, approved-model/retrieval/top-k/temperature/top-p controls, and provider-free source preview | Basic single-turn chat | Best conversational UX: SSE streaming, three-turn context window, new-conversation control, source cards, retry state |
| Browser experiment UX | Bounded test creation, exact-answer Evaluate action, result reuse, answer/cumulative and current-test/all-test means, response evidence, and matched comparisons; provider work remains guarded | Evaluation remains CLI-based | Parameter grid, estimated workload, live progress, cancellation, results table, CSV export |
| Automated verification | 54 provider-free tests plus PHP/JS/dependency checks in GitHub Actions | One React test file; no workflow found | No authored test suite or workflow found |
| Repository hygiene | Secrets/runtime stores ignored; source and migrations tracked | Saved result JSON and SQL seed tracked | `node_modules`, multiple Chroma stores, IDE files, and a placeholder `.env` are tracked despite ignore rules |

## What should be borrowed

### Priority 0: finish evidence required by the assignment

1. Expand the reviewed evaluation dataset from 25 to 50 questions. The current
   25 are higher quality than a flat question/answer list, but both the supplied
   use case and StudentCompass demonstrate 50. New cases should preserve the
   existing review fields and include more hard, multi-source, and
   unanswerable questions. They should enter as draft until manually verified.
2. Complete a bounded empirical matrix after the RAGAS adapter is verified:
   baseline, one-variable comparisons, repeated model-backed evaluator attempts,
   and human calibration. The dashboard is more defensible than either
   reference, but the stored evidence remains too small for a final comparison.
3. Preserve the newly discovered RAGAS failure as an attempt rather than
   deleting it. Failed evidence is part of the reproducibility record.

### Priority 1: improve the final demonstration workflow

The immediate StudentCompass-inspired Chat configuration gap is now closed:
retrieval method, top-k, temperature, and top-p are editable in the browser and
Preview Sources remains usable without a model call. This is deliberately
separate from the larger controlled batch launcher below.

1. Add a browser experiment launcher for dataset, retrieval method, top-k,
   corpus variant, baseline, and one changed variable. It should call the same
   preflight/authorization path as the CLI and show the application/cost cap
   before execution.
2. Add JSON and CSV export for run configuration, question-level results, and
   matched comparisons. StudentCompass makes results easy to take away; this
   project already has the stronger underlying data model.
3. Show live run progress and allow safe cancellation between questions. Do not
   stream or interrupt in the middle of a database transaction.

### Priority 2: product polish that should remain secondary

1. Add streaming generation and a short conversation window only if the final
   demo needs a student-chat story. Keep evaluation runs single-turn so history
   does not become an uncontrolled variable.
2. Add URL/HTML and PowerPoint ingestion if multi-format coverage is graded.
   Use the existing normalized document/hash lifecycle rather than introducing
   a second ingestion path.
3. Add authentication before any deployment beyond localhost. The current
   document and evaluation administration screens are intentionally local and
   are not access-controlled; StudentCompass also lists authentication as
   future work.

## What should not be copied

- Do not replace the required PHP/MySQL stack with React/Flask just to resemble
  the references.
- Do not collapse unlike evaluator outputs into a single overall accuracy
  number or crown a best configuration from unmatched questions.
- Do not commit runtime vector databases, dependency directories, credentials,
  or local result state.
- Do not make chat history part of controlled evaluation prompts unless it is
  the explicitly named experimental variable.
- Do not replace the relational evidence trail with mutable JSON result files.

## Current position

The project is ahead of the examples as a research instrument and behind
StudentCompass as a conventional chatbot product. That is a reasonable trade
for the stated business-manager/developer audience. The most valuable next
work is not a visual rewrite: it is doubling the reviewed question set,
providing a safe browser path for controlled runs and exports, and collecting
enough matched empirical evidence to support the final findings.
