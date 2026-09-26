# UX Design

Implementation status: the task-focused shell, progressive-disclosure Chat, provider-free
source preview, guided baseline/comparison launcher, study-readiness checklist,
status-first Evaluation inspector, score contracts, human-review workflow,
portable run exports, and evidence-first run comparison described
below are implemented as of August 3, 2026. The July 20 simplification pass renamed the user-facing
sections around tasks while retaining the richer experiment data model behind
them.

The global status pill is evidence-based: it begins at **Checking
application…**, becomes **Application data ready** only after a server health
response, and otherwise gives a user-safe unavailable state. Operational
details remain in logs and setup documentation.

## Design Goal

The application should translate technical RAG evaluation results into clear
evidence that managers can use for decisions while preserving enough detail for
developers to diagnose retrieval and answer-quality problems.

## Finalized Application Model

The frontend uses task-focused views rather than one long dashboard. Navigation
preserves a stable URL hash for each workspace:

- Overview: purpose, current corpus, test-question, and evaluator counts.
- Chat: one interactive question with configurable retrieval/generation settings,
  its answer, and evidence side by side.
- Documents: source ingestion and a contained source library.
- Gold Standard: reviewed test-question coverage, expected answers, cited
  evidence, and review state.
- Evaluation: immutable batch-run history with a two-pane response inspector for
  outputs, references, evaluator signals, runtime, and retrieved contexts.
- Compare Runs: a secondary view reached from Evaluation for matched comparisons,
  failure patterns, metric trade-offs, and recommendations.

This lifecycle follows established LLM-evaluation product patterns: iterate on
one case in a playground, maintain a versioned dataset, preserve experiments,
inspect individual failures and traces, then turn evidence into findings. It
maps directly to the capstone research protocol without exposing internal FP
milestone organization as the primary user experience.

## Stakeholders and Primary Workflows

| Stakeholder | Primary goal | Supported workflow |
| --- | --- | --- |
| Business user or manager | Understand which evidence and metric are useful for a decision | Open dashboard, compare runs, inspect metric explanations and limitations, read findings |
| Developer | Build and improve the RAG pipeline | Review configuration, run tests, inspect retrieved chunks, diagnose low scores |
| Administrator | Maintain the knowledge base and test set | Upload documents, manage test questions, run evaluations, review history |
| General user | Ask a Metro State question and verify the answer | Submit question, read answer, inspect cited sources |

## Information Architecture

The main navigation contains five task labels:

- Overview: project purpose, current capabilities, and entry points.
- Chat: ask one question, choose settings, preview sources, and inspect evidence.
- Documents: upload and manage Metro State documents.
- Gold Standard: manage the reviewed answer key and coverage.
- Evaluation: create and inspect saved batch runs, download evidence, and review
  individual responses.

Compare Runs is intentionally reached from Evaluation instead of occupying the
main navigation. This keeps advanced research analysis available without making
it part of the first-time user's required path.

## Plain-Language Evaluation Model

The user-facing model is:

1. Overview states the research question: which evaluation method is most
   useful for a specific RAG-response failure and decision?
2. Gold Standard contains the test answer key: a reviewed question, expected
   answer, and expected evidence.
3. A test run sends several reviewed questions through the same retrieval and
   generation pipeline used by Chat, with one fixed configuration.
4. Evaluation stores each generated answer, its retrieved sources, and separate
   metric statuses for every answered question.
5. Compare Runs only claims a difference when the same questions and the same
   quality check exist in both runs.
6. Conclusions use a portfolio: local checks screen broadly, LLM judge/RAGAS
   diagnose selected cases, and human review calibrates disagreements.

“Dataset” and “experiment” remain valid research/database terms, but they are
not used as unexplained primary navigation labels. Chat history is never the
evaluation answer key.

## Key Screens

### Home

Introduces the project to nontechnical users and provides direct actions for
asking a question, managing documents, and viewing evaluations.

### Ask a Question

Uses a focused question form. The result area displays the answer first,
followed by source citations and retrieved chunks. Recommended defaults keep
the normal path simple. Researchers can expand Advanced settings to choose
vector or keyword retrieval, top-k, temperature, top-p, and an approved model.
A plain-language summary makes the active configuration visible, Reset Defaults restores the
environment-backed choices, and Preview Sources runs retrieval without a paid
model call. Answer generation remains disabled unless the local paid-call guard
is explicitly enabled.

### Evaluation Dashboard

Uses summary cards for major metrics, filters for model and retrieval settings,
and a comparison table or chart. It must allow users to inspect cases where
metrics disagree instead of presenting only one combined score. Each metric
must have a plain-language definition, score basis, intended use, and
limitation.
Technical details remain available without overwhelming the initial business
summary.

The dashboard must support the layered evaluator research objective without
collapsing unlike scores into one unexplained grade. Each evaluator
view should identify whether it measures retrieval, generation, or both and
show its method family, score, explanation/details, runtime, cost estimate,
version/configuration, and error state. Users must be able to hold a question
and saved response fixed while comparing evaluator outputs side by side.

The Evaluation UI names three automatic method families instead of presenting an
abstract numbered layer model:

- Local metrics: lexical, required-fact, token-overlap, semantic, BERTScore,
  expected-source, and refusal signals.
- LLM judge: one versioned rubric evaluator.
- RAGAS: Faithfulness, Response Relevancy, Context Precision, and Context Recall.

Human review is labeled as supporting calibration evidence, not another
automatic evaluator. Runtime, usage, cost, skips, and failures are operational
metadata. None of these methods vote on or generate the answer: they describe
different properties of one already-saved answer and its exact contexts. The
default UI presents a dimensional profile rather than an average of unlike
scores.

### Score Explanation Contract

A raw number is not sufficient. Every evaluator result card must answer:

- Based on what? Identify the exact comparison target: reference answer,
  required-fact list, question, ordered contexts, expected source, or
  answerability label.
- How was it calculated? Show the human-readable rule, scale, direction, and
  numerator/denominator or precision/recall details where applicable.
- What is the threshold? Show its exact value and label it as calibrated,
  project-defined/descriptive, or absent.
- What happens below it? Explain that a descriptive cutoff creates a review
  flag, not proof that an answer is wrong.
- What does it not mean? State the evaluator's most important limitation.
- Can it be audited? Show evaluator/library/model/prompt version, status,
  runtime, cost, and expandable details/errors.

For example, `Required fact coverage 1.0` should display `1 of 1 reviewed facts
found` and list the matched fact. It must not imply that the entire answer is
perfect. `BERTScore F1 0.953` should show that it compared contextual tokens in
the generated and reference answers, include precision/recall and the model,
and say `Above project review threshold 0.80`. It must not present the value as
`95.3% factually correct`.

Until thresholds are validated against human-reviewed examples, avoid the
labels `Correct` and `Incorrect` on thresholded similarity cards. Prefer
`Above review threshold`, `Below review threshold`, `Not applicable`,
`Skipped`, and `Failed`.

### Implemented Evaluation Workspace

Evaluation leads with the boundary between generating and scoring: **New test
run** creates answers, while **Score saved answers** only applies metrics to
text that already exists. A bounded browser form exposes approved model,
retrieval, top-k, temperature, top-p, exact reviewed-question selection, and full or
category-scoped sources with a call/cost preview. Quick, baseline, and
comparison modes use task language. Selecting a comparison baseline copies its
settings and exact ordered questions, shows a readable summary, and disables every
control except the one variable chosen for the experiment. The server repeats
the zero/one/multiple-change check. A five-item study checklist turns stored
evidence into concrete next actions for the final report.

The saved-test browser makes scope and purpose explicit. Completed tests appear
first; interrupted records are collapsed under **Earlier attempts needing
attention** with a recovery explanation. Each test summary shows:

- saved-answer scope versus the Gold Standard;
- saved method-result slots versus the 13 available methods;
- whether all 13, the local eight, or only partial results are available;
- concise completed/skipped/failed status; and
- expandable model/retrieval settings and technical run identity.

The newest available response remains selected automatically so large empty
panels do not obscure the workflow. Database IDs are hidden from primary labels;
answers are shown as `Question 1 of 3`, with internal IDs available only in
technical provenance. The response inspector should show:

1. question, category, difficulty, and answerability;
2. generated answer beside the reviewed reference;
3. saved contexts in rank order with expected-source/evidence indicators;
4. a status summary for Local metrics, LLM judge, RAGAS, and human review;
5. collapsed, individually named evaluator cards grouped by the three
   automatic method families;
6. human/failure labels and disagreement review prompts; and
7. expandable audit details.

Each evaluator card should include its name, the question it answers, method
family, retrieval/generation dimension, applicability/status, score and scale,
threshold interpretation, explanation, limitations, inputs, deterministic or
model-judged status, version/model/prompt metadata, runtime, cost, and errors.

### FP10 Evidence and Accessibility Pass

FP10 makes the research state and audit trail visible without requiring users
to infer it from database fields:

- Chat shows whether paid generation is enabled, disables Ask while the local
  paid-call flag is off, and keeps provider-free source preview available.
- Response metadata distinguishes recorded generation usage from unavailable
  usage/cost and exposes answer-key snapshot and code provenance.
- Retrieved evidence displays semantic distance, lexical signal, final ranking
  score, and retrieval algorithm version when captured.
- Compare Runs puts question-matched baseline evidence before descriptive run cards
  and shows an explicit empty state when no valid pair exists.
- Global catalog cards teach score contracts and coverage; they are not a
  cross-run leaderboard.
- The reviewed answer-key workspace is named Gold Standard; saved tests and
  scores are named Evaluation. Each test exposes preflighted **Score saved
  answers** controls plus a direct per-answer **Evaluate** action. Each metric
  card shows the selected answer value and completed-test cumulative mean;
  current-test and all-test means remain available separately.
- The metric dependency guide separates gold-standard-dependent methods from
  RAGAS Faithfulness and Response Relevancy, which do not require a gold answer.
- Documents exposes search, category/type filtering, sorting, category groups,
  explicit Replace/Cancel conflict handling, replacement/deletion for every
  active source, verified vector cleanup, and a confirmed Delete All. Successful
  corpus changes clear an already-rendered Chat source preview.
- Overview includes the live active chunk count and Chat includes an
  allowlisted model selector inside collapsed Advanced settings.
- Evaluation visibly recommends a three-layer evaluator portfolio rather than
  a universal combined grade. Local-complete tests no longer look unfinished
  merely because optional advanced methods were not run, interrupted records
  are labeled as archived audit history, and the evidence-rich completed test
  is selected first.
- Human-facing labels replace category slugs, primary run IDs, and raw model or
  retrieval identifiers; exact IDs remain in expandable technical provenance.
- Gold Standard explains why reviewed references are needed for correctness,
  fact, retrieval, and refusal claims while distinguishing the two available
  reference-free RAGAS checks.
- Evaluation includes a goal-first decision guide. A visitor chooses overall
  confidence, correctness/completeness, grounding, retrieval, relevance,
  refusal, or low-cost regression and receives a recommended starting method,
  complementary evidence, limitation, and Gold Standard dependency.
- Compare Runs states both the evaluator-process recommendation and the bounded
  current RAG default beside the evidence scope and limitations that support it.
- Previously tiny audit text is raised to a readable floor, secondary colors
  have stronger contrast, disclosure controls have larger targets, keyboard
  focus is visible, browser Back/Forward navigation works across workspace
  views, and reduced-motion preferences are honored.

The full single-page workspace received the typography, contrast, focus, and
responsive pass; Chat, Evaluation, and Compare Runs received the deepest
workflow changes because they contain the model-cost and research-claim risks.

### Choosing a Metric

The evaluator catalog and expandable score contracts provide a purpose-based
guide instead of a winner leaderboard:

| User concern | Primary evidence | Required complementary evidence |
| --- | --- | --- |
| Cheap regression | required facts, ROUGE/token F1, semantic similarity | inspect changed/flagged cases |
| Correctness/completeness | LLM-judge rubric | baseline evidence and sampled human review |
| Hallucination/grounding | RAGAS Faithfulness | retrieved contexts and correctness review |
| Direct answer relevance | RAGAS Response Relevancy | correctness and faithfulness because relevance alone can be wrong |
| Retrieval ranking/noise | RAGAS Context Precision | expected-source rank/context inspection |
| Missing retrieval evidence | RAGAS Context Recall | verified reference evidence |
| Unanswerable behavior | refusal correctness and judge refusal rubric | human review; inapplicable RAGAS metrics are skipped |
| Release/high-risk decision | relevant metric profile | human review; never one automated score |

### Disagreement and Applicability

Disagreement is research evidence, not automatically a system error. The UI
should identify cases worth review, such as high semantic similarity with low
judge correctness, high relevance with low faithfulness, or high faithfulness
with low context recall. Initially these are review prompts, not automatic
diagnoses based on arbitrary thresholds.

`Not applicable`, `Skipped`, `Failed`, and numeric zero are distinct states.
For example, Context Recall normally does not apply to a deliberately
unanswerable question; that is not a zero-quality result. Evaluator failures
must not make the RAG response appear incorrect.

### Dataset Review Versus Response Review

The Dataset `Reviewed`, `Needs revision`, and `Draft` controls describe whether
the test question, expected answer, and expected evidence are trustworthy. They
do not ask a reviewer to judge every generated response from memory.

FP8 human response review is a separate sampled workflow. It presents the
generated answer together with the reviewed reference and source evidence, then
records correctness, completeness, faithfulness, relevance/helpfulness,
refusal behavior, and a failure label as applicable. Users should prioritize
disagreement and high-risk cases rather than manually review every possible
answer.

### Document Management

Uses a clear upload form and indexed list showing document status, type, chunk
count, and available actions. The implemented FP6 browser form accepts TXT,
text-based PDF, and DOCX files. It shows the selected filename and size before
submission, an elapsed parsing/ingestion state, and specific validation or
parser errors. Successful ingestion updates the list and dashboard counts
without a page reload.

The form now states the text-only capability boundary before upload: embedded
pictures, charts, and scanned pages remain in the source file but are not OCR'd,
chunked, or embedded. This prevents a successful DOCX/PDF upload from implying
that its visual content is searchable.

Replacement identifies which document will be replaced and regenerates only
its chunks and embeddings. Selecting a duplicate filename first presents a
Replace existing/Cancel upload decision; no silent replacement is initiated.
The old vectors are verified absent before removal is considered complete, so
Chat source preview cannot silently reuse stale chunks. A successful corpus
change also clears any already-rendered Chat source preview. Deletion requires
confirmation and removes any
active source from MySQL and ChromaDB; uploaded files are removed from storage,
while bundled seed files remain as recovery material. **Restore bundled
sources** re-indexes that starting collection from the same page and preserves
uploads. Delete All clears the active index after typed confirmation.
Unsupported, encrypted, empty, and
scanned-without-text files produce understandable messages.

### Evaluation Questions

Provides a searchable list and form for the 50 reviewed v2.0 questions. The UI
should display expected answer, expected source, category, difficulty, and
whether the question is answerable from the corpus. Filters should help verify
coverage across categories and answerability before running experiments.

### Research Results and Failure Analysis

Provides run-level summaries plus per-question drill-down. A detail view should
show the question, expected answer/source, generated answer, retrieved chunks,
settings, each metric score, and any assigned failure category. Users should be
able to compare corpus variants or RAG settings while holding other variables
fixed.

The comparison view should expose teaching examples: correct paraphrases that
lexical metrics penalize, factually wrong answers that semantic metrics score
highly, faithful answers based on incomplete retrieval, context
precision/recall trade-offs, and disagreements between automated metrics and
human review.

## Interaction and Accessibility Guidelines

- Use plain-language labels and explain technical metrics with tooltips.
- Do not communicate pass/fail status by color alone.
- Maintain keyboard-accessible controls and visible focus states.
- Use semantic headings, form labels, and descriptive button text.
- Confirm destructive operations such as deleting documents or test cases.
- Show loading, success, empty, and error states for asynchronous operations.
- Design mobile-first with Bootstrap breakpoints.

## Implemented Visual Direction

- Deep forest green, lime, orange, warm paper surfaces, and restrained shadows
  establish the research-workspace hierarchy.
- Dense run and metric cards remove the earlier large empty areas while keeping
  source evidence and explanations readable.
- Layer number, label, state text, and border treatment prevent color from being
  the only status cue.
- Desktop uses a compact run/response split view; responsive breakpoints stack
  summaries, layers, results, forms, comparison rules, and catalog cards.
- The home page and empty states distinguish implemented capability, missing
  experiment evidence, and future research conclusions.
