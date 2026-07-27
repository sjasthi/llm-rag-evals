# FP8 and FP9 Implementation Record

## Status and Boundary

FP8 and FP9 application support was implemented and locally verified on July
14, 2026. The code, schema, evaluator catalog, controlled-run support, Results
inspector, human-review workflow, and Compare Runs workspace are live.

The implementation is intentionally separate from the empirical study:

- the existing FP7 responses still have their eight real baseline results;
- no RAGAS or LLM-judge score has been invented or inserted;
- the advanced runner was exercised in dry-run mode only because those methods
  can call an external model and consume API quota;
- an advanced proof run requires an explicit `--allow-paid` flag; and
- preliminary and final research conclusions remain pending until comparable
  advanced, human, and controlled-run evidence is actually collected.

This distinction lets the project say that FP8/FP9 infrastructure is complete
without claiming that an experiment occurred when it did not.

## Implemented Evaluator Portfolio

Thirteen active evaluator definitions are registered. Each definition includes
a score contract: the question it answers, comparison target, calculation,
scale, direction, threshold, threshold status, applicability, implementation,
inputs, and main limitation.

### Baseline layer (eight)

1. Exact or accepted-answer match
2. Required-fact coverage
3. Token-overlap F1
4. ROUGE-L F1
5. Embedding semantic similarity using `all-MiniLM-L6-v2`
6. BERTScore F1 using `distilbert-base-uncased`
7. Expected-source accuracy and retained source rank
8. Refusal correctness against the reviewed answerability label

These methods are inexpensive diagnostics. A `passed` flag means the score met
the registered project review rule. It is not a factual verdict. In particular:

- required-fact coverage `1.0` means all manually listed fact phrases appeared;
- BERTScore `0.953` means contextual tokens strongly resembled the reference;
- the BERTScore `0.80` cutoff is project-defined and unvalidated; and
- neither value proves that every claim is correct or grounded.

### Advanced layer (five)

1. Versioned Gemini LLM-as-judge rubric
2. RAGAS Faithfulness
3. RAGAS Response Relevancy (`AnswerRelevancy` in the RAGAS API)
4. RAGAS Context Precision
5. RAGAS Context Recall

The judge returns structured 0-4 ratings for correctness, completeness,
faithfulness, relevance, and answerability. Applicable dimensions are averaged
and divided by four for a 0-1 display value. The raw dimension reasons,
unsupported claims, missing facts, overall decision, provider output, prompt
hash, rubric version, model, token usage, runtime, and cost estimate are
retained.

RAGAS uses the 0.4 collections API. Inputs map directly from the one saved
question, generated answer, reviewed reference, and ordered saved contexts. It
does not regenerate an answer. The pinned dependency pair is:

```text
ragas==0.4.3
langchain-community==0.4.1
```

Version `0.4.1` of `langchain-community` is pinned because `0.4.2` removed an
import path still used by RAGAS 0.4.3. The evaluator provider is configurable;
the current adapter uses Gemini and a local Hugging Face embedding model for
Response Relevancy.

## Applicability and Failure Semantics

`completed`, `skipped`, `failed`, and numeric zero are different states.

- A deliberately unanswerable question skips Response Relevancy, Context
  Precision, and Context Recall.
- A claim-free expected refusal skips Faithfulness.
- Retrieval metrics skip when required reviewed references or contexts are
  absent.
- One evaluator failure is stored on that evaluator and does not invalidate the
  saved RAG response or other evaluator results.
- Skipped and failed entries are excluded from numeric summaries.

The UI presents these states separately. Missing advanced results are labeled
as missing evidence rather than displayed as zero.

## Immutable Attempts and Canonical Results

`evaluator_result_attempts` appends every evaluator attempt with:

- evaluator and response identity;
- monotonic attempt number;
- status, raw and normalized scores, and threshold flag;
- explanation and structured details;
- merged evaluator/run configuration snapshot;
- raw provider output;
- input, output, and total token counts;
- runtime and estimated cost; and
- isolated error text.

`evaluator_results` remains the convenient canonical row used by the browser.
Its documented policy is `latest_attempt`. The browser also calculates attempt
count, same-metric mean, range, and population standard deviation so a
nondeterministic judge is not falsely presented as stable. FP7 result rows were
backfilled as attempt 1 without changing their measured scores.

## Advanced Runner and Cost Guardrails

Preview one saved response:

```powershell
python rag\run_advanced_evaluation.py --response-id 17 --dry-run --json
```

Preview a bounded run subset:

```powershell
python rag\run_advanced_evaluation.py --run-id 3 --limit 1 --dry-run --json
```

The preflight shows `run`, `reuse`, or `skip` for every evaluator/response,
application count, paid-call count, and estimated cost. Existing completed
active-version results are reused unless `--force` is deliberate. Execution is
blocked unless all applicable limits pass:

- external calls require `--allow-paid`;
- default maximum applications is 5;
- default maximum estimated cost is 1.0 in configured currency units;
- attempts must be between 1 and 10; and
- evaluator input/output prices default to zero, which is explicitly reported
  as “pricing unavailable,” not as a promise that calls are free.

An authorized one-response proof would be:

```powershell
python rag\run_advanced_evaluation.py `
  --response-id 17 `
  --allow-paid `
  --max-applications 5 `
  --max-estimated-cost 1.00 `
  --json
```

Do not run that command until provider pricing is entered in `.env`, the
preflight is reviewed, and external API use is approved.

## Reproducible Controlled Runs

New evaluation runs freeze:

- dataset name, version, and database identity;
- retrieval method and top-k;
- chunk size and overlap;
- embedding and answer model/provider;
- temperature and top-p;
- corpus-variant key and selected categories;
- ordered document manifest, hashes, and manifest hash; and
- baseline evaluator keys.

The run row can link to a baseline run and an experiment key. Pre-FP8 rows are
marked `legacy_partial` with `legacy-unknown` corpus provenance; the UI does not
pretend their full historical manifest can be reconstructed.

Example Chroma baseline:

```powershell
python rag\run_evaluation.py `
  --dataset-id 5 `
  --name "FP8 Chroma top-3 baseline" `
  --retrieval chroma_vector `
  --top-k 3 `
  --experiment-key retrieval-method-v1 `
  --corpus-variant full-current `
  --json
```

Example one-variable MySQL comparison:

```powershell
python rag\run_evaluation.py `
  --dataset-id 5 `
  --name "FP8 MySQL top-3 comparison" `
  --retrieval mysql_keyword `
  --top-k 3 `
  --experiment-key retrieval-method-v1 `
  --baseline-run-id 4 `
  --corpus-variant full-current `
  --json
```

Example focused corpus variant:

```powershell
python rag\run_evaluation.py `
  --dataset-id 5 `
  --name "FP8 focused calendar corpus" `
  --retrieval chroma_vector `
  --top-k 3 `
  --experiment-key corpus-composition-v1 `
  --baseline-run-id 4 `
  --corpus-variant calendar-registration-only `
  --categories academic_calendar,registration `
  --json
```

Use IDs returned by the local database; the example baseline ID is illustrative.
Generation calls are external, so start with `--limit 1` when proving a new
configuration. A defensible comparison changes one declared variable while
holding dataset, question selection, answer model, temperature, and other
settings fixed.

## Genuine MySQL Retrieval

`mysql_keyword` searches authoritative `document_chunks` in MySQL using a
FULLTEXT index, applies lexical reranking, and has a deterministic database
fallback for short/date-heavy questions that FULLTEXT may omit. It is distinct
from the retained `keyword` filesystem troubleshooting baseline in
`rag/query.py`.

Verify MySQL retrieval without generation:

```powershell
python rag\query.py `
  "When does Fall 2026 registration begin in eServices?" `
  --retrieval mysql `
  --top-k 3 `
  --json
```

The verified local result ranks the Fall 2026 academic-calendar chunk first.

## Human Review

Dataset review and response review are intentionally different:

- Dataset `reviewed`, `needs_revision`, and `draft` describe whether the test
  question, expected answer, and expected evidence are trustworthy.
- Response human review rates a generated answer while showing its reference
  and exact saved contexts.

The response inspector now housed under Evaluation records optional 1-5 correctness, completeness,
faithfulness, relevance, and refusal-correctness ratings; an overall decision;
a failure category; reviewer alias; notes; rubric version; and timestamps.
Submitting another review by the same alias makes the older record noncurrent
instead of overwriting it.

Human review is calibration evidence, not infallible ground truth. A reviewer
may leave a dimension blank when the shown evidence cannot support a rating.

## FP9 Evaluation and Compare Runs UX

At the FP9 checkpoint, the workspace then named Results added the underlying
four evidence types. The later rename to Evaluation keeps all of that evidence
but presents the
automatic methods directly as Local metrics, LLM judge, and RAGAS, with Human
review labeled as supporting evidence. The workspace now:

- uses a compact run browser and automatically opens a real saved response;
- states run coverage as executed responses out of dataset questions;
- shows retrieval method, completed-result count, skips, failures, and legacy
  provenance without presenting failed rows as completed checks;
- summarizes completed, failed, skipped, and not-run status for Local metrics,
  the LLM judge, and RAGAS on each selected response;
- groups score cards by those named method families;
- expands every score contract beside the observed explanation;
- shows attempt variability only within the same evaluator;
- marks the expected retrieved source;
- provides evidence-backed human-review controls; and
- raises targeted disagreement prompts without declaring an automatic cause.

The Compare Runs workspace now:

- states the five interpretation rules first;
- compares run configuration, corpus label, coverage, canonical evaluator
  count, skips/failures, runtime, and recorded cost;
- provides a catalog entry for all 13 active evaluators;
- reports descriptive means within one run and calculates deltas only for
  declared baselines matched on question and evaluator (FP10 hardening); and
- never averages lexical, semantic, retrieval, judge, and human dimensions into
  one unexplained grade.

No chart was added merely for decoration. The current comparisons are compact
tables/cards because exact run mappings and score contracts are the important
relationships. A later chart is justified only after comparable complete runs
exist.

## API and Schema Surface

`GET api/evaluations.php` returns the current dataset, questions, full evaluator
contracts, runs, response summaries, run-scoped/matched findings, layer counts,
and interpretation rules.

`GET api/evaluations.php?response_id=17` returns the saved answer/reference,
frozen run settings, exact contexts, canonical evaluator rows, attempt
statistics, immutable attempts, current human reviews, and disagreement cues.

`POST api/evaluations.php` with `action=human_review` validates and versions a
response review. `PATCH api/evaluations.php` continues to update Dataset review
state.

New schema/migration elements include:

- FP8 run provenance columns and foreign keys;
- `evaluator_result_attempts`;
- `human_reviews`;
- `evaluator_results.updated_at`;
- MySQL FULLTEXT chunk search; and
- explicit legacy-run provenance backfills.

## Verification Completed

- 34 Python unit/static regression tests passed at the FP8/FP9 checkpoint; the
  July 21 frontend-first suite now contains 54 provider-free tests.
- All PHP files pass syntax lint.
- Browser JavaScript passes `node --check`.
- Dataset API returns 25 questions and 13 evaluators. After the bounded FP10
  proof, it returns 4 runs and 6 response summaries for the active dataset.
- Response 17 returns 8 real baseline results, 8 immutable attempts, and 3
  exact saved contexts.
- The human-review endpoint created two versions for one temporary reviewer,
  exposed only the newest as current, and the exact temporary rows were removed;
  the public current-review count returned to zero.
- RAGAS 0.4.3 collections classes import successfully with the pinned
  compatibility dependency.
- The July 20 bounded proof and authorized follow-up stored one completed
  LLM-judge result and four completed RAGAS results for response 19. Earlier
  async-adapter, missing-extra, and free-tier throttle failures remain in the
  immutable attempt history; the current canonical rows are completed.
- Genuine MySQL retrieval ranks the expected Fall 2026 source first.
- Desktop Evaluation and Compare Runs views were rendered and visually inspected;
  responsive rules collapse all multi-column evaluation sections on narrow
  screens.

## Remaining Research Work

The implementation enables, but does not fabricate, these next steps:

1. inspect raw outputs, applicability, latency, and provider usage;
2. expand the reviewed evaluation set from 25 to the requested 50 questions;
3. repeat the judge on a stratified subset to observe variability;
4. collect independent human reviews for disagreements and failure cases;
5. run a complete fixed Chroma baseline if budget permits;
6. run matched MySQL/Chroma or top-k comparisons;
7. run a matched focused/full corpus comparison;
8. analyze each evaluator against human/failure evidence; and
9. write conclusions scoped to the tested dataset, corpus, models, versions,
   and settings.

FP10 should emphasize empirical execution, calibration, teaching examples,
final findings, and reproducibility—not another evaluation-framework expansion.
