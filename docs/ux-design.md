# UX Design

## Design Goal

The application should translate technical RAG evaluation results into clear
evidence that managers can use for decisions while preserving enough detail for
developers to diagnose retrieval and answer-quality problems.

## Stakeholders and Primary Workflows

| Stakeholder | Primary goal | Supported workflow |
| --- | --- | --- |
| Business user or manager | Understand which evidence and metric are useful for a decision | Open dashboard, compare runs, inspect metric explanations and limitations, read findings |
| Developer | Build and improve the RAG pipeline | Review configuration, run tests, inspect retrieved chunks, diagnose low scores |
| Administrator | Maintain the knowledge base and test set | Upload documents, manage test questions, run evaluations, review history |
| General user | Ask a Metro State question and verify the answer | Submit question, read answer, inspect cited sources |

## Information Architecture

The main navigation will contain:

- Home: project purpose, current capabilities, and entry points.
- Ask: question-answer interface with retrieved sources.
- Documents: upload and manage Metro State documents.
- Evaluations: manage test cases and launch evaluation runs.
- Dashboard: compare metrics, configurations, and previous runs.
- Reports: summarize findings and recommendations.
- About: explain the project, evaluation methods, and limitations.

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
should have a plain-language definition, intended use, and limitation.
Technical details remain available without overwhelming the initial business
summary.

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

## Interaction and Accessibility Guidelines

- Use plain-language labels and explain technical metrics with tooltips.
- Do not communicate pass/fail status by color alone.
- Maintain keyboard-accessible controls and visible focus states.
- Use semantic headings, form labels, and descriptive button text.
- Confirm destructive operations such as deleting documents or test cases.
- Show loading, success, empty, and error states for asynchronous operations.
- Design mobile-first with Bootstrap breakpoints.

## Initial Visual Direction

- Dark blue and teal establish a professional analytics theme.
- White cards and restrained shadows separate content clearly.
- Metric and framework cards provide scannable summaries.
- Icons support labels but do not replace text.
- The home page shows planned functionality honestly instead of presenting
  unfinished features as operational.
