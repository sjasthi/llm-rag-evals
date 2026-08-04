# Final Project Scope

## Project Name

LLM RAG Evaluation Project

## One-Sentence Definition

This project is a PHP/MySQL research application for running repeatable RAG
experiments, comparing the usefulness of evaluation metrics, and studying how
retrieval and document-collection choices affect grounded Metro State answers.

## Project Purpose

The purpose is not simply to build a chatbot or finish a one-time semester
application. The application is the research instrument used to answer these
questions:

> What do different RAG evaluation metrics reveal, which problems does each
> metric detect, where can each metric be misleading, and how are the results
> affected by the document collection and RAG configuration?

The final product should help:

- business users or managers understand which evidence is useful for a
  particular decision,
- developers distinguish ingestion, retrieval, and generation failures,
- researchers understand where metrics agree or disagree, and
- future developers reproduce and extend the experiments.

The final report should recommend metrics for specific uses. It should not
claim that one metric, provider, or configuration is universally best.

The working emphasis is to research and explain representative evaluator types
across multiple method families. The professor's reference lists eight broad
options, not eight required advanced models. RAGAS is part of this comparison,
not the sole evaluation approach. The project must teach what each score is
based on, why scores differ, and each evaluator's inputs, cost, speed,
determinism, strengths, limitations, and appropriate use cases. The detailed
working set and protocol are defined in `docs/evaluation-strategy.md`.

## Current Implementation Boundary (August 2, 2026)

The complete application support through FP9 is present: eight baselines, five
advanced evaluator paths, immutable attempts, reproducible controlled runs,
MySQL/Chroma retrieval choices, human response review, status-first Evaluation,
and evidence-first Compare Runs. FP10 hardening now adds immutable answer-key and
context provenance, code/runtime/dependency fingerprints, generation usage and
honest unknown-cost states, guarded paid-call paths, same-question/evaluator
comparison rules, accessibility improvements, provider-free CI, and a complete
demo/checkoff record. The frontend-first follow-up adds active chunk counts,
organized delete/replace-capable document administration, an approved Chat
model selector, and run-level evaluator preflight/execution. Chat exposes
retrieval, top-k, temperature, and top-p and can preview sources without calling
a model. The UI also explains that controlled Gold Standard questions use the same answer pipeline
as Chat and reports Local, LLM-judge, and RAGAS status separately. A July 20 bounded proof produced one live response, one
completed LLM-judge result, and four completed current RAGAS results while
retaining earlier adapter/dependency/quota failures in attempt history; it did
not produce a human calibration set or matched final experiment. The August 3
continuation now adds six completed exact-question controlled conditions,
matched advanced evidence, portable final-study exports, and an empirical
report/recommendation draft. Seven selected final-study responses now have
single-reviewer overall human decisions for descriptive calibration. The
final-readiness pass adds the
source-verified 50-question v2.0 Gold Standard while preserving v1.0 and adds
per-run JSON/CSV evidence downloads for the final report.

## Final Product Goal

By the final submission, the application should let a user:

1. Upload and manage TXT, text-based PDF, and DOCX Metro State documents.
2. Ask questions against those documents.
3. See generated answers with retrieved sources.
4. Run a reviewed evaluation set containing 50 Metro State questions.
5. Apply multiple evaluation metrics to the same stored responses.
6. Compare retrieval/configuration and collection-size experiments.
7. Inspect metric disagreements and categorized failure cases.
8. View findings explaining which metrics are useful for which purposes.

## Research Contribution

The expected contribution is a documented, reproducible evaluation method and
the findings produced with it. The project should leave behind:

- a reviewed evaluation question set with expected answers and sources;
- response, context, setting, latency, and score records that can be audited;
- an explanation of each implemented metric's usefulness and limitations;
- comparisons showing metric agreement and disagreement;
- evidence separating retrieval failures from answer-generation failures;
- a controlled experiment on document-collection size or composition; and
- limitations and future questions for organizations with hundreds, thousands,
  or millions of documents.

## What Is Being Evaluated

The project evaluates the RAG system as a whole, not just the language model.

A RAG configuration includes:

- selected document set,
- chunk size,
- chunk overlap,
- retrieval top-k,
- embedding model/provider,
- answer model/provider,
- generation settings such as temperature and top-p,
- prompt format,
- evaluation method.

The same evaluation questions should be run against different configurations so
the results are comparable.

## Primary Evaluation Focus

The primary focus is RAG behavior and the behavior of the metrics used to
measure it:

- Did the system retrieve the correct source chunks?
- Did the generated answer match the expected answer?
- Was the answer grounded in the retrieved context?
- Did changing chunk size, top-k, or temperature improve or weaken results?
- Which configuration is most useful for this document set?
- How do MySQL-based retrieval and ChromaDB-based retrieval compare for this
  project dataset?
- Do exact match, semantic similarity, source accuracy, and groundedness agree
  on which responses are successful?
- Which failure types does each metric detect or miss?
- Does adding more or more-similar documents change source ranking, answer
  quality, refusal behavior, latency, or metric agreement?

This is the core of the project.

## Secondary Evaluation Focus

Comparing model providers is allowed, but it is secondary.

Provider comparisons should only be done if the rest of the RAG pipeline is
stable. If providers are compared, the comparison should keep the documents,
questions, chunking, top-k, prompt, and scoring method as consistent as
possible.

The project should not claim that one model is universally better than another.
It should only claim how each provider performed in this specific Metro State
RAG setup.

Example acceptable claim:

> With the same document set, top-k value, and evaluation questions, Provider A
> produced higher source-grounded scores but had higher average latency.

Example claim to avoid:

> Provider A is better than Provider B.

## Final System Pages

The finished application should aim for these pages:

### 1. Home / Overview

Explains what the project does, what is being evaluated, and the current project
status.

### 2. Documents / Admin

Supports document management:

- upload or import Metro State documents,
- search, filter, sort, and group active documents,
- show document type and chunk count,
- replace an existing or same-name document,
- delete any active document or clear the active index if needed.

### 3. Chat

Supports normal RAG question answering:

- question input,
- browser controls for approved model, retrieval method, top-k, temperature, and top-p,
- provider-free preview of the ranked source chunks,
- generated answer,
- source document names,
- retrieved chunk excerpts,
- model/settings used for the response.

### 4. Gold Standard

Manages the gold evaluation dataset:

- question,
- expected answer,
- expected source document,
- topic/category,
- active/inactive status.

### 5. Evaluation

Creates and inspects saved tests using selected RAG settings:

- top-k,
- retrieval method,
- temperature,
- provider/model,
- top-p.

The browser can preview and create a bounded new test with approved model,
retrieval, top-k, temperature, top-p, exact reviewed-question selection, and a full or
category-scoped source collection. It can label a run as a controlled baseline
or create a one-setting comparison by choosing an existing completed baseline;
the browser copies and locks the other settings/questions and the server verifies
the exact question set and actual difference count. New answers receive the local eight scores
automatically. Every saved test also exposes
preflight and execution for either the local eight across the full test or all
13 methods for one exact selected answer under the configured response,
application, and cost limits.

The same view shows:

- each named answer/retrieval score with its own calculation, scale, threshold
  provenance, applicability, and limitation,
- source accuracy and retained rank,
- faithfulness or groundedness when applicable,
- latency,
- estimated API cost if available,
- per-question failures,
- metric agreement/disagreement,
- results grouped by configuration and corpus variant,
- the selected answer's metric value beside that metric's cumulative average
  across completed tests, and
- each metric's current-test mean beside its all-completed-tests mean.

The dashboard must not average unlike lexical, semantic, retrieval, judged, and
human signals into one universal answer grade.

Chunk size, overlap, and embedding model describe the active index rather than
one answer. Comparing those settings requires a separately re-chunked and
re-embedded corpus variant so each test uses one internally consistent index.

### 6. Compare Runs

Provides the secondary, research-oriented comparison reached from Evaluation.
It shows compatible configuration evidence and only computes deltas for
question/evaluator-matched baseline pairs.

### 7. Report

Summarizes findings in plain language:

- which configurations performed better for the tested goals and conditions,
- which metrics provided useful or misleading evidence,
- which questions failed,
- whether failures originated in parsing, retrieval, generation, expected data,
  or scoring,
- what trade-offs were observed,
- which conclusions are limited to the tested corpus,
- recommended next steps.

## Minimum Required Features

The project should be considered successful if it implements:

1. Metro State document storage.
2. Document chunking.
3. Embedding generation.
4. Similarity retrieval.
5. Answer generation from retrieved context.
6. Source display.
7. A manually reviewed dataset of at least 25 questions covering the current
   categories and including unanswerable cases.
8. Representative evaluator types spanning lexical/token overlap, semantic,
   contextual embedding, source/retrieval, LLM-as-judge, and RAGAS measures,
   applied to common stored responses with documented score contracts.
9. Stored per-question evaluation results and run settings.
10. At least one controlled retrieval/configuration comparison.
11. A controlled document-collection size or composition comparison.
12. Results and failure-analysis views that explain metric usefulness.
13. TXT, text-based PDF, and DOCX ingestion through the document interface.

## Preferred Focused Final Scope

The preferred final scope is intentionally focused on the evaluation goal:

- The existing 27 Metro State documents as the initial baseline, with approved
  additions when they support a research experiment.
- The final 50 reviewed v2.0 evaluation questions, with the 25-question v1.0
  set retained for historical-run reproducibility.
- Browser-based TXT, text-based PDF, and DOCX upload and ingestion.
- No requirement to reproduce enterprise scale locally; use controlled document
  subsets/additions and state the limits of extrapolating to very large corpora.
- One main LLM provider working end-to-end.
- Optional second provider if it helps demonstrate provider trade-offs.
- No full authentication unless required; this is expected to be a local class
  demonstration.
- Optional simple admin passcode only if the professor expects an admin area to
  be separated from user-facing pages.
- MySQL storage for metadata, questions, expected answers, responses,
  evaluation runs, scores, and settings.
- ChromaDB storage for chunks, embeddings, source metadata, and vector
  retrieval.
- MySQL and ChromaDB should be treated as comparison options where practical,
  based on the instructor's note.
- Python helper/service for ChromaDB ingestion and retrieval, while PHP remains
  the main application interface.
- Python evaluation layer for local evaluator libraries, LLM-as-judge, and the
  selected RAGAS metrics while PHP remains the main application interface.

## Out of Scope Unless It Supports the Evaluation Goal

These are intentionally excluded unless the professor requires them or they
directly improve the RAG evaluation outcome:

- React frontend.
- Flask as the main application server.
- Full user account system.
- Multi-user chat history.
- Google Cloud Storage.
- Large-scale vector infrastructure beyond local ChromaDB.
- Multi-agent RAG.
- Real-time streaming responses.
- Production-grade deployment beyond the course hosting/demo requirement.
- Exhaustive model leaderboard.
- Training or fine-tuning a custom LLM.

The final project review identified multimodal ingestion, conversation memory,
multi-user isolation, and bounded agentic RAG as valuable follow-on research.
They remain outside the submitted implementation rather than being silently
added to its claims. See the [post-capstone RAG research roadmap](post-capstone-roadmap.md)
for proposed architectures, experiments, and acceptance criteria.

## Recommended Final Demo

The final demo should show:

1. The document list.
2. One document replacement or chunk-count example.
3. A user question.
4. The generated answer.
5. The retrieved sources.
6. An evaluation run or stored evaluation results.
7. A comparison between two configurations.
8. Cases where metrics agree and disagree.
9. A corpus-size or composition comparison.
10. A conclusion explaining which metrics are useful for particular decisions,
    what failed, and what cannot yet be generalized.

## Example Final Comparison Structure

| Configuration | Retrieval | Top-K | Dataset coverage | Expected-source hit rate | RAGAS faithfulness | Human acceptable | Runtime/cost | Notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| A | Chroma | 3 | measured/50 | report observed | report observed | reviewed sample | recorded | Fixed baseline |
| B | MySQL | 3 | measured/50 | report observed | report observed | reviewed sample | recorded | Retrieval method changed only |

The placeholders must be replaced with stored experiment evidence. The final
report should explain metric trade-offs in plain language and may not invent an
`Avg Answer Score` by mixing incompatible metrics.

## Difference From `implementation-approach.md`

`final-project-scope.md` defines the project boundaries:

- what the final product is,
- what it is not,
- what success means,
- what should be demonstrated,
- which features are required versus optional.

`implementation-approach.md` explains how to build it:

- architecture,
- storage strategy,
- API key handling,
- development phases,
- implementation trade-offs.

Read this scope document first when deciding what belongs in the project. Read
the implementation approach when deciding how to build the selected scope.
