# LLM RAG Evaluation Project — Final Report

**Andrew Xiong · ICS 499 Capstone · Metro State University**

Prepared August 3, 2026. This report is evidence-complete for the bounded
automated study and its seven-response single-reviewer human sample.

Repository evidence: [final-study JSON exports](../data/evaluation/final-study/README.md)
and [evaluator contracts](evaluation-strategy.md).

## Executive Summary

This capstone produced a PHP/MySQL research workbench for evaluating
Retrieval-Augmented Generation over Metro State documents. The application
manages and indexes documents, retrieves evidence through Chroma vector search
or MySQL lexical search, generates grounded Gemini answers, applies 13 named
evaluation methods, preserves reproducibility metadata, supports sampled human
review, and exports portable evidence.

The final bounded experiment compared six completed configurations on the same
five reviewed questions. The sample deliberately included easy, medium, and
hard questions; a false-premise unanswerable question; multi-fact answers;
date and numeric distractors; and four subject areas. Thirty saved responses
produced 250 canonical results: 238 completed and 12 correctly skipped as not
applicable, with no evaluator failures in the completed study.

A student reviewer then assessed the five run-5 responses and the two
incomplete higher-top-k responses. Six were marked acceptable and one was
marked needs revision for an incomplete answer. The reviewer supplied overall
decisions rather than dimension-level rubric scores, so the calibration below
is descriptive and does not claim inter-rater or per-dimension agreement.

The strongest supported recommendation is Chroma vector retrieval at top-k 3
for this 27-document corpus. It found the reviewed source at rank 1 for all four
answerable cases, preserved every reviewed required fact, refused the
unanswerable case, and used substantially fewer tokens than top-k 5 or 8.
MySQL retrieval was equally successful on these five questions, so the study
does not establish a retrieval-quality winner. Gemini 3.1 Flash-Lite preserved
source hit, required-fact, and refusal results while reducing mean latency from
2,276 ms to 1,053 ms, but the sample is too small for a universal model claim.

The experiment also found a real pipeline defect. Two higher-top-k answers
ended mid-sentence because the old 512-token output allocation was nearly
consumed by hidden thinking tokens. The generator now uses a 2,048-token
allocation, rejects non-STOP finish reasons, records thinking and finish
metadata, and includes thinking tokens in cost estimates. Historical results
were not rewritten; the incomplete answers remain failure-analysis evidence.

## Research Questions

1. Which metrics expose retrieval, correctness, grounding, completeness, and
   refusal failures?
2. Where do metrics agree or disagree on the same response?
3. Which metric portfolio is useful for regression testing, diagnosis, and
   human decision support?
4. How do retrieval method, top-k, answer model, and corpus composition affect
   observed quality and operational behavior?
5. What can and cannot be generalized from a local 27-document experiment?

## System and Data

The required stack is preserved: HTML/CSS/Bootstrap/jQuery in the browser, PHP
API endpoints, MySQL for relational state, Python for retrieval/generation and
evaluation, ChromaDB for vector search, and Gemini for answer/judge calls.

The corpus contains 27 bundled Metro State text sources divided across eight
categories and indexed as 77 chunks with chunk size 800 and overlap 100.
MySQL and Chroma both reported 77 active chunks before the study. Dataset v2.0
contains 50 unique, active, reviewed questions: 47 answerable and three
unanswerable. Each answerable case has a reviewed answer, expected source,
source-verified evidence, accepted variants, and required facts. Dataset v1.0
is retained for historical reproducibility.

The application freezes the dataset/question snapshot, ordered contexts,
document manifest and hashes, retrieval algorithm, model settings, code and
dependency versions, usage, cost status, evaluator attempts, and failures for
each new run. The six completed exports and their checksums are tracked in the
[final-study evidence directory](../data/evaluation/final-study/README.md).

## Controlled Study Design

All completed conditions used the exact ordered question IDs
`1, 23, 210, 213, 221`, corresponding to dataset positions
`1, 23, 35, 38, 46`.

| Position | Category | Difficulty | Answerability | Purpose |
| ---: | --- | --- | --- | --- |
| 1 | Academic calendar | Easy | Answerable | Fall/Spring/Summer date distractors |
| 23 | Unanswerable | Easy | Unanswerable | Exact safe-refusal behavior |
| 35 | Financial aid | Hard | Answerable | Multi-step, multi-fact answer |
| 38 | Graduation | Hard | Answerable | GPA range plus Metro State credit minimum |
| 46 | Tuition/fees | Medium | Answerable | Numeric and audit/enrollment distractors |

Run 5 was the reference condition. Every comparison reused the same ordered
question IDs and changed one supported setting. The server independently
validated the exact baseline response question set; equal counts alone were
not accepted.

| Run | Controlled condition | Baseline | Retrieval | Top-k | Model | Documents |
| ---: | --- | ---: | --- | ---: | --- | ---: |
| 5 | Reference | — | Chroma vector | 3 | Gemini 2.5 Flash | 27 |
| 6 | Retrieval method | 5 | MySQL keyword | 3 | Gemini 2.5 Flash | 27 |
| 7 | Top-k | 5 | Chroma vector | 5 | Gemini 2.5 Flash | 27 |
| 8 | Top-k | 5 | Chroma vector | 8 | Gemini 2.5 Flash | 27 |
| 10 | Answer model | 5 | Chroma vector | 3 | Gemini 3.1 Flash-Lite | 27 |
| 12 | Corpus composition | 10 | Chroma vector | 3 | Gemini 3.1 Flash-Lite | 20 |

The 20-document subset retained academic-calendar, financial-aid, graduation,
and tuition/fees documents. Runs 5–10 used temperature 0 and top-p 0.9. Run 12
retained run 10's settings so only corpus composition changed.

## Evaluation Methods

Eight baseline methods were applied to every saved answer: exact/accepted
answer matching, required-fact coverage, token F1, ROUGE-L, embedding semantic
similarity, BERTScore, expected-source accuracy, and refusal correctness.

Five advanced methods were applied to the same hard financial-aid answer in
the matched Chroma and MySQL runs: a versioned Gemini judge rubric plus RAGAS
Faithfulness, Response Relevancy, Context Precision, and Context Recall. These
methods scored the already-saved answer and contexts; they did not regenerate
the answer.

The application does not average unlike methods into a universal grade. Each
method has a documented comparison target, calculation/rubric, scale,
project-defined review threshold, and limitation in repository file
`docs/evaluation-strategy.md`.

## Results

### Retrieval, required facts, and refusal

| Run | Expected source hit (answerable) | Expected source at rank 1 | Required-fact mean | Refusal mean |
| ---: | ---: | ---: | ---: | ---: |
| 5 | 4/4 | 4/4 | 1.00 | 1.00 |
| 6 | 4/4 | 4/4 | 1.00 | 1.00 |
| 7 | 4/4 | 4/4 | 0.75 | 1.00 |
| 8 | 4/4 | 4/4 | 0.75 | 1.00 |
| 10 | 4/4 | 4/4 | 1.00 | 1.00 |
| 12 | 4/4 | 4/4 | 1.00 | 1.00 |

The unanswerable question correctly skipped required-fact and expected-source
evaluation, producing 12 not-applicable results across six runs. Those skips
are not zeros or failures.

### Independent answer-similarity signals

| Run | Exact/contains | Token F1 | ROUGE-L | Semantic similarity | BERTScore |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 0.5000 | 0.8084 | 0.7777 | 0.8899 | 0.9447 |
| 6 | 0.5000 | 0.7865 | 0.7565 | 0.8841 | 0.9402 |
| 7 | 0.3500 | 0.7376 | 0.6965 | 0.8279 | 0.9143 |
| 8 | 0.3500 | 0.8159 | 0.7859 | 0.8882 | 0.9412 |
| 10 | 0.5000 | 0.7530 | 0.7530 | 0.8650 | 0.9413 |
| 12 | 0.5000 | 0.7270 | 0.7270 | 0.8574 | 0.9346 |

These values are separate signals, not a combined leaderboard. Exact/contains
averaged only 0.50 in the baseline even though all reviewed facts were present.
Correct numeric paraphrases such as `3.800–3.899` and `$15.00 per credit` did
not reproduce a whole accepted phrase, while fact coverage and source accuracy
both scored 1.00. This is a concrete reason not to equate exact matching with
factual correctness.

Run 8 demonstrates the opposite risk in aggregate overlap metrics: its mean
token F1 and ROUGE-L slightly exceeded run 5 even though the position-1 answer
stopped after `Monday, March 23,` and omitted the required year. Per-question
fact coverage caught that failure; a run mean alone could hide it.

### Operational measurements

| Run | Mean latency | Total tokens | Stored pre-fix cost estimate |
| ---: | ---: | ---: | ---: |
| 5 | 2,276.0 ms | 5,480 | $0.001561 |
| 6 | 2,463.6 ms | 5,567 | $0.001667 |
| 7 | 2,382.2 ms | 8,011 | $0.002252 |
| 8 | 2,292.8 ms | 11,094 | $0.003196 |
| 10 | 1,052.8 ms | 4,025 | $0.001586 |
| 12 | 1,518.4 ms | 4,114 | $0.001626 |

Top-k 5 increased total tokens by 46% and top-k 8 by 102% relative to top-k 3
without improving expected-source rank. Gemini 3.1 Flash-Lite reduced mean
latency by 54% and total tokens by 27% relative to the Gemini 2.5 Flash
condition while retaining the tested fact/source/refusal outcomes.

The cost column is retained for auditability but is not an invoice and should
not drive the cross-model conclusion. The historical generator recorded
candidate tokens but did not separately bill hidden thinking tokens, and one
configured generation price pair was shared across model choices. Both issues
are now explicit: thinking tokens are included in future estimates, while
per-model price tables remain future work.

### Advanced matched case

For the hard financial-aid question, runs 5 and 6 produced the same substantive
answer and both retrieved the reviewed source at rank 1. Their advanced results
were also identical:

| Method | Chroma response 23 | MySQL response 28 | Interpretation |
| --- | ---: | ---: | --- |
| LLM judge | 1.0000 | 1.0000 | All applicable 0–4 rubric dimensions were acceptable |
| RAGAS Faithfulness | 1.0000 | 1.0000 | Claims were supported by saved contexts |
| RAGAS Response Relevancy | 0.8748 | 0.8748 | Strong but not perfect question focus |
| RAGAS Context Precision | 1.0000 | 1.0000 | Relevant contexts were highly ranked |
| RAGAS Context Recall | 1.0000 | 1.0000 | Contexts covered the reviewed answer |

Response Relevancy's 0.8748 alongside perfect fact, source, judge, faithfulness,
precision, and recall results demonstrates that metrics address different
questions. It is not evidence that the response was 87.48% factually correct.

### Human calibration

Seven final-study responses received current reviews: all five baseline answers
from run 5 and the two incomplete outputs from runs 7 and 8. The reviewer marked
six responses acceptable and run-7 response 33 needs revision with failure
category `incomplete_answer`.

| Response | Human decision | Selected automatic evidence | Interpretation |
| ---: | --- | --- | --- |
| 21 | Acceptable | Required facts 1.00; semantic 0.909 | Date answer aligned across human and automatic checks |
| 22 | Acceptable | Exact/refusal/semantic 1.00 | Deliberately unsupported question was refused correctly |
| 23 | Acceptable | Token F1/ROUGE-L 0.633; judge/faithfulness/source/facts 1.00 | Correct expanded answer shows why low lexical overlap is not necessarily failure |
| 24 | Acceptable | Exact/contains 0.00; facts 1.00; semantic 0.978 | Correct paraphrase defeated strict accepted-answer containment |
| 25 | Acceptable | Exact/contains 0.00; semantic 0.698; facts 1.00; BERTScore 0.920 | Human and fact-aware checks accepted an answer that one semantic model placed below threshold |
| 33 | Needs revision | Source hit 1.00; facts 0.00; token F1 0.389; semantic 0.584 | Retrieval succeeded, but the generated answer stopped before answering either requested part |
| 36 | Acceptable | Exact/facts 0.00; token F1 0.778; semantic 0.895 | Human accepted the shortened date while strict required-fact checks flagged the omitted year |

This small calibration supports a portfolio interpretation. Expected-source
accuracy correctly diagnoses retrieval but cannot detect incomplete generation.
Required-fact and lexical checks catch omissions but can be stricter than an
overall human acceptability decision. Semantic methods recognize many
paraphrases but can still disagree with a reviewer on exact numeric wording.

## Failure Analysis

Run 7's financial-aid response ended with `typically`; run 8's registration
response ended after the day of the month. In each case, total minus prompt and
visible-answer usage was about 490 tokens, strongly indicating that hidden
thinking consumed almost all of the old 512-token output allocation. Source
retrieval was correct, so this was a generation-budget failure rather than a
retrieval failure.

The corrective change increases the allocation to 2,048, records thinking
tokens and finish reason, rejects incomplete non-STOP results, and includes
thinking tokens in estimated cost. Two August 3 `--no-save` Gemini 2.5 Flash
checks then repeated the affected questions without changing the original runs.
The top-k 5 financial-aid answer completed all requested facts with 1,104 input,
55 visible output, and 1,672 total tokens. The top-k 8 registration answer
completed the full date with finish reason `STOP`, 2,402 input, 25 visible
output, 301 thinking, and 2,728 total tokens. Both passed the non-STOP rejection
guard. Their combined configured cost estimate was $0.0032868. The second call
completed after one short free-tier cooldown.

Two failed runs add operational evidence:

- Run 9 used `gemini-2.5-flash-lite`, which Google reported as unavailable to
  new users. The approved list now uses stable `gemini-3.1-flash-lite`.
- Run 11 reached the 20-request free-tier daily limit for Gemini 2.5 Flash after
  two answers. Its partial output is excluded from completed comparisons. The
  corpus experiment was completed as run 12 against the valid run-10 baseline.

## Findings and Recommendations

1. Use Chroma top-k 3 as the project default for this corpus. It achieved the
   tested retrieval and fact-coverage goals with the smallest context/token
   footprint. Higher top-k did not improve expected-source rank and exposed
   incomplete-output risk in the evaluated code version.
2. Keep MySQL keyword retrieval as a transparent diagnostic baseline. It tied
   Chroma on the five sampled questions, so no quality superiority claim is
   justified. A larger sample is required, especially paraphrase-heavy queries
   with weak lexical overlap.
3. Offer Gemini 3.1 Flash-Lite as the low-latency approved option. Its tested
   source, fact, and refusal outcomes matched the baseline with much lower
   latency. Model pricing and broader quality need a larger, fresh run.
4. Keep the full 27-document corpus as the ordinary default. The 20-document
   focused subset did not improve the tested fact/source/refusal outcomes and
   increased mean latency in this single sample. Category subsets remain useful
   for controlled research and scoped deployments.
5. Use a portfolio of metrics. Required-fact coverage, expected-source accuracy,
   and refusal correctness are strong regression checks for this reviewed data;
   semantic/BERT-style metrics help recognize paraphrases; LLM judge and RAGAS
   should be reserved for sampled diagnosis; human review remains necessary for
   calibrated acceptability claims.
6. Preserve per-question evidence and failed attempts. Run means alone hid an
   incomplete date, and the failed model/quota runs documented deployment risks
   that a success-only report would miss.

## Comparison with Professor Examples

RAGWorks demonstrates a broad top-k/temperature/top-p grid but stores mutable
JSON and uses two binary judge outcomes. StudentCompass demonstrates an Optuna
search over chunk size, top-k, temperature, and top-p; its saved 20-trial
artifact reports best parameters `chunk_size=800`, `top_k=3`,
`temperature=0.737604...`, and `top_p=0.915860...` with objective `0.872814`,
although only 8–10 valid questions appear per saved trial.

This project borrowed the useful principle—compare deliberate parameter
conditions—but kept the required PHP/MySQL stack and added exact-question
matching, immutable attempts, answer-key/context/code/corpus provenance,
explicit skips/failures, 13 evaluator definitions, human-review support, and
portable exports. The bounded one-variable matrix is smaller than the examples'
automated grids; its claims are correspondingly narrower and more auditable.

## Verification

The post-fix provider-free suite contains 70 passing tests. Coverage includes
document parsing, dataset evidence integrity, chunking, vector cleanup,
retrieval contracts, grounded prompts, exact question selection, local and
advanced evaluator behavior, cost/usage rules, baseline matching, exports,
runtime recovery, and frontend regressions. JavaScript syntax, all PHP files,
and `git diff --check` also pass. All 13 PHP files passed syntax checks. A
provider-free browser walkthrough passed all
six views and the two bounded live generation checks confirmed complete output
at the formerly failing top-k settings.

MySQL reused the recovered user-space data directory and all seven migrations.
The current local database contains 12 runs (nine completed and three failed),
51 responses, 316 canonical results, 340 immutable attempts, and eight current
human reviews. Of those, the final completed study contributes six runs,
30 responses, 250 canonical results, and seven current human reviews.

The last provider-free scoring audit found that two valid skipped results per
study run were being offered for repeat execution. Those 12 genuine repeat
attempts remain in the immutable history. The runner now reuses completed and
not-applicable current-version results while leaving failures retryable.

## Limitations

- Five stratified questions are sufficient for a bounded deadline study, not
  statistical generalization across all 50 reviewed questions.
- Only one hard question received all five advanced methods in each of two
  retrieval conditions.
- Seven selected final-study responses were reviewed by one student reviewer.
  Optional dimension-level ratings were left blank, so the evidence supports
  descriptive overall calibration, not inter-rater reliability or quantitative
  dimension-level agreement.
- The 27-document corpus cannot represent enterprise search over thousands or
  millions of documents.
- Gemini free-tier quotas, model retirement, and pricing can change. Provider
  facts and configured prices must be rechecked at execution time.
- Generation cost was not model-specific in historical runs, and RAGAS did not
  expose token usage through its metric result.
- Chunk size, overlap, and embedding model were held fixed because fair changes
  require separately rebuilt indexes.

## Source Notes

- Professor examples: <https://github.com/sjasthi/ragworks> and
  <https://github.com/sjasthi/student-compass> (rechecked August 3, 2026).
- Stable Gemini 3.1 Flash-Lite model:
  <https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite>.
- Current Gemini API pricing:
  <https://ai.google.dev/gemini-api/docs/pricing>.
- [Detailed evaluator contracts and study protocol](evaluation-strategy.md).
- [Complete application-generated evidence and checksums](../data/evaluation/final-study/README.md).
