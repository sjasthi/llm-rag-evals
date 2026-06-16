# UX Design

## Design Goal

The application should translate technical RAG evaluation results into clear
evidence that managers can use for decisions while preserving enough detail for
developers to diagnose retrieval and answer-quality problems.

## Stakeholders and Primary Workflows

| Stakeholder | Primary goal | Supported workflow |
| --- | --- | --- |
| Business user or manager | Decide which RAG configuration or evaluation approach is most useful | Open dashboard, compare runs, inspect summary metrics, read recommendation |
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
and a comparison table or chart. Technical details remain available without
overwhelming the initial business summary.

### Document Management

Uses a clear upload form and searchable table showing document status, type,
upload date, and available actions.

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
