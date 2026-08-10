# Final Capstone Presentation Script

**Andrew Xiong · ICS 499 · LLM RAG Evaluation Project**

Target length: 10–12 minutes, plus questions. This script can be used for a
live Zoom presentation or a recorded submission. Bracketed text is a visual or
demo cue and does not need to be read aloud.

Before recording, open the repository README and the application Overview page.
Use saved runs and source preview; do not make paid provider calls during the
presentation.

## Opening

[Show the repository README and project title.]

Hello Professor Jasthi. My name is Andrew Xiong, and this is my ICS 499 capstone,
the LLM RAG Evaluation Project.

The project began with a practical question: how can we tell whether a
Retrieval-Augmented Generation response is actually good? A generated answer
can sound confident even when the system retrieved the wrong source, omitted a
required fact, used unsupported information, or should have refused the
question.

My final deliverable is therefore more than a chatbot. It is a PHP and MySQL
research workbench for running controlled RAG experiments, applying different
evaluation methods, preserving evidence, and explaining what each method can
and cannot tell us.

The central research question is: what is the best way to evaluate a RAG
response? My conclusion is that there is no single universally best score. The
best method depends on whether the decision concerns retrieval, factual
completeness, grounding, refusal behavior, semantic similarity, cost, or human
acceptability.

## 1. Final Application and Architecture

[Show the Overview screenshot or application Overview page.]

The submitted application uses the required course stack. The frontend uses
HTML, CSS, Bootstrap, and jQuery. PHP provides the web application and validated
JSON endpoints. MySQL stores documents, questions, runs, responses, evaluation
results, human reviews, and provenance. Python performs document extraction,
chunking, retrieval, grounded generation, and evaluation. ChromaDB provides
vector retrieval, and Gemini is the configured answer and judge provider.

The bundled knowledge base contains 27 Metro State documents in eight
categories. Python converts them into 77 chunks using a chunk size of 800 and
an overlap of 100. The chunks are stored relationally in MySQL and embedded in
Chroma using the local `all-MiniLM-L6-v2` model.

At question time, the application can retrieve with Chroma vector search or a
genuine MySQL FULLTEXT keyword baseline. Retrieved evidence is sent through one
shared grounded-answer pipeline. This same pipeline is used by ordinary Chat
and controlled evaluation runs, preventing the test path from silently using a
different implementation.

## 2. What Was Implemented Beyond the Initial RAG Core

[Move through Documents, Chat, Gold Standard, Evaluation, and Compare Runs.]

The early project core could ingest the bundled text files, retrieve chunks,
and generate a grounded answer. The final application adds the surrounding
workflows required to make that core usable and researchable.

The Documents page now supports browser administration for TXT, text-based PDF,
and DOCX files. A user can search, filter, upload, replace, delete, or restore
the bundled corpus. Same-name replacement is staged safely: the new document
must ingest successfully before the old MySQL and Chroma records are removed.
Vector deletion is read back and verified so a stale deleted source cannot
continue appearing in Chat.

Chat includes approved model, retrieval, top-k, temperature, and top-p controls,
but hides them under progressive disclosure for ordinary use. A provider-free
source preview lets a reviewer inspect retrieval without spending API quota.

The Gold Standard page provides a reviewed answer key. Evaluation creates
bounded tests, preserves answers and exact contexts, applies selected methods,
supports human review, and exports JSON or CSV. Compare Runs only presents
question-matched and evaluator-matched evidence, so unrelated run averages are
not treated as a valid experiment.

## 3. Gold Standard and Reproducibility

[Open Gold Standard and expand one reviewed question.]

Dataset version 2.0 contains 50 reviewed questions across nine categories:
47 answerable questions and three deliberately unanswerable cases. The set
includes easy, medium, and hard examples.

Each answerable question stores the expected answer, expected source,
source-verified evidence, accepted variants, and required facts. The
unanswerable questions define the exact safe-refusal behavior. The original
25-question version remains tracked so older runs are not assigned a rewritten
answer key.

Reproducibility is a major part of the application. A new run freezes its
dataset and question snapshots, ordered retrieved contexts, document manifest
and hashes, retrieval algorithm, model settings, source-tree and dependency
versions, usage, estimated-cost status, evaluator attempts, and failures.
Historical failures are preserved rather than overwritten. Each completed run
can also be exported from the browser, and the six final-study exports are
committed to GitHub with SHA-256 checksums.

## 4. Controlled Final Study

[Show Evaluation and the guided baseline/comparison controls.]

The final experiment used the same ordered five-question sample for every
condition. The sample covered academic calendar, an unanswerable false premise,
financial aid, graduation, and tuition and fees. It included easy through hard
questions, numeric distractors, multi-fact answers, and refusal behavior.

Run 5 was the reference condition: Chroma retrieval, top-k 3, Gemini 2.5 Flash,
and all 27 documents. Run 6 changed only retrieval to MySQL. Runs 7 and 8
changed only top-k to 5 and 8. Run 10 changed only the answer model to Gemini
3.1 Flash-Lite. Run 12 compared a focused 20-document, four-category subset
against the matching Flash-Lite baseline.

This produced six completed conditions and 30 saved responses. The application
stored 250 canonical evaluator results: 238 completed and 12 correctly skipped
as not applicable. The skipped results came from applying source and
required-fact checks to the unanswerable case; they are not zeros or evaluator
failures.

## 5. Evaluation Portfolio

[Show the evaluator groups and separate score cards.]

The project implements 13 named automatic methods plus a separate human-review
workflow.

The eight local methods are accepted-answer matching, required-fact coverage,
token F1, ROUGE-L, embedding semantic similarity, BERTScore,
expected-source accuracy, and refusal correctness. These are repeatable and can
screen the full saved set without provider calls.

The five advanced methods are a versioned structured LLM judge and four RAGAS
dimensions: Faithfulness, Response Relevancy, Context Precision, and Context
Recall. They are guarded because they can consume external quota and cost.
They evaluate already-saved answers and contexts rather than regenerating an
answer.

The interface never averages these unlike methods into one unexplained grade.
Every method exposes its comparison target, scale, threshold, inputs,
limitations, and execution status. Human decisions are also stored separately
from automatic results instead of being converted into another hidden metric.

## 6. Results and Metric Disagreement

[Show run 5 results and Compare Runs for runs 5 and 6.]

For all six completed conditions, the expected source was retrieved at rank one
for all four answerable questions, and the unanswerable case was refused
correctly.

The Chroma top-k 3 baseline and MySQL top-k 3 both achieved complete required
fact coverage on this sample. Therefore, I do not claim that one retrieval
method universally defeated the other. The evidence supports Chroma top-k 3 as
the efficient project default, while MySQL remains a useful transparent
diagnostic baseline.

Metric disagreement was one of the most useful findings. Baseline strict
accepted-answer matching averaged only 0.50 even though required facts and
expected-source accuracy were complete on every applicable case. Correct
numeric paraphrases did not reproduce an entire accepted phrase, so strict
matching failed while fact-aware and source-aware checks passed.

The opposite problem also occurred. The top-k 8 condition had slightly higher
mean token F1 and ROUGE-L than the baseline even though one response omitted a
required year. Per-question fact coverage exposed that omission. This shows why
a run mean or one similarity score cannot be treated as the probability that an
answer is correct.

## 7. Advanced and Human Evidence

[Show the hard financial-aid response and its advanced results.]

The matched Chroma and MySQL financial-aid answers received the same advanced
results: 1.00 from the structured judge, Faithfulness, Context Precision, and
Context Recall, with Response Relevancy at 0.8748.

That lower relevancy result did not mean the answer was 87.48 percent factually
correct. The facts and grounding were complete; relevancy was measuring how
directly the response focused on the question. This is useful disagreement,
not a reason to average all scores together.

Seven selected final-study responses also received current human reviews. Six
were marked acceptable and one was marked needs revision. Because there was
one student reviewer and no dimension-level ratings, I describe this as a
small calibration sample rather than inter-rater evidence.

## 8. Failure Found and Fixed

[Show response 33 or the failure-analysis section of the report.]

The research process found a real generation defect. Two higher-top-k answers
ended mid-sentence even though retrieval found the correct source. The stored
usage showed that hidden model thinking had consumed almost all of the old
512-token output allocation.

The fix increased the allocation to 2,048 tokens, rejects non-STOP finish
reasons, records finish and thinking metadata, and includes thinking tokens in
future cost estimates. Two bounded no-save checks repeated the affected top-k 5
and top-k 8 questions and produced complete answers. The original incomplete
responses were not rewritten; they remain part of the failure evidence.

This example also shows why source accuracy alone is not enough. Retrieval was
successful, but generation was incomplete. Required-fact checks and human
review caught the problem.

Two failed study attempts recorded additional deployment lessons: one retired
Gemini model name was removed from the approved list, and one partial run hit a
free-tier request limit. Failed runs are excluded from completed comparisons
but retained in the audit trail.

## 9. Performance and Recommendations

[Show the report performance table or Compare Runs findings.]

Chroma top-k 3 used 5,480 total tokens with mean latency of 2,276 milliseconds.
Top-k 8 used 11,094 tokens—approximately double—without improving expected
source rank. This supports top-k 3 as the default for the tested corpus.

Gemini 3.1 Flash-Lite retained the tested source, fact, and refusal outcomes
while reducing mean latency to 1,053 milliseconds and total tokens to 4,025.
That makes it the supported low-latency option, but the five-question sample is
too small for a universal model-quality claim.

My recommendations are to use Chroma top-k 3 for ordinary semantic retrieval,
retain MySQL as a diagnostic baseline, keep the full corpus as the normal
default, and use category subsets only for controlled or scoped work. For
evaluation, use local metrics for broad regression screening, sampled judge and
RAGAS methods for diagnosis, and human review for ambiguous acceptability
decisions.

## 10. Repository Readiness, Limitations, and Next Work

[Return to the README and show the reviewer links and green Actions run.]

The final repository now contains the complete study report, presentation
outline, this script, interface screenshots, six application-generated JSON
exports, checksums, setup instructions, and categorized technical and historical
documentation.

The provider-free suite contains 70 tests. GitHub Actions does more than static
checking: it creates a fresh MySQL service and Chroma directory, applies the
schema and migrations, ingests all 27 documents into 77 chunks, seeds all 50
questions and 13 evaluators, starts PHP, and verifies the application APIs and
ranked source preview. No provider key or paid call is used. PHP and Python also
share the same rule that explicit deployment variables override a local `.env`
file, so CI safety flags cannot be silently replaced by local settings.

The limitations are explicit. The final automated study uses five stratified
questions, not all 50. Only one hard case per retrieval condition received all
advanced methods. Human review is a seven-response, single-reviewer sample. The
27-document corpus does not represent enterprise scale, and chunk size,
overlap, and embedding model were held fixed because fair changes require
separate rebuilt indexes.

Post-capstone research could expand the exact-question sample, add independent
reviewers, repeat model runs, rebuild chunk and embedding variants, and test
multimodal documents, conversation memory, user isolation, and bounded agentic
retrieval. Those features are documented as future work and are not claimed as
part of the submitted application.

## Closing

[End on the Overview page or final report.]

The main result of this capstone is a working RAG evaluation application and a
reproducible method for making narrow, auditable claims. Instead of hiding
failures or forcing unlike scores into one number, the system preserves the
question, source, answer, context, evaluator behavior, human decision, and
configuration needed to understand each result.

For this tested Metro State corpus, the evidence supports Chroma top-k 3 as the
efficient default, MySQL as a useful diagnostic baseline, and a portfolio of
fact, source, semantic, judged, and human evidence rather than one universal
metric.

Thank you for reviewing my project. The complete code, final report, raw study
exports, limitations, and future research plan are available from the
repository README.

## Optional Live Demonstration Order

If time permits after the script:

1. Show Overview readiness and the 27-document/77-chunk counts.
2. Show Documents administration and supported file types.
3. Preview ranked Chat sources without a provider call.
4. Expand one source-verified Gold Standard question.
5. Open run 5 in Evaluation and show its five exact questions.
6. Contrast accepted-answer matching with required facts and source accuracy.
7. Compare runs 5 and 6, then runs 5 and 8.
8. Show response 33 and its needs-revision human review.
9. Show JSON/CSV export and the tracked evidence directory.

## Likely Questions and Short Answers

**Why did you evaluate only five questions when the dataset contains 50?**

The five-question set was a bounded, stratified controlled sample chosen to
cover answerability, difficulty, four subject areas, numeric distractors, and
multi-fact behavior. I preserve the 50-question reviewed dataset for broader
future experiments and explicitly avoid claiming statistical generalization.

**Why not select one best metric?**

The metrics have different targets. Source accuracy diagnoses retrieval,
required facts diagnose omissions, semantic methods recognize paraphrases,
RAGAS and the judge provide sampled grounding or rubric evidence, and human
review addresses acceptability. Combining them without a validated weighting
would hide those differences.

**Why keep both Chroma and MySQL retrieval?**

Chroma supports semantic matching, while MySQL provides a transparent lexical
baseline. They tied on this small sample, which is useful evidence that the
project should not claim a universal retrieval winner.

**What was the most important defect you found?**

The higher-top-k study exposed incomplete answers caused by hidden thinking
consuming the old output budget. Retrieval was correct, so the stored evidence
helped isolate generation as the failing stage and verify the targeted fix.

**Can another reviewer reproduce the paid study exactly?**

The repository preserves the code, corpus, question snapshots, configuration,
contexts, results, attempts, raw exports, and checksums. Provider behavior,
quota, pricing, and model versions can change, so exact future model text is not
guaranteed. The committed exports make the completed historical evidence
inspectable without repeating paid calls.
