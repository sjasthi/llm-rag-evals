# FP10 Hardening Record

> **Status:** Historical hardening and verification record. The hardened
> behavior is part of the submitted application; final empirical conclusions
> are in [Final Study Report](final-study-report.md).

## Scope

This pass turns the FP8/FP9 application into a more defensible research
instrument without overstating empirical model results. After the hardening
pass, one separately authorized and capped provider proof was run on July 20,
2026.

## Immutable evidence

New generated responses store a versioned snapshot of the reviewed evaluation
case: dataset identity/version, question text, answer key, source/evidence,
accepted variants, required facts, answerability, difficulty, category, review
status, and question update time. Scoring reads that snapshot first, so later
edits to the live question cannot rewrite a historical result.

Every retrieved excerpt now retains its source path, category, chunk index,
document hash, chunk hash, semantic distance, lexical score, final ranking
score, and versioned ranking metadata. Response records also retain a Git/source
tree code fingerprint. Migration 006 labels historical rows as
`legacy_backfill` or `legacy-unavailable`; those labels are evidence limits, not
invented provenance.

## Paid-call and cost safety

Answer generation records provider input/output/total tokens when available.
An estimate is recorded only when token usage and configured per-million rates
support it. Missing pricing is represented as `NULL`/`unknown`, never zero.

The following paths are guarded:

- direct `rag/answer.py` generation;
- baseline `rag/run_evaluation.py` generation;
- advanced `rag/run_advanced_evaluation.py` evaluation; and
- browser `api/ask.php` generation.

Dry runs are no-write and provider-free. Real calls require explicit paid-call
authorization and a cap. Unknown pricing additionally requires a separate
override. The browser is paused by default with `ALLOW_PAID_GENERATION=0`.

## Findings validity

The Findings view no longer presents lifetime means as a run leaderboard.
Catalog cards show coverage and score contracts. Descriptive means are scoped
to one run. A comparison delta is calculated only when a run declares
`baseline_run_id` and both runs contain a completed result for the same
`question_id` and evaluator. With the current legacy proof runs, the correct UI
state is “No valid paired comparison exists yet.”

## UI and accessibility

The pass increases previously tiny audit text, darkens low-contrast secondary
colors, enlarges disclosure controls, adds strong keyboard focus indicators,
honors reduced-motion preferences, uses navigable browser history for workspace
views, and exposes snapshot, code, generation-cost, and retrieval-score
provenance in the response inspector.

The follow-up simplification pass now names the main workflow Overview, Chat,
Documents, Gold Standard, and Evaluation. Gold Standard is explicitly presented
as the reviewed test answer key—not chat history—and Evaluation explains a run
as a batch of questions answered under one fixed configuration. Compare Runs
remains available from Evaluation without crowding the primary navigation. Chat
exposes an approved model plus vector/keyword retrieval, top-k, temperature, and top-p, and provides a
provider-free source preview while paid answer generation is paused.

The final clarity pass makes the shared implementation visible in all three
relevant views: a reviewed Gold Standard question is sent through the same
retrieval-and-answer pipeline as Chat, then its saved answer is scored under
Evaluation. Evaluation no longer presents baseline, advanced, human, and operations
as four numbered evaluation steps. It shows Local metrics, the LLM judge, and
RAGAS separately, reports completed/failed/skipped/not-run status per selected
answer, and identifies human review as supporting evidence. Run and response
headlines now count completed checks instead of describing failed canonical
rows as successful “quality-check results.”

The July 20 frontend-first follow-up adds bounded browser test creation and a
Score saved answers control to every test, provider-free preflight,
local-eight/full-test and all-13/exact-answer modes, reuse/replacement behavior,
and current-test versus all-test means for every evaluator. User-facing question
numbers replace internal response IDs in primary navigation, and interrupted
attempts are moved to actionable collapsed history.
It also labels gold-standard dependency, shows the active chunk count on
Overview, and makes the complete document index searchable, filterable,
replaceable, and removable from the browser.

The August 2 browser-only follow-up adds quick, controlled-baseline, and
saved-baseline-comparison modes to New test run. A comparison restores the
baseline's exact ordered questions and settings, unlocks one declared variable, can vary
source-category composition, and is rejected server-side unless exactly one
supported difference is observed. Evaluation also derives a study-readiness
checklist from the stored dataset, run, matched-pair, human-review, and export
state.

The July 21 professor-recording alignment adds an explicit Replace
existing/Cancel upload conflict decision, exact-ID Chroma cleanup with a
read-back stale-vector check, and Chat-preview invalidation after every
successful corpus change. Every saved answer now has a direct Evaluate action
that locks the all-13 workflow to that exact answer and starts the guarded
call/cost preflight. Each metric card displays the isolated answer score beside
the evaluator's cumulative average over completed tests; the expandable table
retains current-test and all-test means. The New test form also identifies the
active chunk size/overlap and explains why another chunking configuration
requires a separately rebuilt index.

## Verification

Verified locally through August 2, 2026:

- 59 provider-free Python unit/static tests pass, with the same checks defined
  in the GitHub Actions quality workflow;
- all PHP files pass `php -l`;
- `assets/js/app.js` passes `node --check`;
- migrations 006 and 007 apply to the existing MySQL database;
- summary and response-detail API reads succeed against legacy rows;
- a live completed response returns all 13 metric records with all 13
  cumulative-average fields populated;
- the active Chroma collection contains 77 vectors and supports the exact
  source-path ID lookup used by verified deletion;
- the browser answer endpoint returns HTTP 503 while paid calls are paused;
- browser vector and keyword previews return the requested number of sources,
  invalid settings return HTTP 422, and preview never requires paid-call opt-in;
- baseline dry run freezes dataset/corpus/code/preflight data and leaves the run
  count unchanged; and
- pricing-aware baseline and advanced dry runs report bounded estimates and
  perform no writes or provider calls; and
- dataset v2.0 contains 50 unique reviewed questions whose answerable evidence
  excerpts are verified against bundled sources, while v1.0 remains available;
  per-run JSON/CSV export is covered by the frontend regression suite.

## Authorized empirical proof (July 20, 2026)

- Current Gemini 2.5 Flash rates were verified against the
  [official Gemini API pricing page](https://ai.google.dev/gemini-api/docs/pricing)
  and configured at `$0.30` per million input tokens and `$2.50` per million
  output tokens.
- Baseline run 4 generated response 19 for reviewed question 1. The response
  used 991 input tokens, 25 output tokens, 1,072 total provider tokens, took
  1,689 ms, and recorded an estimated generation cost of `$0.00035980`.
- The expected `fall_2026.txt` source ranked first. All eight local/supporting
  evaluators completed and passed; required-fact coverage and expected-source
  accuracy were `1.0`.
- The five-application advanced preflight estimated `$0.07215`, below the
  approved `$1.00` ceiling. The LLM judge completed with normalized score `1.0`
  and recorded estimated cost `$0.00120550`.
- The first four RAGAS attempts failed before scoring because RAGAS 0.4.3 invoked
  `agenerate()` on the synchronous Google GenAI structured-output client. The
  adapter now runs synchronous generation in a worker thread and is covered by
  a provider-free regression test. An authorized retry exposed the missing
  `instructor[google-genai]` extra, which is now pinned. Subsequent bounded
  retries respected the free-tier cooldown and completed all four metrics:
  Faithfulness `1.0`, Response Relevancy `0.9154`, Context Precision `1.0`, and
  Context Recall `1.0`. All earlier failures remain in immutable attempt history.

## Empirical continuation

The recovered database initially had only three unique questions in its first
local baseline, no declared question-matched baseline/comparison pair, five
advanced results on one response, and one human review. The August 3 final-study
continuation closed that evidence gap with six controlled five-question
conditions, matched retrieval/top-k/model/corpus comparisons, advanced scoring
for the same hard question under Chroma and MySQL retrieval, and seven selected
overall human decisions. Six reviewed responses were acceptable and one needed
revision. This remains a descriptive single-reviewer calibration sample rather
than inter-rater evidence, and earlier failed attempts remain auditable.
Dataset v2.0 provides 50 reviewed, source-verified questions while preserving
v1.0 for historical runs. Per-run JSON/CSV export is available for final
analysis and reporting.
