# RAG Evaluation Research Plan

## Research Framing

This capstone is both a working web application and a research project. The web
application is the experimental instrument: it ingests documents, retrieves
evidence, generates grounded answers, runs repeatable evaluations, and stores
the results. The primary final deliverable is the knowledge produced by those
experiments.

The project should explain what different RAG evaluation metrics reveal, where
each metric is useful, where it can be misleading, and how document-collection
size and composition affect the interpretation of results. It should not assume
that one metric or one RAG configuration is universally best.

## Primary Research Questions

1. Which metrics are useful for detecting retrieval failures, incorrect
   answers, unsupported claims, and incomplete answers?
2. When do automated metrics agree or disagree on the same response?
3. Which metrics are most useful to developers, managers, and human reviewers?
4. How do retrieval settings such as top-k, chunk size, and retrieval method
   affect measured answer quality?
5. How does the size and composition of the indexed document collection affect
   retrieval difficulty and metric results?
6. What combination of metrics gives a defensible overall evaluation of this
   Metro State RAG system?

## Research Outputs

The final project should produce:

- a reproducible Metro State evaluation dataset;
- stored RAG responses and the exact contexts used for each response;
- results from multiple evaluation metrics applied to the same responses;
- comparisons showing where metrics agree, disagree, or fail to capture an
  important problem;
- a failure analysis separating retrieval failures from generation failures;
- a small corpus-size or corpus-composition experiment;
- recommendations explaining which metrics are useful for particular purposes;
- limitations and follow-up questions for larger organizational document sets.

## Evaluation Dataset Design

Begin with at least 25 manually reviewed questions. Twenty-five is a practical
starting point, not a universal ratio between questions and documents. The
number of questions should be justified by coverage and research usefulness.

The initial dataset should:

- cover all eight current Metro State document categories;
- include factual dates, amounts, requirements, and policy questions;
- include questions that require distinguishing similar documents or terms;
- include answerable and deliberately unanswerable questions;
- store a verified expected answer and expected source document;
- record category, difficulty, and answerability;
- avoid multiple questions that test the same fact without a research reason.

For the current 27-document collection, a starting distribution of 25-35
questions is appropriate. More questions can be added when they improve topic,
document, difficulty, or failure-mode coverage. A much larger document corpus
does not automatically require the same proportional increase in questions;
the evaluation set should instead sample the behaviors and risks that matter.

## Metrics and Their Specific Uses

Professor-provided evaluation reference:

- [RAG Chatbot Accuracy Evaluation: Options & Trade-offs](https://github.com/sjasthi/ics499/blob/main/presentations/rag_chatbot_evaluations.md)

This reference separates retrieval quality from generation quality and compares
exact/string matching, BLEU/ROUGE/METEOR, semantic similarity, BERTScore,
LLM-as-judge, RAGAS, human evaluation, and production A/B testing. FP7 should
implement approximately ten evaluator/metric types against the same stored
responses, record cost/speed/determinism trade-offs, and use human-reviewed
expected answers/sources to interpret metric agreement and disagreement.

| Metric | What it helps assess | Main limitation |
| --- | --- | --- |
| Normalized exact/contains match | Whether a required fact, date, or phrase appears | Penalizes correct paraphrases and can reward unsupported keyword copying |
| Semantic answer similarity | Whether generated and expected answers have similar meaning | Similar meaning does not prove factual correctness or grounding |
| Expected-source accuracy | Whether retrieval includes the expected document | Does not prove the retrieved excerpt contains enough evidence |
| Context precision | How much retrieved context is relevant | Requires relevance labels or a judge and may miss necessary supporting context |
| Context recall | Whether retrieval found the evidence needed to answer | Requires known supporting evidence and can be expensive to label |
| Faithfulness/groundedness | Whether answer claims are supported by retrieved context | Usually requires an LLM judge or carefully designed claim checking |
| Answer relevance | Whether the response directly addresses the question | A relevant response can still be wrong |
| Refusal correctness | Whether unsupported questions are refused appropriately | Requires answerability labels and should distinguish safe refusal from over-refusal |
| Latency | Operational responsiveness | Faster does not mean more accurate |
| Estimated API cost | Resource trade-offs between methods | Provider prices and token accounting can change |
| Human review | Nuanced correctness and usefulness | Slower, subjective, and difficult to scale |

The research should compare metric behavior rather than combining all scores
into one unexplained number. If a composite score is added, its weights and
purpose must be documented.

## Initial Experiment Sequence

### Experiment 1: Metric Behavior on a Fixed Baseline

Hold the current RAG configuration fixed and run all reviewed questions. Apply
the initial metrics to the same stored responses. Inspect cases where exact
match, semantic similarity, source accuracy, and human judgment disagree.

### Experiment 2: Retrieval Method or Top-K

Compare the keyword baseline and ChromaDB semantic retrieval, or compare top-k
values such as 3, 5, and 8 while keeping other settings fixed. Separate source
retrieval results from answer-generation results.

### Experiment 3: Corpus Size and Composition

Create reproducible document subsets, for example a small focused collection
and the full 27-document collection. If more approved documents become
available, add a larger collection. Run the same applicable questions and
settings against each collection.

Measure:

- expected-source hit rate at top-k;
- ranking changes and irrelevant-context rate;
- answer correctness and faithfulness;
- refusal behavior;
- latency; and
- changes in agreement between evaluation metrics.

This experiment does not attempt to reproduce a company with millions of
documents on a local capstone machine. It produces evidence about how increasing
search-space size or adding similar distractor documents changes behavior, then
states the limits of generalizing those observations to enterprise scale.

### Experiment 4: Failure Analysis

Review low-scoring and metric-disagreement cases. Assign a failure type:

- ingestion or parsing failure;
- missing or incorrect expected data;
- retrieval miss;
- relevant source ranked too low;
- insufficient retrieved context;
- unsupported generation;
- incomplete answer;
- incorrect refusal;
- misleading automated score; or
- ambiguous question.

## Multi-Format Document Capability

FP6 adds browser-based TXT, PDF, and DOCX upload. All formats feed
one normalized ingestion pipeline:

```text
browser upload
  -> PHP validation and private file storage
  -> Python format-specific text extraction
  -> normalized text and metadata
  -> existing chunking and stable identifiers
  -> MySQL document/chunk records
  -> ChromaDB embeddings
  -> ingestion status shown in the browser
```

Implementation requirements:

- allow only `.txt`, `.pdf`, and `.docx` initially;
- validate extension, MIME type, size, and successful upload status;
- generate server-controlled storage names instead of trusting filenames;
- reject encrypted, unreadable, empty, or unsupported files with clear errors;
- preserve original filename and document type as metadata;
- extract text server-side and never execute uploaded content;
- record parsing/ingestion failures in MySQL;
- replace or re-ingest a document without leaving duplicate chunks;
- delete browser-managed uploads from storage, MySQL, and ChromaDB while
  protecting bundled sources;
- update indexed document/category counts from the live document list;
- keep uploaded files and generated vector data out of Git;
- add parser and upload tests using small non-sensitive fixtures.

Recommended Python libraries are `pypdf` for text-based PDFs and
`python-docx` for DOCX files. Scanned-image OCR is a later enhancement unless
the professor explicitly requires it.

## FP6-FP10 Research Roadmap

### FP6: Document Administration and Multi-Format Ingestion

Implementation status: completed, verified, committed, and pushed July 6, 2026.

- Add browser upload/list/replace/delete controls and live counts.
- Support TXT, text-based PDF, and DOCX extraction.
- Connect uploaded files to the existing MySQL/ChromaDB ingestion workflow.
- Display document type, ingestion status, chunk count, and useful errors.
- Preserve the completed Ask workflow and add regression tests.

### FP7: Gold Dataset and Baseline Metrics

- Create at least 25 manually verified evaluation questions.
- Cover all current categories and include unanswerable cases.
- Add question-management and evaluation-run interfaces.
- Implement normalized match, semantic similarity, expected-source accuracy,
  refusal correctness, and latency.
- Store per-question scores and all run settings.

### FP8: Advanced Metrics and Research Experiments

- Add faithfulness/groundedness and answer-relevance evaluation.
- Evaluate whether LLM-as-judge or selected RAGAS-style metrics add useful
  evidence beyond the baseline metrics.
- Run controlled retrieval/top-k and corpus-size/composition experiments.
- Analyze disagreements and label failure cases.

### FP9: Results, Interpretation, and System Testing

- Build dashboard comparisons and drill-down views.
- Explain each metric in plain language, including limitations.
- Present per-question failures and metric disagreements.
- Write preliminary findings and stakeholder-specific recommendations.
- Complete accessibility, upload security, and end-to-end testing.

### FP10: Final Research Report and Delivery

- Stabilize the application and reproducible experiment procedure.
- Finalize findings, limitations, and future-research questions.
- Demonstrate how evidence leads to recommendations.
- Deliver setup documentation, final report, presentation, and tagged release.

## Interpretation Rules

- Do not claim that a metric, provider, or configuration is universally best.
- State which corpus, questions, settings, and judge were used for every claim.
- Treat LLM-as-judge output as another measurement, not unquestionable truth.
- Separate observed results from explanations or hypotheses.
- Report negative and contradictory results instead of hiding them.
- Do not generalize the local 27-document experiment directly to millions of
  enterprise documents; describe what the experiment suggests and its limits.
