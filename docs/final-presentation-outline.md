# Final Presentation Outline

Target length: 10–12 minutes plus questions. Keep the application open on the
Overview page, with MySQL already started by `scripts/start-local-mysql.ps1`.

## Slide 1 — Problem and Deliverable

- RAG answers can sound correct even when retrieval, facts, or grounding fail.
- The deliverable is a PHP/MySQL evidence workbench, not only a chatbot.
- It compares configurations and evaluation methods over Metro State sources.

Speaker point: “My question was not which metric is universally best. It was
what each method reveals, misses, and costs for a specific decision.”

## Slide 2 — Architecture

```text
27 Metro State documents
  -> Python parsing/chunking
  -> MySQL metadata + 77 chunks
  -> Chroma embeddings
  -> Chroma or MySQL retrieval
  -> grounded Gemini answer
  -> 13 evaluators + human review
  -> MySQL audit trail + JSON/CSV export
```

Mention the required Bootstrap/jQuery, PHP, MySQL, Python, Chroma, and Gemini
stack and server-side secret handling.

## Slide 3 — Gold Standard and Reproducibility

- Dataset v2.0: 50 reviewed questions, 47 answerable and three unanswerable.
- Nine categories; easy, medium, and hard cases.
- Expected answer, source, evidence, accepted variants, and required facts.
- Each run freezes question, corpus, context, code, model, usage, and attempts.

Demo: open Gold Standard and one reviewed question.

## Slide 4 — Controlled Experiment

- Five exact questions: positions 1, 23, 35, 38, and 46.
- Six completed, one-variable conditions; 30 saved responses.
- Variables: retrieval method, top-k 3/5/8, model, and 27 vs 20 documents.
- 250 canonical study results; no evaluator failures in completed runs.

Demo: open Evaluation, choose the baseline, and show the exact-question and
one-variable comparison controls.

## Slide 5 — Retrieval and Core Quality

| Condition | Source rank 1 | Required facts | Refusal |
| --- | ---: | ---: | ---: |
| Chroma k=3 | 4/4 | 1.00 | 1.00 |
| MySQL k=3 | 4/4 | 1.00 | 1.00 |
| Chroma k=5 | 4/4 | 0.75 | 1.00 |
| Chroma k=8 | 4/4 | 0.75 | 1.00 |
| Flash-Lite/full | 4/4 | 1.00 | 1.00 |
| Flash-Lite/subset | 4/4 | 1.00 | 1.00 |

Speaker point: “MySQL tied Chroma on this sample, so I do not claim a retrieval
winner. The evidence supports Chroma k=3 as an efficient default.”

## Slide 6 — Metric Disagreement

- Baseline exact/contains mean: 0.50.
- Baseline required facts and expected source: 1.00 on applicable questions.
- Correct numeric paraphrases failed whole-phrase exact matching.
- Top-k 8 had slightly higher token F1/ROUGE-L than baseline while one answer
  omitted the required year.

Speaker point: “A metric score answers its own narrow question. It is not a
percentage probability that the answer is correct.”

Demo: show the registration or Magna Cum Laude response and its separate metric
cards.

## Slide 7 — Advanced Evaluation

Matched hard financial-aid case for Chroma and MySQL:

- judge: 1.00;
- faithfulness: 1.00;
- response relevancy: 0.8748;
- context precision: 1.00; and
- context recall: 1.00.

Speaker point: “Relevancy was lower even though facts and grounding were
complete. That is useful disagreement, not a vote to average away.”

## Slide 8 — Failure Found by the Research

- Two higher-top-k responses ended mid-sentence.
- Retrieved source was correct; this was not retrieval failure.
- Hidden thinking consumed nearly all of the old 512-token output budget.
- Fix: 2,048-token allocation, finish-reason rejection, thinking metadata, and
  thinking-aware cost estimates.
- Retained old runs as evidence instead of rewriting them.
- Two bounded `--no-save` Gemini checks then returned complete answers at top-k
  5 and 8; combined configured cost estimate: $0.0032868.
- Single-reviewer human calibration marked six of seven sampled responses
  acceptable and the truncated financial-aid response needs revision. The shortened registration
  date was accepted, preserving a real human/strict-fact-check disagreement.

Also mention the retired model name and free-tier quota failures as deployment
lessons.

## Slide 9 — Performance and Recommendations

- Chroma k=3: 5,480 total tokens, 2,276 ms mean latency.
- Chroma k=8: 11,094 tokens with no source-rank improvement.
- Gemini 3.1 Flash-Lite: 4,025 tokens and 1,053 ms mean latency while retaining
  tested fact/source/refusal outcomes.

Recommendations:

- Chroma top-k 3 default;
- MySQL as diagnostic baseline;
- Flash-Lite as low-latency option;
- full corpus for normal use, subsets for controlled/scoped work; and
- local regression metrics plus sampled judge/RAGAS and human review.

## Slide 10 — Limits and Next Work

- Five-question bounded sample, not statistical proof over all 50 questions.
- One matched hard case received all advanced metrics.
- Seven selected responses were reviewed by one student reviewer; this is
  descriptive calibration, not inter-rater evidence.
- Local 27-document behavior cannot be generalized to enterprise scale.
- Future: larger exact sample, per-model price table, rebuilt
  chunk/embedding variants, and background batch execution.

Close with: “The main result is a reproducible way to make narrow, auditable
claims—and to preserve disagreement and failure instead of hiding them.”

## Live Demo Order

1. Overview health/readiness.
2. Documents: 27 sources and categories.
3. Chat: preview ranked evidence without a paid call.
4. Gold Standard: one source-verified case.
5. Evaluation: run 5 and its exact five-question coverage.
6. Score cards: exact match versus required facts/source accuracy.
7. Compare Runs: run 5 versus 6, then 5 versus 8.
8. Use the browser's Export JSON/CSV controls; keep private working notes off
   screen.
9. Show the seven saved human reviews and the response-33 needs-revision case;
   state that automatic results and human decisions remain separate evidence.

## Pre-Demo Checklist

```powershell
.\scripts\start-local-mysql.ps1
.\.venv\Scripts\python.exe -m unittest discover -s tests
node --check assets\js\app.js
php -l index.php
```

- Confirm `api/health.php` reports ready.
- Do not regenerate study answers during the presentation.
- Keep API keys and `.env` off screen.
- Use saved runs and exports so the demo is resilient to quota/network issues.
