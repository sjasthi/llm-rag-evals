# Frontend-First Workflow and July 20 Requirements

> **Status:** Historical requirements and implementation record. The described
> workflow is implemented; current screenshots and reviewer links are in the
> README.

## Product position

The deployed user is assumed to have no source-code, terminal, or database
access. PHP and Python remain implementation details behind browser actions.
The main navigation now describes user tasks:

1. **Overview** shows active documents, categories, chunks, gold-standard
   questions, and evaluator count.
2. **Chat** answers an arbitrary question with recommended defaults. Approved
   model/retrieval/generation controls remain available in a collapsed Advanced
   settings panel for research comparisons.
3. **Documents** administers the active retrieval corpus.
4. **Gold Standard** reviews questions, expected answers, expected evidence,
   required facts, and answerability labels.
5. **Evaluation** creates bounded tests, scores saved answers, and inspects the
   generated answer, reference, evidence, and method results.

The header begins in a neutral checking state and calls a read-only health
endpoint. It reports either application-data readiness or a concise
retry/contact-administrator state. Infrastructure names and setup steps stay in
operator documentation rather than end-user error copy.

## Document lifecycle

The active index is incremental. Rebuilding unrelated documents is unnecessary:

The upload form explicitly distinguishes storage from indexing. Pictures and
charts remain in an active source file, but the submitted ingestion path indexes
only extracted text; scanned pages without a text layer require a future OCR or
multimodal workflow.

| User action | MySQL | ChromaDB | Source files |
| --- | --- | --- | --- |
| Add Doc 51 | Insert Doc 51 and its chunks | Embed/upsert only Doc 51 chunks | Store the upload |
| Delete Doc 49 | Delete Doc 49; live chunks cascade | Delete vectors filtered by Doc 49 source path | Delete uploads; retain bundled seed files for recovery |
| Replace Doc 48 | Ingest the new copy, then delete the previous active record | Upsert new vectors and delete old source vectors | Replace uploaded storage after successful ingestion |
| Delete all | Delete all active document/chunk rows | Delete all collection records | Delete uploads; retain bundled seed files for recovery |
| Restore bundled | Upsert all tracked starting documents/chunks | Replace vectors for each bundled source | Read retained bundled files; preserve uploads |

The visible filename is now a replacement identity for browser ingestion. If a
new file has the same name as an indexed file, the browser stops and asks the
user to choose **Replace existing** or **Cancel upload**. After replacement is
confirmed, the new version is validated, parsed, chunked, and embedded first.
Only after success are the previous active document, chunks, and vectors
removed. Vector deletion is read back and verified before the old database row
is removed; a stale vector now fails visibly instead of remaining available to
Chat source preview. Any Chat answer/source preview already visible in the
browser is also cleared after add, replace, delete, or delete-all succeeds; the
user must retrieve again against the current corpus. The controlled verification used two
different files named `frontend_replacement_probe.txt`: chunk count changed from
one to two, only one active same-name record remained, and cleanup restored the
corpus to 27 documents and 77 chunks.

The Documents action **Restore bundled sources** runs that retained-source
recovery through the browser. It adds or refreshes the complete starting
collection under the current chunk/embedding settings without deleting any
separately uploaded source.

Chroma supports record `upsert` by ID and `delete` by IDs or metadata filters,
which is why incremental source updates do not require re-embedding the complete
corpus: <https://docs.trychroma.com/reference/python/collection>.

## Evaluation lifecycle

An evaluation run contains saved answers and the exact retrieved contexts used
for those answers. The page deliberately separates two actions:

- **New test run** sends reviewed Gold Standard questions through the shared
  retrieval-and-generation pipeline. The browser selects an approved model,
  retrieval method, top-k, temperature, top-p, source collection, and a bounded
  exact reviewed-question set, then previews model calls and estimated cost before
  generation. It offers a quick test, a labeled controlled baseline, or a
  comparison with a completed baseline. Comparison mode copies the baseline,
  fixes the same ordered questions, locks unchanged controls, and requires the
  researcher to vary exactly one setting. New answers are saved and receive
  the local eight scores automatically.
- **Score saved answers** never regenerates text. It provides two bounded modes:

- **All 13 methods · one selected answer:** eight local methods plus LLM judge
  and four RAGAS metrics. The selected question's exact saved-answer record is
  sent to the backend; the first response is never chosen implicitly.
  Completed active-version results are reused unless the user explicitly
  requests replacement. Provider calls are preflighted and capped.
- **Local 8 methods · full run:** all provider-free baseline metrics are applied
  across every saved response in the selected run.

Each answered-question row also has a direct **Evaluate** action. It selects
that exact saved answer, switches to the all-13 scope, and runs the call/cost
preflight. The user then confirms **Apply scores**. This extra confirmation is
intentional because up to five methods may call the configured evaluator
provider.

The Evaluation summary includes a study checklist for reviewed Gold Standard
coverage, a controlled baseline, valid question/evaluator-matched comparison
rows, sampled human review, and portable exports. It points the user to the
next missing action rather than requiring a database query or documentation
cross-check.

The page also states the recommended evaluator portfolio: run transparent local
checks across every response, apply the LLM judge and RAGAS to representative,
difficult, or failing cases, and use human review to calibrate disagreements.
This answers “which evaluator is better?” by purpose instead of inventing one
universal grade from unlike measurements.

A goal-first selector makes that choice concrete inside the browser. It maps
correctness/completeness, grounding, retrieval, relevance, refusal, overall
confidence, and low-cost regression needs to a primary method, complementary
evidence, a limitation, and whether reviewed Gold Standard data is required.
The Gold Standard page explains the same dependency from the answer-key side,
and Compare Runs exposes the current bounded recommendation with its study
scope instead of requiring a report to explain the conclusion.

The scoring preflight reports saved answers, methods to apply, results to reuse,
external applications, and estimated cost before execution. Evaluation does not
regenerate the saved answer. A new retrieval/model configuration requires a new
controlled run so its answer and contexts are not confused with old evidence.

Database primary keys are implementation details. The browser labels answers
as `Question 1 of 3`, while response/run IDs appear only inside expandable
technical provenance. Completed tests are listed first. Interrupted historical
attempts are collapsed under **Archived interrupted attempts** and explicitly
identified as audit history rather than unfinished current work. A completed
test with the strongest existing human-review and automatic-evaluation coverage
opens first.

Every evaluator card shows the selected answer's isolated score beside the
cumulative mean for that same evaluator across all completed saved tests. An
expandable run table also shows the current-test mean and all-test mean. These
remain separate values. No cumulative 13-metric grade is shown because the
methods measure different dimensions, have different applicability, and
sometimes lack a numeric score.

## Metric dependency map

All metrics evaluate evidence after the answer has been generated. None selects
retrieved chunks or generates the answer.

| Method group | Gold-standard dependency | Main inputs |
| --- | --- | --- |
| Eight local metrics | Required | Generated answer plus expected answer, accepted variants, required facts, expected source, or answerability label |
| LLM judge | Required in this project | Question, response, expected answer/evidence/facts, answerability, retrieved chunks |
| RAGAS Faithfulness | Not required | Question, response, retrieved chunks |
| RAGAS Response Relevancy | Not required | Question and response |
| RAGAS Context Precision | Required | Question, expected answer, retrieved chunks |
| RAGAS Context Recall | Required | Question, expected answer, retrieved chunks |

Reference-free does not mean provider-free: both reference-free RAGAS methods
still use model-backed evaluation.

## How recommended parameters should be chosen

Ordinary chat users should normally ask a question and keep recommended
defaults. Researchers determine those defaults through offline experiments:

1. Freeze one reviewed dataset and corpus version.
2. Choose a baseline configuration.
3. Change one controlled variable, such as retrieval method or top-k.
4. Run the same gold-standard questions through each configuration.
5. Compare the same evaluator on the same questions, including failure,
   latency, token, and cost evidence.
6. Inspect disagreements and calibrate a representative sample with human
   review.
7. Recommend a configuration for a stated use case rather than claiming a
   universal best setting.

The parameters are not all varied in the same way:

| Parameter | Safe comparison method | Reason |
| --- | --- | --- |
| Retrieval method | New test run | Vector and keyword retrieval can use the same current index. |
| Top-k | New test run | It changes how many existing chunks are supplied to the model. |
| Model, temperature, top-p | New test run | They change generation while preserving the corpus. |
| Chunk size and overlap | Separate corpus/index variant, then new test run | They change the chunks themselves, so the documents must be re-chunked and re-embedded consistently. |
| Embedding model | Separate corpus/index variant | Existing vectors are not comparable after the embedding space changes. |

For a first optimization pass, use all reviewed questions with a fixed model,
chunking, and temperature; compare vector versus keyword retrieval and top-k 1,
3, and 5. Select candidates using a metric profile: source accuracy/context
precision for retrieval, fact coverage/recall for completeness,
faithfulness/judge/human review for answer support, plus latency and cost. Then
test generation settings on the strongest retrieval candidates. This keeps the
experiment interpretable and avoids treating thirteen unlike measurements as
one arbitrary objective.

This matches current evaluation practice: LangSmith describes offline
evaluation as running a target over a curated dataset with evaluators and then
comparing experiments, and RAGAS separates evaluation datasets from experiment
results. See <https://docs.langchain.com/langsmith/evaluation> and
<https://docs.ragas.io/en/stable/concepts/datasets/>.

## Remaining scale work

The browser can now launch a bounded synchronous test without terminal access
and download any saved test as JSON or long-form CSV. A full grid across models,
retrieval methods, top-k values, temperatures, and all 50 reviewed v2.0
questions still needs a persistent background job queue, rate-limit-aware
scheduling, progress/cancellation, and resumable retries. The current browser
preflight, bounded launcher, and immutable attempts are the foundation for it.
