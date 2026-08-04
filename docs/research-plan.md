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
6. What portfolio of complementary metrics gives defensible evidence for a
   particular decision without hiding disagreements in one overall score?

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

The working research emphasis is representative evaluator types drawn from
multiple method families, not ten questions, eight advanced models, or a
RAGAS-only integration. The professor-provided reference lists eight broad
options. This project uses the first four as baseline families, adds an
LLM-as-judge and four selected RAGAS dimensions, calibrates them with sampled
human review, and documents production A/B testing as out of scope. See
`docs/evaluation-strategy.md` for the evaluator set, controlled protocol,
score contracts, trade-offs, teaching examples, and FP7-FP10 sequence.

## Evaluation Dataset Design

Dataset v2.0 now contains 50 manually reviewed questions. The original 25-case
v1.0 set was a practical starting point, not a universal ratio between questions
and documents, and remains tracked for historical reproducibility. The final
count is justified by added category, distractor, multi-fact, policy, cost, and
failure-mode coverage.

The initial dataset should:

- cover all eight current Metro State document categories;
- include factual dates, amounts, requirements, and policy questions;
- include questions that require distinguishing similar documents or terms;
- include answerable and deliberately unanswerable questions;
- store a verified expected answer and expected source document;
- record category, difficulty, and answerability;
- avoid multiple questions that test the same fact without a research reason.

For the current 27-document collection, the 50-question v2.0 set is the final
submission baseline. More questions should be added only when they improve topic,
document, difficulty, or failure-mode coverage. A much larger document corpus
does not automatically require the same proportional increase in questions;
the evaluation set should instead sample the behaviors and risks that matter.

## Metrics and Their Specific Uses

Professor-provided evaluation reference:

- [RAG Chatbot Accuracy Evaluation: Options & Trade-offs](https://github.com/sjasthi/ics499/blob/main/presentations/rag_chatbot_evaluations.md)

This reference separates retrieval quality from generation quality and compares
exact/string matching, BLEU/ROUGE/METEOR, semantic similarity, BERTScore,
LLM-as-judge, RAGAS, human evaluation, and production A/B testing. These are
method options rather than eight required advanced models. The project applies
representative methods against the same stored responses, records
cost/speed/determinism trade-offs, and uses human-reviewed expected
answers/sources to interpret metric agreement and disagreement.

RAGAS is one evaluator framework within the comparison rather than the entire
research scope. Human review is the calibration baseline. Production A/B
testing is discussed as an option but is not an implementation target for a
localhost capstone without real traffic.

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

Every score must have a documented contract: exact comparison target,
calculation and scale, configured threshold, whether the threshold is
calibrated or project-defined, the interpretation of high/low values, and what
the score cannot prove. Current FP7 cutoffs are descriptive review thresholds,
not universal correctness boundaries. FP8/FP9 now expose those rules and
support sampled human judgments; threshold calibration still requires actual
review evidence before threshold-based claims.

## Initial Experiment Sequence

### Experiment 1: Metric Behavior on a Fixed Baseline

Hold the current RAG configuration fixed and run all reviewed questions. Apply
the local and advanced metrics to the same stored responses. Inspect cases
where required-fact coverage, lexical/semantic similarity, source accuracy,
RAGAS dimensions, LLM judgment, and human judgment disagree. Start by applying
the advanced evaluators to the three saved Run 3 responses without regenerating
their answers, then expand only after the cost-bounded proof is stable.

August 3 bounded-study result: five stratified questions were used for the
deadline matrix rather than claiming execution of all 50. All eight baseline
methods ran on 30 responses; all five advanced methods ran on one matched hard
case in each retrieval condition. The sample-size limitation must remain
explicit in any reported findings.

On a stratified subset, repeat the LLM judge and preserve every attempt. Report
score range/variance and decision agreement so judged results are not treated
as deterministic. Keep evaluator failures and skipped/not-applicable results
separate from answer-quality scores.

### Experiment 2: Retrieval Method or Top-K

Compare genuine MySQL FULLTEXT/lexical retrieval and ChromaDB semantic
retrieval, or compare top-k values such as 3, 5, and 8 while keeping other
settings fixed. Separate source retrieval results from answer-generation
results. The retained filesystem keyword command is a troubleshooting baseline,
not the database comparison condition.

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
separately required. The final review requested a researched multimodal plan,
not a late change to the completed text-only baseline; that plan is recorded in
the [post-capstone roadmap](post-capstone-roadmap.md).

## FP6-FP10 Research Roadmap

### FP6: Document Administration and Multi-Format Ingestion

Implementation status: completed, verified, committed, and pushed July 6, 2026.

- Add browser upload/list/replace/delete controls and live counts.
- Support TXT, text-based PDF, and DOCX extraction.
- Connect uploaded files to the existing MySQL/ChromaDB ingestion workflow.
- Display document type, ingestion status, chunk count, and useful errors.
- Preserve the completed Ask workflow and add regression tests.

### FP7: Gold Dataset and Baseline Metrics

Implementation status: completed and verified July 10, 2026.

- Create at least 25 manually verified evaluation questions.
- Cover all current categories and include unanswerable cases.
- Add question-management and evaluation-run interfaces.
- Add evaluator definitions and heterogeneous per-question result storage.
- Implement local baseline families: exact/contains, token overlap,
  embedding-semantic similarity, BERTScore, expected-source accuracy, refusal
  correctness, latency, and evaluator runtime.
- Generate each RAG response once and apply all compatible evaluators to the
  same saved answer and contexts.
- Store raw scores/details, evaluator versions/settings, errors, runtime, and
  cost estimates.

Implemented FP7 evidence:

- dataset version 1.0 contains 25 reviewed questions across all eight source
  categories plus three deliberately unanswerable questions;
- eight local evaluators operate on the same saved response: exact/contains,
  required-fact coverage, token F1, ROUGE-L, semantic similarity, BERTScore,
  expected-source accuracy, and refusal correctness;
- a controlled runner links responses to questions and runs, saves exact ranked
  contexts, and records heterogeneous results without regenerating answers;
- the browser supports dataset review/filtering, run history, response detail,
  separate evaluator scores/explanations/runtime, and retrieved evidence; and
- the representative three-question run stored 24 successful evaluator results
  with all expected sources ranked first.

### FP8: Advanced Metrics and Research Experiments

Implementation status: evaluator contracts, judge/RAGAS adapters, immutable
attempts, applicability/failure handling, cost-bounded runner, human-review
schema, reproducible run metadata, MySQL retrieval, and category corpus variants
were completed and verified July 14, 2026. No paid advanced scores were created
during that implementation pass. A separate July 20 bounded proof later stored
one completed LLM-judge result. The preserved RAGAS adapter/dependency failures
were corrected, and bounded retries completed all four RAGAS metrics for that
same response. The August 3 continuation completed six controlled conditions,
matched advanced scoring, and seven selected human reviews.

- Add a versioned LLM-as-judge rubric plus RAGAS Faithfulness, Response
  Relevancy, Context Precision, and Context Recall.
- Determine what judged/RAGAS metrics add beyond local baselines and where
  their cost, variability, or evaluator bias changes their usefulness.
- Store judge model/prompt/configuration, raw output, usage, runtime, cost,
  applicability, and errors; preserve repeated attempts.
- Add a sampled human response-review rubric separate from Dataset review.
- Label FP7 cutoffs as project-defined and test them against reviewed cases.
- Explain each score's basis, calculation, scale, threshold, and limitation in
  the Evaluation UI.
- Run controlled retrieval/top-k and corpus-size/composition experiments.
- Analyze disagreements and label failure cases.

### FP9: Evaluation Results, Interpretation, and System Testing

Implementation status: the drill-down now housed under Evaluation, score-contract explanations,
human-review form, disagreement prompts, run comparison, interpretation rules,
and full evaluator catalog were completed and verified July 14, 2026. The final
clarity pass groups automatic results as Local metrics, LLM judge, and RAGAS,
with Human review labeled separately as supporting evidence.
Matched automated findings are available from the completed study runs.
Seven selected final-study responses have single-reviewer overall human decisions:
six acceptable and one needs revision.

- Build dashboard comparisons and drill-down views.
- Explain each metric in plain language, including limitations.
- Present per-question failures and metric disagreements.
- Write preliminary findings and stakeholder-specific recommendations.
- Complete accessibility, upload security, and end-to-end testing.

### FP10: Final Research Report and Delivery

Implementation status (August 2, 2026): application stabilization,
reproducibility/cost safeguards, matched-comparison rules, accessibility,
provider-free CI, documentation, the 50-question v2.0 answer key, portable run
exports, and FP10 demonstration/checkoff preparation are complete. The August 3
matrix, evidence exports, evidence-based report draft, and presentation outline
are also complete, along with the seven-response human-calibration sample. Final
presentation delivery, commit/push, and the release tag remain pending.

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
