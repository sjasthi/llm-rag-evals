# Post-Capstone RAG Research Roadmap

## Status and Purpose

The submitted capstone is a completed, working text-RAG evaluation baseline.
This document records researched extensions that could be investigated after
the course. It does not claim that multimodal retrieval, conversation memory,
multi-user isolation, or agentic RAG are implemented in the submitted system.

The roadmap keeps the project's central question in view:

> What is the best way to evaluate a RAG response?

Each proposed capability therefore includes an evaluation plan. Adding a more
complex RAG architecture is useful only if its quality, evidence, latency,
cost, and failure modes can be compared with the completed baseline.

## Completed Baseline

| Area | Final submitted behavior |
| --- | --- |
| Document ingestion | Browser-managed UTF-8 TXT, text-based PDF, and DOCX upload, replacement, deletion, and bundled-source restoration |
| Text preparation | Normalized text split into 800-character passages with 100-character overlap |
| Embeddings | Local `all-MiniLM-L6-v2` embeddings persisted in ChromaDB; each vector has 384 dimensions |
| Retrieval | Chroma semantic retrieval with lexical reranking, plus MySQL FULLTEXT as a controlled comparison |
| Answer generation | Single-turn, source-grounded Gemini response with saved evidence, settings, usage, latency, and provenance |
| Evaluation | A 50-question reviewed answer key, eight local checks, one LLM judge, four RAGAS methods, and human review |
| Research evidence | Six controlled five-question study conditions, portable exports, matched comparison rules, and documented limitations |
| Interface | Overview, Chat, Documents, Gold Standard, Evaluation, and Compare Runs views for browser-only users |

The baseline is intentionally narrow. It establishes a stable comparison point
before adding features that introduce new model calls, state, storage, and
failure modes.

## Capability Boundary at Submission

### Documents containing pictures, charts, or scanned pages

The complete uploaded source file is retained in ignored runtime storage while
it is active. A DOCX therefore still contains its original embedded pictures,
and a PDF still contains its rendered pages. Replacement exchanges the entire
source file; it does not merge pictures from the old and new versions.

The current knowledge index is text-only:

- DOCX ingestion reads paragraphs and tables with `python-docx`.
- PDF ingestion reads the extractable text layer with `pypdf`.
- Embedded image pixels are not passed through OCR or a vision model.
- A scanned, image-only PDF is rejected when it contains no extractable text.
- Only extracted text is chunked and embedded.
- Text drawn inside a chart or screenshot is consequently not searchable.

This distinction is important: preserving a picture inside the stored source
does not mean the RAG system understands or retrieves that picture.

### Follow-up questions

Chat sends one question at a time. The answer endpoint does not receive earlier
messages or a conversation identifier. A question such as “What about the
spring date?” cannot safely depend on an earlier question unless it repeats the
missing subject.

### Multiple users

The local web server can receive separate HTTP requests, but that alone is not
multi-user RAG. The submitted application has no login, user identifier,
conversation owner, role model, or tenant boundary. Its knowledge base and
saved research evidence are a shared local workspace.

### Agentic behavior

The submitted answer path is deterministic at the workflow level:

```text
question -> retrieve top-k passages -> construct grounded prompt -> generate answer
```

It does not create a plan, select tools, issue subquestions, retry retrieval, or
judge whether additional evidence is required.

## Enhancement 1: Multimodal RAG

### Research goal

Answer questions whose evidence appears in diagrams, screenshots, tables,
graphs, and charts—for example, questions about values or trends shown only in
an NVIDIA report figure.

OCR alone is not sufficient. OCR may recover labels and numbers, but a chart
question can also require understanding axes, legends, spatial relationships,
and the connection between a figure and nearby text.

### Recommended first architecture

The project's included [multimodal RAG guide](Hands_On_Guide_to_Multimodal_RAG_Systems.pdf)
describes a summary-linked design: extract text, tables, and images; create
searchable summaries; retain links to the raw elements; retrieve by summary;
and give the original elements to a multimodal model for synthesis. This is the
best fit for the current codebase because it can reuse the existing text
embedding and Chroma retrieval path.

```text
PDF or DOCX
    |
    v
layout-aware extraction
    |-- text passages -------------------------+
    |-- tables -> structured text/summary -----+--> text embeddings -> ChromaDB
    `-- pictures/charts -> vision summary -----+
                                |
                                `--> asset ID -> original page/image storage

question -> retrieve summaries -> resolve asset IDs -> Gemini text + image input -> answer
```

The ingestion-time vision summary should record observable content rather than
invent an interpretation. A structured result could include:

- page number and figure label;
- element type: picture, chart, diagram, table, or scanned page;
- visible title, labels, legend, axes, units, and values;
- short factual description;
- OCR text when applicable;
- extraction model and prompt version;
- confidence/warnings for unreadable or ambiguous elements.

The raw page or image must remain linked to the summary. Passing only a caption
to the answer model would make the system caption-aware, but not fully
multimodal at answer time.

### Alternative research condition

A second condition could use native multimodal embeddings for both text and
visual elements. NVIDIA's current RAG Blueprint documents VLM embeddings and a
VLM reranker for PDF pages, charts, tables, and images. That is a useful
architecture comparison, but it has substantially greater infrastructure and
GPU requirements than the capstone's local MiniLM baseline.

The comparison should therefore be:

1. text layer only—the submitted baseline;
2. vision-generated summaries retrieved with the existing text embedder;
3. native multimodal embeddings and reranking, if suitable hardware is
   available.

### Proposed data changes

A future `document_assets` table could contain:

| Field | Purpose |
| --- | --- |
| `asset_id` | Stable identifier for one visual or structured element |
| `document_id` | Parent source document |
| `page_number` | User-facing evidence location |
| `element_type` | Image, chart, table, diagram, or scanned page |
| `storage_path` | Server-controlled path to the raw element |
| `content_hash` | Replacement and provenance verification |
| `extracted_text` | OCR or structured table text, when available |
| `vision_summary` | Text used for retrieval |
| `extractor_version` | Parser/model/prompt provenance |
| `status` and `error` | Partial-failure visibility |

Retrieved evidence would record both a chunk ID and, when applicable, an asset
ID. This allows the UI and exports to show the exact page or figure used.

### Proposed interface changes

- Show page, table, chart, and picture counts after ingestion.
- Label a source as text-only, OCR-assisted, caption-assisted, or multimodal.
- Preview retrieved figures beside their summaries.
- Display the original page number and figure identifier in source cards.
- Explain extraction failures instead of silently omitting visual evidence.
- Allow an administrator to reprocess a failed visual element without
  re-ingesting unrelated documents.

### Evaluation design

Create a separate, reviewed multimodal subset containing at least these cases:

- a value found only in a chart;
- a trend or comparison represented spatially;
- a table with merged or visually grouped cells;
- a screenshot with interface labels;
- a figure whose caption is insufficient without the image;
- a control question answerable from ordinary nearby text;
- an unanswerable visual question requiring refusal.

Measure each architecture with:

- required-fact or numeric-value accuracy;
- expected page/figure retrieval accuracy;
- answer faithfulness to the retrieved visual evidence;
- human review of chart interpretation;
- extraction failure rate;
- ingestion latency and model cost;
- answer latency and token/image usage.

Do not evaluate multimodal support only with a general text answer score. The
test set must identify where the expected evidence exists and whether the
system actually retrieved the correct visual element.

### Acceptance criteria

- The system identifies visual elements without losing ordinary document text.
- A chart-only question retrieves the correct page/figure.
- The answer cites that page/figure and reports units correctly.
- Replacing a document removes its old text and visual assets.
- A visual extraction failure is visible and does not falsely mark the whole
  document as fully multimodal.
- The multimodal condition can be compared with the frozen text-only baseline.

## Enhancement 2: Conversation History and Context

### Research goal

Support follow-up questions while keeping retrieval reproducible and preventing
old conversation details from silently contaminating unrelated questions.

Conversation support affects two different stages:

1. **Retrieval:** resolve references such as “it,” “that deadline,” or “the
   second option” into a query that can retrieve the right evidence.
2. **Generation:** give the answer model a bounded number of recent turns so it
   can respond coherently.

Simply appending the entire transcript to every prompt is not a controlled
design. It increases token cost, can retrieve irrelevant material, and makes
the answer difficult to reproduce.

### Recommended implementation

1. Add `conversations` and `conversation_messages` tables.
2. Give each browser session a conversation identifier.
3. Save user and assistant messages with timestamps and response provenance.
4. Start with a configurable three-turn window.
5. Rewrite a follow-up into a standalone retrieval query using the bounded
   history.
6. Save the original question, rewritten query, exact history window, rewriting
   model/version, and retrieved evidence.
7. Add **New conversation** and **Clear conversation** controls.

NVIDIA's multi-turn documentation describes the same essential comparison:
simple history concatenation is cheaper, while query rewriting adds a model
call but can improve retrieval for contextual questions. Both should be tested
rather than assuming one is always preferable.

### Evaluation design

Build short reviewed conversations such as:

```text
Turn 1: When does Fall 2026 registration begin?
Turn 2: What about spring?
Turn 3: Which one happens first?
```

Compare:

1. no history;
2. concatenated recent user questions;
3. model-rewritten standalone queries.

Measure follow-up answer accuracy, expected-source retrieval, query-rewrite
accuracy, faithfulness, added latency, added token cost, and context leakage.
Controlled single-turn evaluation must remain available so historical results
do not silently change when conversation support is introduced.

### Acceptance criteria

- A follow-up resolves the intended subject using only its own conversation.
- Starting a new conversation removes that context.
- The UI shows when history influenced retrieval.
- The rewritten query and history window appear in exports/provenance.
- A single-turn request behaves exactly like the existing baseline.

## Enhancement 3: Multi-User RAG

### Research goal

Allow concurrent users to interact without exposing one person's conversation,
settings, uploads, or private evidence to another.

Multi-user support has two separate concerns:

- **Concurrency:** can the service handle overlapping retrieval and model calls?
- **Isolation:** does every read and write apply to the correct user, role, and
  conversation?

Passing a concurrency test does not prove isolation.

### Staged design

#### Stage 1: Anonymous session isolation

- Issue a server-managed session identifier in a secure, HTTP-only cookie.
- Scope conversations and messages to that session.
- Keep the bundled knowledge base shared and read-only for ordinary users.
- Keep document administration and research-run mutation in an administrator
  role.

This stage is enough to test independent browser conversations without adding
a full account system.

#### Stage 2: Authenticated roles, only for deployment

- Add users and roles such as viewer, researcher, and administrator.
- Apply ownership checks in every API query, not only in the browser.
- Add CSRF protection to state-changing browser requests.
- Rate-limit provider-backed generation and evaluation operations.
- Define whether uploaded collections are shared, private, or explicitly
  assigned to a group.

#### Stage 3: Concurrent work management

- Move slow ingestion and large evaluation jobs to a bounded background queue.
- Make document replacement and vector cleanup idempotent.
- Prevent two administrators from replacing the same source simultaneously.
- Record job owner, status, progress, retry count, and error.
- Monitor request latency, queue time, provider rate limits, and failures.

### Evaluation design

- Open two independent browser sessions and verify that neither can read the
  other's history.
- Ask different follow-ups in both sessions and verify retrieval isolation.
- Run simultaneous read-only source previews and record p50/p95 latency and
  error rate.
- Attempt simultaneous replacement of one controlled source and verify one
  consistent final version with no stale vectors.
- Verify that ordinary users cannot upload, delete, evaluate, or export data
  outside their role.

### Acceptance criteria

- No cross-session conversation leakage.
- Every state-changing API performs server-side authorization.
- Shared knowledge-base rules are explicit in the interface.
- Concurrent jobs cannot create duplicate documents, chunks, or vectors.
- Load-test evidence states the tested concurrency and hardware instead of
  claiming unlimited scale.

## Enhancement 4: Agentic RAG

### Research goal

Determine whether bounded planning and retrieval retries improve difficult,
multi-hop questions enough to justify their additional model calls, latency,
and operational complexity.

Agentic RAG should be an optional condition beside the standard pipeline—not a
replacement for every question. Direct factual questions often need only one
retrieval pass.

### Proposed bounded workflow

```text
question
  -> complexity/router check
      -> simple: use the existing RAG pipeline
      -> complex: create 1-3 focused subquestions
                    -> retrieve evidence for each
                    -> check evidence sufficiency
                    -> retry at most once when evidence is missing
                    -> synthesize with citations
                    -> optional groundedness verification
```

Every step should be saved: plan, subqueries, retrieved chunks, retry reason,
model usage, latency, and final evidence. Maximum steps and model calls must be
enforced. Arbitrary web browsing, code execution, or external side effects
should remain disabled unless a separately reviewed use case requires them.

NVIDIA's current Agentic RAG design similarly targets ambiguous, multi-document,
and multi-hop questions and warns that the agentic path costs more latency and
LLM calls than the standard chain.

### Evaluation design

Create reviewed cases that require:

- combining facts from two documents;
- resolving an ambiguous initial query;
- comparing several dated policies;
- finding a value in a table and relating it to explanatory text;
- refusing when one required fact is absent.

Compare the standard and agentic paths on answer completeness, expected-source
coverage, faithfulness, retries, latency, call count, cost, and human review.
Also include simple questions to detect needless agent overhead.

### Acceptance criteria

- The router leaves straightforward questions on the standard path.
- Plans and retries are bounded and inspectable.
- The agent never treats its own intermediate answer as source evidence.
- Citations resolve to retrieved knowledge-base elements.
- Any quality improvement is reported beside the added latency and cost.

## Recommended Research Order

| Priority | Work | Reason |
| ---: | --- | --- |
| 1 | Preserve and export the completed baseline | All later comparisons require a frozen reference condition |
| 2 | Multimodal ingestion proof using one image-heavy PDF | Directly addresses the identified document-processing gap |
| 3 | Conversation/session schema and a three-turn evaluation set | Creates measurable follow-up behavior and the foundation for user isolation |
| 4 | Anonymous multi-session isolation and concurrency tests | Separates users before adding full authentication complexity |
| 5 | Bounded agentic RAG experiment | Highest complexity and cost; useful only after retrieval evidence is reliable |

These are research priorities, not commitments for the completed course. A
small, measured proof is preferable to claiming broad production support.

## Cross-Cutting Evaluation Matrix

| Capability | Baseline | Experimental condition | Primary evidence |
| --- | --- | --- | --- |
| Multimodal | Text-layer chunks only | Vision summaries and raw visual evidence; optionally VLM embeddings | Figure/page retrieval, numeric/fact accuracy, visual faithfulness, cost |
| Conversation | Independent questions | Three-turn history with concatenation or query rewriting | Follow-up retrieval/answer accuracy, leakage, latency, tokens |
| Multi-user | Shared local workspace | Session- or user-scoped conversations and roles | Isolation, authorization, concurrency, p95 latency, error rate |
| Agentic | One retrieval and generation pass | Bounded plan, subqueries, retry, synthesis | Multi-hop completeness, sources, calls, latency, cost |

The existing evaluator portfolio still applies, but no single metric covers all
of these concerns. Quality metrics must be combined with provenance, human
review, security/isolation tests, and operational measurements.

## README-Based Demonstration Plan

No slide deck is required for this roadmap. A future walkthrough can use the
repository README and the live application in this order:

1. State the evaluation research question.
2. Show the completed text-RAG and evaluation architecture.
3. Upload a controlled DOCX or PDF containing ordinary text and a picture.
4. Show that the source file retains the picture while only its ordinary text
   is currently indexed.
5. Replace it with a same-named version and show that the whole source and its
   chunks are replaced safely.
6. Ask a source-backed question and inspect retrieved evidence.
7. Open Gold Standard, Evaluation, and Compare Runs to explain the evaluator
   portfolio and bounded findings.
8. Close with the four extension experiments and their acceptance criteria.

The presentation should say “planned” or “research condition” for every
capability in this document. It should not imply that the final submitted
baseline already processes images, remembers chat, isolates users, or runs an
agent.

## References

Project sources:

- [Hands-on Guide to Multimodal RAG Systems](Hands_On_Guide_to_Multimodal_RAG_Systems.pdf)
- [Final project scope](final-project-scope.md)
- [Reference-repository comparison](reference-repository-comparison.md)
- [Evaluation strategy](evaluation-strategy.md)

Official platform references reviewed for this roadmap:

- [NVIDIA RAG Blueprint: Multimodal Retriever](https://docs.nvidia.com/rag/latest/multimodal-retriever.html)
- [NVIDIA RAG Blueprint: VLM Generation](https://docs.nvidia.com/rag/latest/vlm.html)
- [NVIDIA RAG Blueprint: Multi-Turn Conversation Support](https://docs.nvidia.com/rag/latest/multiturn.html)
- [NVIDIA RAG Blueprint: Agentic RAG](https://docs.nvidia.com/rag/latest/agentic-rag.html)
- [NVIDIA RAG Blueprint: Evaluation](https://docs.nvidia.com/rag/latest/evaluate.html)
- [Gemini API: Document Understanding](https://ai.google.dev/gemini-api/docs/document-processing)
- [Gemini API: Image Understanding](https://ai.google.dev/gemini-api/docs/image-understanding)

These external systems are research references, not dependencies of the
submitted application.
