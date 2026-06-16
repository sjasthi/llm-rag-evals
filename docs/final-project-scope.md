# Final Project Scope

## Project Name

LLM RAG Evaluation Project

## One-Sentence Definition

This project is a PHP/MySQL web application that evaluates how well different
RAG configurations answer Metro State questions using retrieved source
documents.

## Project Purpose

The purpose is not simply to build a chatbot. The purpose is to build a small
RAG evaluation system that can answer this question:

> Which RAG configuration gives the most accurate, source-grounded answers for
> Metro State questions?

The final product should help:

- business users or managers understand which approach performs better,
- developers understand which settings improve or weaken the RAG pipeline, and
- the developer demonstrate a repeatable evaluation process.

## Final Product Goal

By the final submission, the application should let a user:

1. Manage a small set of Metro State documents.
2. Ask questions against those documents.
3. See generated answers with retrieved sources.
4. Run a fixed evaluation set of Metro State questions.
5. Compare at least two RAG configurations or evaluation methods.
6. View a summary showing which configuration performed best.

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

The primary focus is RAG behavior:

- Did the system retrieve the correct source chunks?
- Did the generated answer match the expected answer?
- Was the answer grounded in the retrieved context?
- Did changing chunk size, top-k, or temperature improve or weaken results?
- Which configuration is most useful for this document set?

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
- list documents,
- show document type and chunk count,
- replace an existing document,
- delete or deactivate a document if needed.

### 3. Ask

Supports normal RAG question answering:

- question input,
- generated answer,
- source document names,
- retrieved chunk excerpts,
- model/settings used for the response.

### 4. Evaluation Questions

Manages the gold evaluation dataset:

- question,
- expected answer,
- expected source document,
- topic/category,
- active/inactive status.

### 5. Evaluation Runs

Runs selected questions through selected RAG settings:

- chunk size,
- overlap,
- top-k,
- temperature,
- provider/model,
- selected evaluation method.

### 6. Results / Dashboard

Shows:

- average answer score,
- source accuracy,
- faithfulness or groundedness score if available,
- latency,
- estimated API cost if available,
- per-question failures,
- best-performing configuration.

### 7. Report

Summarizes findings in plain language:

- which configuration performed best,
- which questions failed,
- what trade-offs were observed,
- recommended next steps.

## Minimum Required Features

The project should be considered successful if it implements:

1. Metro State document storage.
2. Document chunking.
3. Embedding generation.
4. Similarity retrieval.
5. Answer generation from retrieved context.
6. Source display.
7. Gold question dataset.
8. At least two evaluation methods or two RAG configurations.
9. Stored evaluation results.
10. Results comparison table or dashboard.

## Preferred Focused Final Scope

The preferred final scope is intentionally focused on the evaluation goal:

- 10-20 Metro State documents.
- 30-50 evaluation questions.
- TXT/cleaned text support first.
- PDF/DOCX support if time allows.
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
- Python helper/service for ChromaDB ingestion and retrieval, while PHP remains
  the main application interface.
- Optional offline Python evaluation only if needed for RAGAS.

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
- Production-grade deployment.
- Exhaustive model leaderboard.
- Training or fine-tuning a custom LLM.

## Recommended Final Demo

The final demo should show:

1. The document list.
2. One document replacement or chunk-count example.
3. A user question.
4. The generated answer.
5. The retrieved sources.
6. An evaluation run or stored evaluation results.
7. A comparison between two configurations.
8. A conclusion explaining which configuration performed better and why.

## Example Final Comparison

| Configuration | Chunk Size | Top-K | Temperature | Avg Answer Score | Source Accuracy | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| A | 500 | 3 | 0.0 | 78% | 85% | Faster but missed some context |
| B | 800 | 5 | 0.0 | 86% | 93% | Best balance for the test set |
| C | 800 | 8 | 0.3 | 81% | 90% | More context, less consistent answers |

The final report should explain this table in plain language.

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
