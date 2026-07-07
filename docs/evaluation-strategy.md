# RAG Evaluation Strategy

## Confirmed Research Objective

The professor expects the project to research, implement, compare, and explain
approximately ten evaluator or metric types. The purpose is not to integrate
RAGAS alone or display ten unrelated scores. The project must demonstrate
enough understanding to explain what each evaluator measures, what it misses,
what it costs, and when it is useful.

The same saved RAG responses and retrieved contexts must be evaluated by every
applicable evaluator. This controlled design makes disagreements meaningful:
the answer, question, expected answer, expected source, and retrieved evidence
stay fixed while only the evaluation method changes.

Professor-provided reference:

- [RAG Chatbot Accuracy Evaluation: Options & Trade-offs](https://github.com/sjasthi/ics499/blob/main/presentations/rag_chatbot_evaluations.md)

The reference distinguishes two primary dimensions:

1. Retrieval quality: did the system retrieve the right evidence and rank it
   high enough?
2. Generation quality: did the model answer correctly, relevantly, and only
   from the retrieved evidence?

## Proposed Ten Evaluator Types

This is the working implementation set. It may be refined when dependency,
cost, or dataset testing reveals a defensible reason, but substitutions must
preserve coverage across lexical, semantic, retrieval, grounding, and judged
evaluation.

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

Supporting measurements are required but are not counted as the ten answer or
retrieval evaluators:

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

## Dataset Requirements

The earlier target of at least 25 manually reviewed questions remains the
working dataset-size goal unless the professor changes it. That number is
separate from the ten evaluator types.

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

## FP7-FP10 Execution Plan

### FP7: Evaluation Foundation and Local Baselines

- Finalize and manually verify the evaluation question schema and initial
  dataset.
- Add question management and dataset-version support.
- Add evaluator metadata/result storage so heterogeneous outputs can coexist.
- Build the runner that generates one response and saves exact contexts once.
- Implement inexpensive local evaluators first: exact/contains,
  BLEU/ROUGE/METEOR family, semantic similarity, BERTScore, expected-source
  accuracy, refusal correctness, and latency/runtime tracking.
- Add per-question result tables and raw evaluator error reporting.

### FP8: Judged/RAGAS Evaluators and Experiments

- Add a versioned LLM-as-judge rubric.
- Add RAGAS Faithfulness, Response Relevancy, Context Precision, and Context
  Recall with explicit model/prompt/version settings.
- Track evaluator API usage, runtime, failures, and estimated cost.
- Run the same fixed baseline responses through all evaluator types.
- Analyze disagreements and calibrate selected thresholds against human review.
- Run controlled top-k/retrieval and corpus-composition comparisons.

### FP9: Research Dashboard, Interpretation, and UX

- Present per-question scores, evaluator explanations, errors, and failure
  categories.
- Compare evaluator agreement, disagreement, runtime, and cost.
- Provide plain-language descriptions and limitations for each evaluator.
- Add charts only where they clarify relationships; preserve inspectable tables
  and source evidence.
- Improve visual design, accessibility, and workflow clarity after the research
  pipeline is stable.

### FP10: Validation and Teaching Deliverables

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

FP6 is complete. FP7 should begin by finalizing the database representation for
question metadata, dataset versions, evaluator definitions, evaluator runs,
and heterogeneous results. Before installing RAGAS or other heavy dependencies,
create the reviewed-question workflow and prove that multiple inexpensive
evaluators can score the same saved response without regenerating it.

