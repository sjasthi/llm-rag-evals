# LLM RAG Evaluations Web Application

> **Status:** Final submission requirements baseline. The implemented boundary
> is recorded in [Final Project Scope](docs/final-project-scope.md), and the
> completed study is reported in [Final Study Report](docs/final-study-report.md).

## 1. Project Overview

The goal of this project is to build a web-based research application for evaluating Retrieval-Augmented Generation (RAG) approaches using Metrostate documents as the example knowledge base. The application is the experimental instrument; the final contribution includes what the experiments teach about metric usefulness, failure modes, and the effects of document-collection size and composition.

The system will allow users to upload or manage Metrostate-related documents, ask questions against those documents, generate AI-assisted responses using approved LLM providers such as OpenAI/ChatGPT, Gemini, or Claude, and compare different RAG evaluation approaches. The project is intended to help business users, managers, and developers understand which RAG approach or evaluation framework is most useful for informed decision making.

This project will use the following reference repositories:

* Reference Repo 1: https://github.com/sjasthi/ragworks
* Reference Repo 2: https://github.com/sjasthi/student-compass
* Main Project Repo: https://github.com/sjasthi/llm-rag-evals

The project will port or adapt useful ideas from the reference repositories into the required course technology stack.

---

## 2. Technology Stack

The application must use the following technology stack:

### Front End

* HTML
* CSS
* JavaScript
* jQuery
* Bootstrap

### Server

* PHP

### Backend / Database

* MySQL
* ChromaDB for vector storage and retrieval

### AI / LLM Integration

* Approved LLM providers such as OpenAI/ChatGPT, Gemini, or Claude
* Embedding model for document search
* LLM model for answer generation
* Optional LLM-based evaluation for response scoring

---

## 3. Target Users

### 3.1 Business Users / Managers

Business users and managers will use the application to compare different RAG evaluation approaches and make informed decisions about which approach is most useful.

They should be able to:

* View evaluation results
* Compare RAG performance across different settings
* Understand trade-offs between evaluation frameworks
* Review which approach gives better accuracy, relevance, and faithfulness
* Use reports or dashboard results to support decision making

### 3.2 Developers

Developers will use the application as a starting point for building and testing RAG systems in the required technology stack.

They should be able to:

* Understand the application structure
* Review how documents are processed
* See how questions and responses are stored
* Review how evaluation scores are calculated
* Extend the system with additional evaluation methods or model providers

### 3.3 Admin Users

Admin users will manage the document knowledge base and evaluation test data.

They should be able to:

* Upload Metrostate documents
* View uploaded documents
* Delete or replace documents
* Manage test questions
* Manage expected answers
* Run evaluation tests
* View evaluation history

### 3.4 General Users

General users will ask questions against the Metrostate document knowledge base.

They should be able to:

* Enter a question
* Receive an AI-generated answer
* View retrieved source documents or source chunks
* See basic evaluation feedback when available

---

## 4. Main Project Goal

The main goal is to prove and compare different RAG evaluation frameworks using Metrostate documents.

The application should answer questions such as:

* Did the RAG system retrieve the correct Metrostate document sections?
* Did the generated answer correctly answer the user’s question?
* Was the answer faithful to the retrieved context?
* Did the answer include unsupported or hallucinated information?
* Which evaluation method gives the most useful results for a specific business, development, or research purpose?
* Where do evaluation metrics agree or disagree on the same response?
* Which retrieval or generation failures does each metric detect or miss?
* How does document-collection size or composition affect retrieval and evaluation results?
* Which RAG configuration produces better responses?

The project shall not assume that one evaluation metric or configuration is universally best. Conclusions shall identify the corpus, questions, settings, metrics, and limitations behind each finding.

---

## 5. Metrostate Document Requirement

The project must use Metrostate documents as the RAG example dataset.

Examples of possible Metrostate documents include:

* Course syllabi
* Program requirements
* Academic policies
* Student handbook pages
* Registration information
* Graduation requirements
* Financial aid information
* Advising documents
* Department documents
* Public Metrostate web pages or PDFs

The application should process these documents so users can ask questions and receive answers grounded in the document content.

---

## 6. Functional Requirements

## 6.1 Document Management

The system shall allow admin users to upload Metrostate documents.

The system shall support common document formats such as:

* TXT
* Text-based PDF
* DOCX
* HTML or copied webpage text, if supported

The system shall store document metadata in MySQL, including:

* Document ID
* Document title
* File name
* Upload date
* Uploaded by
* Document type
* Status

The system shall store the original display filename separately from the
server-controlled runtime storage path.

The system shall allow users to view and organize all active indexed documents
without database or command-line access. The browser shall provide search,
category/type filters, sorting, category grouping, and live document/chunk counts.

The system shall allow users to delete or replace any active indexed document
and to clear the full active index with explicit confirmation. The Documents
page shall also restore/re-index the bundled starting collection without
terminal access while preserving separately uploaded documents.

Current implementation adds live document/category/chunk counts, same-name
replacement with an explicit Replace/Cancel conflict prompt, and confirmed
deletion for every active source. Replacement is
staged as add-new then delete-old so a failed new ingestion does not discard the
working version. Deletion removes the MySQL document/chunks and matching
ChromaDB vectors and verifies that no selected-source vectors remain; uploaded
files are also removed. Bundled seed files remain on disk as recovery material
after they are removed from the active index, and the browser's **Restore
bundled sources** action re-ingests that collection with current index settings.
Add, delete, and replace operations embed or remove only the affected source;
unchanged documents are not re-embedded.

The system shall prepare uploaded documents for RAG processing.

The browser upload workflow shall validate extension, MIME type, file size, upload status, and parser output. Uploaded filenames shall not be trusted as server storage names. The system shall reject encrypted, unreadable, empty, or unsupported files with a clear error and record ingestion failures for diagnosis.

TXT, PDF, and DOCX inputs shall be converted into normalized text and then use the same chunking, metadata, MySQL, and ChromaDB ingestion path. Scanned-image PDF OCR is optional unless separately required.

---

## 6.2 Document Chunking

The system shall split uploaded documents into smaller text chunks.

Each chunk shall be associated with its original document.

Each chunk shall store useful metadata, such as:

* Chunk ID
* Document ID
* Chunk text
* Chunk order
* Page number or section, if available
* Created date

The system should support configurable chunking settings, such as:

* Chunk size
* Chunk overlap

---

## 6.3 Embeddings and Retrieval

The system shall generate embeddings for document chunks using an approved embedding provider.

The system shall store chunk information and retrieval metadata.

The system shall retrieve relevant chunks based on the user’s question.

The system should support configurable retrieval settings, such as:

* Top-k value
* Similarity threshold
* Embedding model
* Retrieval method

The system shall return the most relevant document chunks to the answer generation step.

FP8 implementation status: `chroma_vector` uses the persisted local Chroma
collection, while `mysql_keyword` uses an authoritative MySQL FULLTEXT index
with lexical reranking and a database fallback for short/date-heavy queries.
Both paths support top-k and reproducible category subsets and save the actual
retrieval method with each response/run. The older filesystem keyword search
remains only as a command-line troubleshooting baseline.

---

## 6.4 Question Answering

The system shall provide a user interface where users can ask questions about Metrostate documents.

The system shall send the user question and retrieved context to an LLM provider.

The system shall generate an answer based on the retrieved Metrostate document context.

The system shall display the answer to the user.

The system shall display the source documents or source chunks used to generate the answer.

The system should avoid answering questions that are not supported by the retrieved Metrostate documents.

---

## 6.5 Gold Standard Test Set

Final dataset status: version 2.0 contains 50 reviewed questions with expected
evidence, accepted answer variants, required facts, category, difficulty,
answerability, reviewer notes, and versioned membership. The original
25-question v1.0 file remains available for historical-run reproducibility.
Provider-free tests verify that every answerable v2.0 evidence excerpt occurs
in its cited bundled source. The browser supports filtering and review-state
management before controlled runs.

The system shall allow admin users to create and manage evaluation test questions.

Each test question should include:

* Question ID
* Question text
* Expected answer
* Related source document, if known
* Category or topic
* Difficulty level, if needed

The project shall begin with at least 25 manually reviewed Metrostate-related test questions. Twenty-five is a starting target, not a fixed ratio between questions and documents. Additional questions shall be added when they improve category, document, difficulty, answerability, or failure-mode coverage.

The initial test set shall:

* Cover all current document categories
* Include answerable and deliberately unanswerable questions
* Include factual dates, amounts, requirements, and policy questions
* Store a verified expected answer and expected source for answerable questions
* Store answerability, category, and difficulty metadata
* Avoid redundant questions unless repetition supports a documented experiment

The test set will be used to compare RAG performance across different settings and evaluation methods.

---

## 6.6 RAG Evaluation Methods

FP7 implements the evaluator foundation and eight local/supporting evaluators:
exact/contains, required-fact coverage, token F1, ROUGE-L, embedding semantic
similarity, BERTScore, expected-source accuracy, and refusal correctness. Each
result is attached to one saved response and stores its raw/normalized score,
explanation, structured details, runtime, cost placeholder, status, and error.

FP8 implementation status (July 14, 2026): five advanced definitions are live:
a versioned structured LLM-as-judge rubric plus RAGAS Faithfulness, Response
Relevancy, Context Precision, and Context Recall. The system preserves immutable
attempts, applicability/skips/failures, model and prompt configuration, raw
provider output, usage, runtime, and estimated cost. A guarded runner requires
dry-run review, explicit paid-call authorization, and application/cost limits.
The bounded Response 19 proof now has a completed LLM judge plus all four RAGAS
metrics. Earlier adapter, dependency, and free-tier quota failures remain in the
immutable attempt history while the latest canonical results are completed.

The system shall support multiple evaluation methods for comparing actual generated answers against expected answers and retrieved context.

The same stored responses should be scored by multiple methods so metric results can be compared directly. The system shall preserve per-question scores and should identify cases where metrics disagree. Metric documentation shall explain what each method measures, its intended use, and its limitations.

The project shall research representative evaluator types across lexical,
token-overlap, semantic, contextual-embedding, source/retrieval,
LLM-as-judge, and RAGAS method families. The professor-provided reference's
eight options are broad approaches, not eight required advanced models. RAGAS
shall be treated as one framework within the comparison rather than the
complete evaluation strategy. Every applicable evaluator shall operate on the
same stored response and retrieved contexts for a controlled comparison.

For each evaluator, the system or final report shall record its required
inputs, retrieval/generation dimension, raw and normalized result where
applicable, configuration/version, deterministic or judged classification,
runtime, estimated cost, error status, strengths, limitations, and recommended
use case. Human review shall be used to calibrate and interpret automated
scores. See `docs/evaluation-strategy.md` for the working evaluator set and
experiment protocol.

Metrics shall not be described as voting on or collectively generating an
answer. The RAG system generates and stores one answer and context set; each
metric independently measures a selected property of that evidence. The system
shall present a dimensional metric profile rather than an unexplained average
of unlike measurements.

The browser shall label which evaluators require gold-standard annotations.
The eight local metrics, LLM judge, RAGAS Context Precision, and RAGAS Context
Recall use at least one reviewed expected answer/source/fact/evidence or
answerability field. RAGAS Faithfulness and Response Relevancy do not require a
gold answer. All 13 metrics operate after retrieval/generation and none is used
to find or generate the answer.

The browser shall expose a bounded New test run workflow for reviewed questions
and a separate Score saved answers workflow for every saved test. Both shall
preflight calls before execution. New tests shall accept an approved model,
retrieval method, top-k, temperature, top-p, exact reviewed-question selection, and an optional
source-category subset. The browser shall offer quick-test,
controlled-baseline, and baseline-comparison modes. Comparison mode shall reuse
the baseline's exact ordered question set, copy and lock unchanged settings, require
exactly one declared change, and save the experiment/baseline/corpus
relationship. The server shall reject comparisons that actually change zero
or multiple supported settings or a different question set. The Evaluation view shall summarize whether
reviewed questions, a controlled baseline, matched comparison results, human
calibration, and report exports are available. Saved-answer
scoring shall distinguish the provider-free local eight from the five
model-backed methods, target the exact selected answer for all-13 scoring, reuse
completed or not-applicable active-version results unless replacement is
requested, leave failed results eligible for retry, and enforce
response/application/cost limits. Primary labels shall use user-facing question
numbers rather than database response IDs. Each saved answer shall expose a
direct Evaluate action that selects it as the exact all-13 target before
preflight. Each metric shall display the selected answer's score, its current
test mean, and its mean across all completed stored tests. A cumulative
13-metric score remains a potential research
target only; it shall not be displayed until weighting, missing-value behavior,
and human calibration are justified.

Each displayed score shall identify its comparison target, plain-language
calculation, scale, direction, threshold, threshold provenance, interpretation,
and primary limitation. Project-defined descriptive cutoffs shall be labeled as
review thresholds and shall not be presented as proof of correctness. The
application shall distinguish completed, not-applicable/skipped, failed, and
numeric-zero results.

FP8 adds a versioned LLM-as-judge rubric and RAGAS Faithfulness, Response
Relevancy, Context Precision, and Context Recall. The system stores exact
judge/model/prompt/library versions, applicability, raw output, token/API usage,
runtime, estimated cost, and errors. Repeated judge attempts shall be preserved
for variability analysis rather than overwritten. Human response review shall
be stored separately from the review state of dataset questions. These
requirements are implemented. The final study includes seven responses with
single-reviewer decisions as a descriptive calibration sample: six
acceptable and one needs revision. It is not inter-rater evidence.

Possible evaluation methods include:

### Exact Match / String Match

Compares the generated answer directly with the expected answer.

### Token Overlap Metrics

Compares word or phrase overlap between the generated answer and the expected answer.

Examples:

* BLEU
* ROUGE
* METEOR

### Semantic Similarity

Compares the generated answer and expected answer using embeddings or semantic similarity.

### BERTScore

Uses contextual token embeddings to calculate precision, recall, and F1 between
the generated and expected answers. It provides a heavier local semantic
comparison that remains distinct from factual grounding.

### Expected-Source Accuracy

Checks whether the manually verified source document appears in the ranked
retrieval results and records its rank. This directly evaluates a project-level
retrieval requirement but does not by itself prove that the retrieved excerpt
contains sufficient evidence.

### LLM-as-Judge

Uses an LLM to score the generated answer based on criteria such as accuracy, completeness, relevance, and faithfulness.

### RAGAS-style Metrics

Uses RAG evaluation metrics such as:

* Faithfulness
* Answer relevancy
* Context precision
* Context recall
* Answer correctness

### Human Evaluation

Allows manual review or scoring of generated answers.

---

## 6.7 Evaluation Criteria

The system should evaluate RAG responses using criteria such as:

### Answer Accuracy

Measures whether the generated answer is factually correct.

### Answer Relevance

Measures whether the generated answer directly responds to the user’s question.

### Faithfulness

Measures whether the answer is supported by the retrieved document chunks.

### Context Precision

Measures whether the retrieved chunks are relevant to the question.

### Context Recall

Measures whether the retrieved chunks contain the information needed to answer the question.

### Source Accuracy

Measures whether the answer cites or uses the correct Metrostate source document.

### Hallucination Detection

Measures whether the generated answer includes information not supported by the retrieved context.

---

## 6.8 Evaluation Dashboard

The system shall include a dashboard for viewing evaluation results.

FP9/FP10 implementation status (updated July 21, 2026): the user-facing
**Evaluation** view creates bounded tests, scores exact saved answers, and
provides response inspection, score contracts, attempt variability,
applicability/failure states, exact contexts, expected-source cues,
disagreement prompts, and versioned response review. Each metric card shows the
selected answer's value beside that evaluator's cumulative average over
completed tests. The secondary **Compare Runs** view provides interpretation
rules, configuration/coverage evidence, run-scoped descriptive summaries,
same-question/evaluator baseline deltas, and the live 13-evaluator catalog. It
does not calculate an aggregate across unrelated metrics or a cross-run
leaderboard from unmatched rows. Matched automated runs now exist; calibrated
interpretation includes seven final-study human reviews. These single-reviewer
overall decisions support descriptive calibration, not inter-rater or
dimension-level agreement claims.

The dashboard should show:

* Total number of test questions
* Executed responses compared with dataset size
* Local-metric, LLM-judge, and RAGAS coverage, with Human review shown
  separately as supporting evidence
* Per-metric summaries only among compatible results
* Above/below review-threshold results with threshold provenance
* Not-applicable/skipped and failed counts separate from numeric scores
* Evaluation method used
* Model used
* Retrieval settings used
* Dataset version and corpus variant
* Runtime and estimated cost when available

The dashboard shall allow response-level inspection of the question, generated
answer, reviewed reference, ordered retrieved contexts, score basis,
calculation details, threshold interpretation, evaluator version, and
limitation. It shall provide purpose-based guidance for choosing metrics and
shall expose disagreement cases instead of ranking evaluators by one universal
score.

The dashboard should allow comparison between different RAG configurations.

Example comparison settings include:

* Different chunk sizes
* Different chunk overlap values
* Different top-k retrieval values
* Different LLM models
* Different embedding models
* Different evaluation frameworks

---

## 6.9 Reports

The system should generate summary reports for business users and managers.

Reports should explain:

* Which RAG approach performed better for the tested corpus and settings
* Which evaluation framework was useful for each specific purpose
* Where evaluation metrics agreed or disagreed
* Which problems each metric detected or missed
* Which settings improved answer quality
* Which settings caused weaker results
* Common failure cases
* What was learned from document-collection size or composition experiments
* Which conclusions cannot be generalized to enterprise-scale collections
* Recommendations for future development

Reports may include tables, charts, or summary text.

---

## 6.10 User Interface Requirements

The front end shall be built using HTML, CSS, JavaScript, jQuery, and Bootstrap.

The implemented primary navigation shall include:

* Overview
* Chat
* Documents
* Gold Standard
* Evaluation

Compare Runs shall remain available as a secondary analysis view reached from
Evaluation. Upload/list actions are consolidated under Documents, and answer
inspection plus metric results are consolidated under Evaluation so a
frontend-only user does not have to infer the relationship between separate
technical pages.

The interface should be simple, clean, and easy to use.

The header shall confirm application-data readiness instead of claiming the
workspace is ready before its services respond. End-user failure messages shall
recommend retrying or contacting the application administrator and shall not
instruct ordinary users to configure MySQL, environment files, Python, or the
codebase.

The Evaluation view shall avoid unexplained empty panels, identify partial tests
clearly (for example, `3 of 50 questions answered`), and group evaluator cards
as Local metrics, LLM judge, and RAGAS, with Human review identified as
supporting evidence. Gold Standard review controls shall explicitly explain
that they verify the quality of the question, reference answer, and evidence;
separate response-review controls shall support sampled human calibration with
the reference and source evidence visible.

Bootstrap should be used for layout, forms, buttons, tables, cards, and responsive design.

---

## 7. Database Requirements

The MySQL database should store the main application data.

ChromaDB should store RAG vector data, including document chunks, embeddings,
source metadata, and retrieval collections.

Possible tables include:

### users

Stores user account information if login is implemented.

### documents

Stores uploaded document metadata.

### document_chunks

Stores chunked document text and metadata.

### questions

Stores user questions and evaluation test questions.

### expected_answers

Stores expected answers for test questions.

### rag_responses

Stores generated answers from the RAG system.

### retrieved_contexts

Stores retrieved chunks used for each question.

### evaluation_runs

Stores each evaluation run.

### evaluation_scores

Stores scores from different evaluation methods.

### model_settings

Stores model, embedding, chunking, and retrieval settings.

---

## 8. Non-Functional Requirements

## 8.1 Usability

The application should be easy for business users, managers, developers, and students to understand.

## 8.2 Maintainability

The code should be organized so future developers can extend the project.

## 8.3 Modularity

The RAG pipeline should be separated into clear steps:

* Document upload
* Chunking
* Embedding
* Retrieval
* Answer generation
* Evaluation
* Reporting

## 8.4 Security

API keys should not be hardcoded in public files.

Sensitive configuration values should be stored in a separate configuration file or environment file.

User input should be validated before being stored or processed.

Database queries should use prepared statements to reduce SQL injection risk.

## 8.5 Performance

The application should handle a reasonable number of Metrostate documents and test questions on a local development machine.

The research shall recognize that organizations may search hundreds to millions of documents. The local project is not required to reproduce enterprise scale, but it shall support a controlled comparison between document subsets or differently composed collections and report how retrieval quality, answer quality, latency, and metric behavior change.

The system should avoid unnecessary repeated API calls when possible.

The system should store results so previous evaluations can be reviewed without rerunning every test.

## 8.6 Cost Awareness

The system should track or estimate API usage when using paid model providers.

The system should allow smaller test runs to reduce unnecessary API cost.

---

## 9. Success Criteria

The project will be considered successful if:

* The application runs using the required technology stack.
* Metrostate documents can be used as the RAG knowledge base.
* Users can ask questions and receive generated answers.
* Retrieved sources or chunks are shown with the answer.
* The system can run evaluation tests against expected answers.
* The system compares at least two RAG evaluation methods.
* The system stores evaluation results in MySQL.
* The final 50-question reviewed set covers the current categories and answerability cases.
* TXT, text-based PDF, and DOCX documents can enter the common ingestion pipeline through the browser workflow.
* The dashboard or report explains metric usefulness, metric disagreement, failure cases, and configuration results.
* Every displayed evaluator score explains what it is based on, how it was
  calculated, what its threshold means, and what it cannot prove.
* Advanced evaluator attempts, versions, applicability, usage, runtime, cost,
  and failures are auditable without regenerating the saved RAG answer.
* A controlled collection-size or collection-composition experiment is reproducible and its limits are documented.
* The application provides a useful starting point for future developers.

---

## 10. Possible Evaluation Experiments

The project may compare RAG performance using experiments such as:

### Experiment 1: Different Top-K Values

Compare response quality when retrieving different numbers of chunks.

Example:

* Top-k = 3
* Top-k = 5
* Top-k = 8

### Experiment 2: Different Chunk Sizes

Compare response quality using different chunk sizes.

Example:

* Small chunks
* Medium chunks
* Large chunks

### Experiment 3: Different Evaluation Methods

Compare how different evaluation frameworks score the same responses.

Example:

* Exact match
* Semantic similarity
* LLM-as-judge
* RAGAS-style metrics

### Experiment 4: Different Models

Compare results using different LLM providers or models.

Example:

* OpenAI/ChatGPT model
* Gemini model
* Claude model
* Other supported model provider
* Local model, if supported

### Experiment 5: Document Collection Size and Composition

Run the same applicable questions against reproducible document collections, such as a focused subset and the full current collection. If additional approved documents are available, include a larger collection or add similar distractor documents.

Compare:

* Expected-source hit rate and rank
* Irrelevant-context rate
* Answer correctness and faithfulness
* Refusal correctness
* Latency
* Agreement and disagreement between evaluation metrics

The results shall be presented as evidence from the tested collections, not as proof of behavior at millions-of-documents scale.

---

## 11. Project Scope

## 11.1 In Scope

The following items are in scope:

* Web-based application
* Metrostate document upload and management
* TXT, text-based PDF, and DOCX parsing
* RAG question-answering system
* Approved LLM provider integration
* MySQL storage
* RAG response evaluation
* Evaluation dashboard
* Comparison of RAG approaches
* Reports for business users and developers
* A final versioned set of 50 reviewed evaluation questions
* Metric-usefulness and metric-disagreement analysis
* Controlled document-collection size or composition experiments

## 11.2 Out of Scope

The following items are out of scope for the initial version:

* Training a custom large language model
* Building a production-level enterprise chatbot
* Supporting every possible document type
* Real-time multi-user collaboration
* Full authentication system, unless required
* Production deployment at enterprise scale
* Guaranteeing perfect answer accuracy

---

## 12. Submission Decisions and Post-Capstone Questions

Resolved implementation decisions:

* Use representative evaluator families rather than eight advanced models.
* Integrate a structured LLM judge and four RAGAS dimensions directly while
  preserving the FP7 baselines.
* Use tables/cards and source-level drill-down first; add charts only when
  comparable complete runs make a relationship clearer.
* Text-based PDFs are supported; OCR remains outside the current scope.
* Rename the reviewed answer-key workspace to `Gold Standard` and consolidate
  saved test creation, answer inspection, and metric results under `Evaluation`.
* Treat the browser as the user's complete operating surface: model selection,
  source administration, evaluator preflight/execution, and run inspection do
  not require direct code or database access.
* Keep ordinary Chat usable with recommended defaults while exposing approved
  model/retrieval/generation options for future deployments and research use.
* Determine recommended settings through controlled gold-standard experiments,
  changing one variable at a time and comparing the same metrics/questions,
  rather than asking ordinary users to guess the best values.
* Implement that protocol as a guided browser baseline/comparison launcher;
  users shall not need to know CLI flags, run IDs, database columns, or
  environment-file settings to create a valid pair.
* Treat chunk size, overlap, and embedding model as index-variant settings that
  require re-chunking/re-embedding; do not present them as safe per-answer
  controls against one shared active index.
* Preserve the guarded preflight before all-13 execution even when the user
  starts from a per-answer Evaluate button, because up to five methods may call
  an external evaluator provider.
* Export each saved run as portable JSON or long-form CSV so configuration,
  answers, contexts, scores, attempts, human reviews, and valid matched
  comparisons can be used in the final report without direct database access.

The submission does not depend on the questions below. They are retained as
possible post-capstone product or research decisions:

1. Should the project port more from RagWorks or Student Compass?
2. Should the final app require user login, or can it be a simple admin/user interface without authentication?
3. Does the professor require a specific number of complete advanced-evaluator
   cases, repeated judge attempts, or independent human reviewers?
4. What weighting and human-calibration evidence would be required before an
   optional multidimensional composite score could be shown responsibly?
5. Should full parameter-grid execution use a background job queue for the
   final submission, or is the current bounded browser execution sufficient?

---

## 13. Initial Minimum Viable Product

The initial MVP should include:

1. Upload TXT, text-based PDF, and DOCX Metrostate documents
2. Store document metadata in MySQL
3. Chunk document text
4. Generate embeddings using the configured local or provider model
5. Retrieve relevant chunks for a question
6. Generate an answer using an LLM API
7. Display answer and sources
8. Store question, answer, context, and settings
9. Run the reviewed evaluation set with multiple metrics
10. Display per-question and aggregate results in a table or dashboard

---

## 14. Future Enhancements

The final submission already implements the human evaluation workflow,
exportable reports, controlled run comparisons, and purpose-specific evaluator
recommendations that appeared in the initial enhancement list.

Post-capstone research candidates are now:

* Multimodal extraction and retrieval for pictures, charts, tables, diagrams,
  and scanned pages
* Bounded conversation history with query rewriting for follow-up questions
* Session/user isolation, roles, and concurrency testing for multi-user RAG
* Optional bounded agentic RAG for ambiguous or multi-hop questions
* Background jobs for larger ingestion and evaluation workloads
* More model providers when they support a controlled research comparison

These are plans rather than implemented final-project requirements. Architecture,
experiments, risks, and acceptance criteria are defined in the
[post-capstone RAG research roadmap](docs/post-capstone-roadmap.md).
