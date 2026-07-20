# UX Design

Implementation status: the task-focused shell, four-layer Experiments
inspector, score contracts, human-review workflow, and evidence-first Findings
workspace described below are implemented as of July 14, 2026. Remaining UX
work is empirical refinement after complete comparison runs, not another broad
frontend redesign.

## Design Goal

The application should translate technical RAG evaluation results into clear
evidence that managers can use for decisions while preserving enough detail for
developers to diagnose retrieval and answer-quality problems.

## Finalized Application Model

The frontend uses task-focused views rather than one long dashboard. Navigation
preserves a stable URL hash for each workspace:

- Overview: research purpose, current baseline, corpus, dataset, and evaluator counts.
- Playground: one interactive question with its answer and evidence side by side.
- Dataset: reviewed question coverage, filters, expected answers, and review state.
- Experiments: immutable run history with a two-pane response inspector for
  outputs, references, evaluator signals, runtime, and retrieved contexts.
- Sources: document ingestion and a contained source library.
- Findings: conclusions, failure patterns, metric trade-offs, and recommendations.

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

The main navigation contains:

- Overview: project purpose, current capabilities, and entry points.
- Playground: question-answer interface with retrieved evidence.
- Dataset: manage reviewed questions and coverage.
- Experiments: compare saved runs and inspect individual responses.
- Sources: upload and manage Metro State documents.
- Findings: summarize research evidence, recommendations, and limitations.

## Key Screens

### Home

Introduces the project to nontechnical users and provides direct actions for
asking a question, managing documents, and viewing evaluations.

### Ask a Question

Uses a focused question form. The result area displays the answer first,
followed by source citations and expandable retrieved chunks.

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

FP8 organizes evaluation evidence into four visibly separate layers:

1. Baseline/local: lexical, required-fact, token-overlap, semantic, BERTScore,
   expected-source, and refusal signals.
2. Advanced: versioned LLM-as-judge plus RAGAS Faithfulness, Response
   Relevancy, Context Precision, and Context Recall.
3. Human calibration: sampled response reviews and failure labels.
4. Operations: response/evaluator runtime, model usage, estimated cost, skips,
   and errors.

These layers do not vote on or generate the answer. They describe different
properties of one already-saved answer and its exact contexts. The default UI
must present a dimensional profile rather than an average of unlike scores.

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

### Implemented Experiments Workspace

The run browser makes experiment coverage and purpose explicit. Each run
summary shows:

- executed responses versus dataset size, for example `3 of 25`;
- dataset version and corpus variant;
- retrieval method, top-k, answer model, and the one controlled variable;
- evaluator coverage by baseline/advanced/human/operations layer;
- completed, skipped, and failed evaluator counts; and
- total runtime and estimated cost when available.

The newest available response remains selected automatically so large empty
panels do not obscure the workflow. The response inspector should show:

1. question, category, difficulty, and answerability;
2. generated answer beside the reviewed reference;
3. saved contexts in rank order with expected-source/evidence indicators;
4. evaluator cards grouped by the four layers;
5. human/failure labels and disagreement review prompts; and
6. expandable audit details.

Each evaluator card should include its name, the question it answers, method
family, retrieval/generation dimension, applicability/status, score and scale,
threshold interpretation, explanation, limitations, inputs, deterministic or
model-judged status, version/model/prompt metadata, runtime, cost, and errors.

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

Replacement identifies which document will be replaced and regenerates its
chunks and embeddings. Deletion requires confirmation and removes a
browser-managed upload from file storage, MySQL, and ChromaDB. Bundled sources
cannot be replaced or deleted. Unsupported, encrypted, empty, and
scanned-without-text files produce understandable messages.

### Evaluation Questions

Provides a searchable list and form for at least 25 reviewed questions. The UI
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
  summaries, layers, results, forms, Findings rules, and catalog cards.
- The home page and empty states distinguish implemented capability, missing
  experiment evidence, and future research conclusions.
