# RAG Evaluation Strategy

## Working Research Objective

The professor-provided reference presents eight broad evaluation options; it
does not say that the project needs eight advanced models. The working project
scope implements representative baseline methods plus a smaller advanced layer
and researches what each measurement contributes. The purpose is not to
integrate RAGAS alone, collect an arbitrary number of scores, or declare one
universal winner. The project must explain what each evaluator measures, what
the score is based on, what it misses, what it costs, and when it is useful.

The same saved RAG responses and retrieved contexts must be evaluated by every
applicable evaluator. This controlled design makes disagreements meaningful:
the answer, question, expected answer, expected source, and retrieved evidence
stay fixed while only the evaluation method changes.

Professor-provided reference:

- [RAG Chatbot Accuracy Evaluation: Options & Trade-offs](https://github.com/sjasthi/ics499/blob/main/presentations/rag_chatbot_evaluations.md)
- [RAGAS available metrics](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/)

The reference distinguishes two primary dimensions:

1. Retrieval quality: did the system retrieve the right evidence and rank it
   high enough?
2. Generation quality: did the model answer correctly, relevantly, and only
   from the retrieved evidence?

## Project Evaluator Portfolio

The professor's eight options are exact/string matching, token overlap,
semantic similarity, BERTScore, LLM-as-judge, RAGAS, human evaluation, and
production A/B testing. The first four informed the FP7 baseline; LLM-as-judge
and four RAGAS dimensions form the FP8 advanced layer; human review calibrates
the study; production A/B testing is documented but cannot be executed without
real traffic. The project therefore should be described by layers and purposes,
not by implying every item is the same kind of metric or model.

| # | Evaluator type | Primary dimension | Inputs | Execution | Main value | Main limitation |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Exact/contains match | Generation | Expected and actual answer | Deterministic/local | Clear pass signal for dates, amounts, names, and required phrases | Rejects valid paraphrases and may reward unsupported keyword copying |
| 2 | Token-overlap family: BLEU, ROUGE-L, and/or METEOR | Generation | Expected and actual answer | Deterministic/local | Fast numeric regression comparison | Word overlap is not factual correctness; verbose or paraphrased answers can be mis-scored |
| 3 | Embedding semantic similarity | Generation | Expected and actual answer | Local embedding model | Recognizes paraphrases and related meaning | Can score a factually wrong answer highly when wording is similar |
| 4 | BERTScore | Generation | Expected and actual answer | Local model; heavier | Contextual token-level precision, recall, and F1 | More compute, model-dependent, and still not proof of grounding |
| 5 | Expected-source accuracy | Retrieval | Expected source and ranked retrieved sources | Deterministic/local | Directly tests whether retrieval found the reviewed source | Does not prove the retrieved chunk contains sufficient evidence |
| 6 | LLM-as-judge rubric | Generation/both | Question, expected answer, actual answer, and optionally contexts | Evaluator-model API | Handles nuanced accuracy, completeness, and explanation | Costs money, varies by prompt/model/run, and can inherit judge bias |
| 7 | RAGAS Faithfulness | Generation grounding | Actual answer and retrieved contexts | Usually evaluator LLM | Detects answer claims unsupported by retrieved evidence | Judge-dependent; a faithful answer can still be irrelevant or based on bad context |
| 8 | RAGAS Response Relevancy | Generation | Question and actual answer | Evaluator LLM/embeddings | Tests whether the response addresses the question | A relevant answer can still be false or ungrounded |
| 9 | RAGAS Context Precision | Retrieval | Question, contexts, and reference information | Usually evaluator LLM | Tests whether relevant chunks rank above distracting chunks | Requires relevance judgments and can add multiple evaluator calls |
| 10 | RAGAS Context Recall | Retrieval | Expected answer/reference and contexts | Usually evaluator LLM | Tests whether retrieval captured the evidence needed for the answer | Depends on reference quality and evaluator interpretation |

Supporting measurements are required but are not answer-quality evaluators:

- latency;
- evaluator runtime;
- estimated API/token cost;
- failure/error status;
- human-review rating; and
- refusal correctness for deliberately unanswerable questions.

Human review is the calibration baseline used to inspect whether automated
metrics are behaving sensibly. Production A/B testing is documented as an
evaluation option but is outside this localhost capstone because it requires
real users, traffic, and outcome signals.

## How to Read a Score

The RAG system produces one saved answer. Metrics do not vote on or jointly
produce that answer. Each applicable evaluator independently compares selected
saved inputs and produces evidence about one dimension. The response is
therefore represented by a metric profile rather than one overall grade.

Every displayed score must identify:

- what it compared: reference answer, reviewed required facts, question,
  retrieved contexts, expected source, or answerability label;
- how it was calculated and what the numerator/denominator mean;
- its scale and whether higher is better;
- its configured threshold and whether that threshold is calibrated or merely
  a project-defined review cutoff;
- what being above or below the threshold means; and
- what the score cannot prove.

The current FP7 thresholds are descriptive starting points. They were not
learned from the 25-question set and are not claimed as universal standards.
Until compared with human-reviewed outcomes, the UI should say `Above review
threshold` or `Below review threshold`, not equate the threshold with factual
correctness.

| FP7 evaluator | Basis of the number | Current rule | Correct interpretation and limitation |
| --- | --- | --- | --- |
| Exact/accepted-answer match | Normalized equality=`1.0`; containment=`0.75`; otherwise `0` | Containment or equality | A lexical signal; it does not prove completeness or grounding |
| Required-fact coverage | Reviewed fact strings found / total reviewed fact strings | All facts found (`1.0`) | `1.0` means every listed phrase appeared, not that the whole answer is correct |
| Token F1 | Harmonic mean of unigram precision and recall against the reference | Descriptive `0.70` | Measures word overlap, not factual truth |
| ROUGE-L F1 | Harmonic mean based on longest common token subsequence | Descriptive `0.70` | Rewards shared ordering/phrasing and may penalize paraphrases |
| Embedding similarity | Cosine similarity of answer/reference embeddings from `all-MiniLM-L6-v2` | Descriptive `0.75` | Meaning similarity can remain high when a date or number is wrong |
| BERTScore F1 | Contextual-token precision/recall/F1 from `distilbert-base-uncased` | Descriptive `0.80` | Not a probability or percent factual correctness |
| Expected-source accuracy | Expected source appears anywhere in saved top-k=`1`, otherwise `0`; rank is retained | Source present | Does not prove the retrieved excerpt was sufficient or used |
| Refusal correctness | Fixed refusal behavior agrees with reviewed answerability label | Agreement=`1` | Does not assess the quality of an answerable response |

For saved response 17, the sole reviewed required fact is `April 6, 2026`, so
finding it gives `1 / 1 = 1.0` required-fact coverage. BERTScore compares the
reference sentence with the generated paraphrase and produced precision
`0.9279`, recall `0.9798`, and F1 `0.9531`. That result is above the current
`0.80` review threshold and indicates highly similar contextual wording; it
does not mean the answer is 95.31 percent factually correct.

## Choosing Evaluators by Purpose

| Purpose | Start with | Add when needed |
| --- | --- | --- |
| Cheap repeatable regression | required facts, token/ROUGE, semantic similarity, source accuracy | advanced review for changed or suspicious cases |
| Nuanced correctness/completeness | versioned LLM judge | human calibration and baseline evidence |
| Grounding or hallucination | RAGAS Faithfulness | judge faithfulness and context/human inspection |
| Answer directness | RAGAS Response Relevancy | correctness and faithfulness signals because relevance alone is insufficient |
| Retrieval ranking/noise | RAGAS Context Precision | expected-source rank and context inspection |
| Retrieval completeness | RAGAS Context Recall | verified reference evidence and human review |
| Unanswerable behavior | refusal correctness and judge answerability rubric | sampled human review; skip inapplicable RAGAS metrics |
| Release/high-risk decision | the relevant metric profile | human review; never rely on one score |

## Dataset Requirements

The earlier target of at least 25 manually reviewed questions remains the
working dataset-size goal unless the professor changes it. That number is
separate from the evaluator portfolio. The planning table names ten primary
types; the executable catalog registers 13 methods because required-fact
coverage, ROUGE-L, and refusal correctness are retained as distinct baseline
signals rather than hidden inside broader families.

Each evaluation question should store:

- question text;
- concise expected answer;
- expected source document and, where practical, expected evidence excerpt;
- category;
- difficulty;
- answerable/unanswerable label;
- required facts or accepted answer variants;
- reviewer notes; and
- active/version status.

The dataset should cover all current Metro State categories and include dates,
amounts, requirements, policy questions, similar-document distractors,
multi-fact questions, and deliberately unsupported questions. Expected data
must be manually verified against the source corpus because every downstream
metric comparison depends on its quality.

## Controlled Evaluation Protocol

1. Freeze a reviewed question-set version and corpus version.
2. Record the retrieval, chunking, prompt, provider, model, temperature, top-k,
   and embedding settings.
3. Generate one RAG response per question and save the exact ranked contexts.
4. Apply every compatible evaluator to that same stored response; do not
   regenerate the answer separately for each evaluator.
5. Store raw score, normalized score where applicable, explanation/details,
   evaluator version/configuration, runtime, cost estimate, and error status.
6. Add a human-review label for a representative sample or all initial cases.
7. Compare evaluator agreement and disagreement per question rather than only
   comparing averages.
8. Assign failure categories: ingestion, expected-data, retrieval, generation,
   refusal, evaluator, or ambiguous-question failure.
9. Repeat selected runs while changing one controlled variable at a time.

## Required Comparisons and Teaching Examples

The final report and demonstration should include concrete examples that teach
the trade-offs:

- a correct paraphrase that exact match penalizes;
- a wrong date or amount that semantic similarity scores too generously;
- a response that is relevant but unsupported by its retrieved context;
- a faithful response produced from incomplete or incorrect retrieval;
- a run where the expected source is retrieved but ranked below distractors;
- a case where context precision and context recall move in different
  directions;
- an unanswerable question that should trigger the fixed refusal;
- an LLM-judge score that changes with judge prompt/model or repeated run; and
- a case where human review disagrees with one or more automated metrics.

For every evaluator, the application/report must answer:

1. What does it measure?
2. Does it evaluate retrieval, generation, or both?
3. What inputs and ground truth does it require?
4. Is it deterministic, embedding-based, or LLM-judged?
5. What is its runtime and monetary cost?
6. Which failures does it detect well?
7. Which failures can it miss or misrepresent?
8. What threshold or interpretation rule is used?
9. Which stakeholder or workflow benefits from it?
10. Should it be used alone or with complementary evaluators?
11. Is its threshold calibrated, project-defined, or absent?
12. What exact evidence produced this particular score?

## FP7-FP10 Execution Plan

### FP7: Evaluation Foundation and Local Baselines

Status: completed and verified July 10, 2026.

- Finalize and manually verify the evaluation question schema and initial
  dataset.
- Add question management and dataset-version support.
- Add evaluator metadata/result storage so heterogeneous outputs can coexist.
- Build the runner that generates one response and saves exact contexts once.
- Implement inexpensive local evaluators first: exact/contains,
  BLEU/ROUGE/METEOR family, semantic similarity, BERTScore, expected-source
  accuracy, refusal correctness, and latency/runtime tracking.
- Add per-question result tables and raw evaluator error reporting.

The implemented local set separates the token-overlap family into token F1 and
ROUGE-L and adds required-fact coverage as an auditable reviewed-fact signal.
Together with exact/contains, semantic similarity, BERTScore, expected-source
accuracy, and refusal correctness, FP7 registers eight local or supporting
evaluators. FP8 adds the versioned LLM judge and four RAGAS dimensions, while
the final report groups methods by family and use rather than
defending an arbitrary metric count.

### FP8: Judged/RAGAS Evaluators and Experiments

Implementation status: evaluator/application infrastructure completed and
verified July 14, 2026. Real advanced scores remain pending an explicitly
authorized cost-bounded provider run.

- Add a versioned LLM-as-judge rubric for correctness, completeness,
  faithfulness, relevance, and answerability/refusal.
- Add RAGAS Faithfulness, Response Relevancy, Context Precision, and Context
  Recall with explicit model/prompt/version settings.
- Map RAGAS inputs from the saved question, answer, ordered contexts, reviewed
  reference, and expected evidence; never regenerate an answer for evaluation.
- Store applicability, skips, API/token usage, runtime, failures, raw model
  output, estimated cost, and exact judge/model/prompt/library versions.
- Preserve repeated judge attempts so variability can be measured rather than
  overwritten.
- Add response-level human reviews separately from Dataset review state.
- Start with the three saved Run 3 responses, then expand to the fixed reviewed
  set only after a cost-bounded proof is stable.
- Analyze disagreements and test descriptive thresholds against sampled human
  review instead of treating a cutoff as truth.
- Implement genuine MySQL chunk retrieval before comparing it with ChromaDB;
  then run one-variable-at-a-time top-k and corpus-composition comparisons.
- Present automatic evidence as clearly named Local, LLM-judge, and RAGAS UI
  groups; label Human review as supporting evidence and operational fields as
  metadata, with a purpose-based evaluator guide and no unexplained average.

### FP9: Research Dashboard, Interpretation, and UX

Implementation status: dashboard/API/human-review infrastructure completed and
verified July 14, 2026. Empirical findings remain pending matched experiments
and reviewer evidence.

- Present per-question scores, evaluator explanations, errors, and failure
  categories.
- Compare evaluator agreement, disagreement, runtime, and cost.
- Provide plain-language descriptions and limitations for each evaluator.
- Add charts only where they clarify relationships; preserve inspectable tables
  and source evidence.
- Improve visual design, accessibility, and workflow clarity after the research
  pipeline is stable.

### FP10: Validation and Teaching Deliverables

Implementation status (July 20, 2026): reproducibility/cost hardening,
question-matched Findings, accessibility, provider-free validation, CI, and the
demo/checkoff materials are complete. Repeat paid runs, human calibration,
empirical recommendations, final presentation/report delivery, and release
tagging remain pending.

- Repeat key runs for reproducibility and document environment/version details.
- Finalize findings, recommendations by use case/stakeholder, and limitations.
- Prepare a demonstration that teaches why evaluator scores differ.
- Deliver the final report, setup/reproduction guide, presentation, and tagged
  release.

## Implementation Principles

- Do not combine unlike metrics into one unexplained universal score.
- Do not claim that RAGAS or any other framework is inherently best.
- Keep raw evaluator outputs and configuration details for auditability.
- Separate evaluator failures from RAG pipeline failures.
- Never use evaluator scores without inspecting representative examples.
- Prefer repeatable local metrics for frequent checks and reserve costly judged
  metrics for deliberate research runs.
- Treat evaluator disagreement as research evidence, not merely noise.
- State conclusions only for the tested corpus, question set, models, settings,
  and evaluator versions.

## Immediate Resume Point

FP8/FP9 support and FP10 provider-free hardening are implemented. Resume only
after recording current provider pricing, an approved monetary cap, the exact
response/application count, and whether unknown cost is permitted. First run a
dry-run-reviewed one-response baseline proof, then an advanced proof against
that saved response. Inspect raw judge/RAGAS output, runtime, applicability,
usage, and immutable provenance before expanding. Then collect a human review
and run matched one-variable retrieval or corpus comparisons. Do not regenerate
answers merely to add an evaluator, do not treat a project threshold as truth,
and do not write comparative findings until the corresponding stored evidence
exists. See `docs/fp8-fp9-implementation.md` and `docs/fp10-hardening.md`.
