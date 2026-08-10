# Reference Repository Comparison

Reviewed July 20 and rechecked August 3, 2026 against the public `main` branches of:

- [RAGWorks](https://github.com/sjasthi/ragworks), commit
  `f51c10e283e10fc69e979dd999b2b628cfd8edaf`
- [StudentCompass](https://github.com/sjasthi/student-compass), commit
  `d44826d9441d5872e776f7c735dc7244b5eeb42b`
- [the course starter/current upstream](https://github.com/sjasthi/llm-rag-evals),
  commit `f2efdf4e09e60c6048716ec91efb1727432c18e7`

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
| Reviewed questions | 50 versioned and source-verified v2.0 questions, including answerability, evidence, accepted variants, and required facts; v1.0 retained | 33 hard-coded evaluation cases in the saved baseline output | 50 gold question/answer pairs in JSON |
| Evaluation breadth | 8 local/supporting evaluators plus LLM judge and 4 RAGAS definitions | Answer accuracy plus binary source accuracy | Browser cosine score across RAG/keyword/prompt-only modes; offline RAGAS faithfulness and answer relevancy with Optuna |
| Experiment integrity | Saved run configuration, question snapshots, ordered contexts, corpus/code hashes, attempts, failures, usage, and cost status | JSON result files; the developer guide warns that reruns can overwrite results | JSON/CSV outputs and best-parameter comments; no relational experiment ledger |
| Comparison method | Same-question/same-evaluator paired deltas only | Aggregate grid results | Aggregate mode/configuration tables and best-configuration callout |
| Human calibration | Versioned response-level human reviews | None found | None found |
| Document lifecycle | Browser upload, same-name staged replacement, per-source/Delete-All index removal, search/filter/sort/grouping; TXT/PDF/DOCX | Add/replace/delete in Chroma; TXT/PDF/DOCX/HTML/PPTX; initial upload asks for a local path | File and URL upload, replace/delete, GCS-to-Chroma reconciliation; TXT/PDF/DOCX/MD |
| Chat experience | Single-turn answer with suggested questions, ranked evidence, approved-model/retrieval/top-k/temperature/top-p controls, and provider-free source preview | Basic single-turn chat | Best conversational UX: SSE streaming, three-turn context window, new-conversation control, source cards, retry state |
| Browser experiment UX | Guided bounded quick/baseline/comparison creation, exact-question reuse, one-variable locking, category-scoped corpora, study checklist, exact-answer Evaluate action, result reuse, answer/cumulative and current-test/all-test means, response evidence, and matched comparisons; provider work remains guarded | Evaluation remains CLI-based | Parameter grid, estimated workload, live progress, cancellation, results table, CSV export |
| Automated verification | 70 provider-free tests plus PHP/JS/dependency checks and a seeded MySQL/Chroma/PHP integration smoke test in GitHub Actions | One React test file; no workflow found | No authored test suite or workflow found |
| Repository hygiene | Secrets/runtime stores ignored; source and migrations tracked | Saved result JSON and SQL seed tracked | `node_modules`, multiple Chroma stores, IDE files, and a placeholder `.env` are tracked despite ignore rules |

## What should be borrowed

### Priority 0: finish evidence required by the assignment

1. Completed August 3: six five-question controlled runs now cover retrieval,
   top-k, answer model, and corpus composition, with matched advanced scoring on
   one hard case. Seven selected responses now have single-reviewer overall human
   decisions for descriptive calibration.
2. Preserve the newly discovered RAGAS failure as an attempt rather than
   deleting it. Failed evidence is part of the reproducibility record.

Completed August 2: dataset v2.0 now contains 50 reviewed questions with exact
bundled-source evidence checks, and v1.0 remains intact for historical runs.

StudentCompass's saved `optuna_results.json` contains 20 trials and reports
`chunk_size=800`, `top_k=3`, `temperature=0.737604...`, `top_p=0.915860...`,
and best value `0.872814`. Only 8–10 valid questions appear per stored trial,
which is a useful reminder to report actual completed coverage rather than only
the intended grid size.

### Priority 1: improve the final demonstration workflow

The immediate StudentCompass-inspired Chat configuration gap is now closed:
retrieval method, top-k, temperature, and top-p are editable in the browser and
Preview Sources remains usable without a model call. This is deliberately
separate from the larger controlled batch launcher below.

Completed August 2: the browser experiment launcher now supports quick tests,
labeled baselines, completed-baseline selection, one unlocked changed variable,
category-scoped corpus variants, exact ordered-question enforcement, and the
same guarded call/cost preflight as the CLI. The Python boundary independently
rejects zero-change and multi-change comparison requests.
2. Show live run progress and allow safe cancellation between questions. Do not
   stream or interrupt in the middle of a database transaction.

Completed August 2: each saved run has JSON and CSV downloads covering run
configuration, question-level answers/contexts/results, immutable attempts,
human reviews, and matched comparisons.

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
for the stated business-manager/developer audience. The reviewed question set,
controlled automated matrix, portable exports, report draft, and presentation
outline are now complete, together with a seven-response descriptive human
calibration sample. The most valuable next work is final editing and
submission/release packaging; additional reviewers would strengthen future
inter-rater analysis but are not represented as completed evidence here.
