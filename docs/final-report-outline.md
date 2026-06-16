# Final Report Outline

This document is a working outline for the final project report. It should be
filled in gradually as implementation and evaluation work is completed.

The final report does not need to be a formal research paper unless the
professor requires one. Its purpose is to explain what was built, how it was
tested, what the evaluation results showed, and what conclusions can be drawn.

## 1. Project Summary

Explain the project in plain language.

Planned content:

- Project name.
- Problem being solved.
- Why RAG evaluation matters.
- Why Metro State documents were used.
- Main project goal.

Draft summary:

> This project builds a PHP/MySQL web application for evaluating
> Retrieval-Augmented Generation configurations using Metro State documents.
> The goal is to compare how different RAG settings affect answer quality,
> source grounding, and usefulness for decision-making.

## 2. Final Scope

Summarize what the final application includes.

Planned content:

- Document management.
- Question-answering page.
- Retrieved source display.
- Evaluation question set.
- Evaluation runner.
- Results dashboard or comparison table.
- Report/recommendation page.

Also mention what was intentionally out of scope:

- Production-grade deployment beyond the course hosting/demo requirement.
- Full authentication system, unless required.
- Large-scale vector infrastructure, unless required.
- Training a custom LLM.

## 3. Technology Stack

Document the actual stack used.

Planned content:

- Frontend: HTML, CSS, JavaScript, jQuery, Bootstrap.
- Server: PHP.
- Database: MySQL.
- LLM provider: selected provider or providers.
- Embedding provider/model.
- Optional Python scripts, if used for RAGAS or advanced evaluation.

Also explain where secrets are stored:

- `.env` for local API keys and database credentials.
- `.env.example` committed with placeholders only.

## 4. System Architecture

Explain the application flow.

Planned content:

```text
Metro State documents
-> text extraction
-> chunking
-> embeddings
-> MySQL storage
-> question embedding
-> similarity retrieval
-> LLM answer generation
-> answer + sources
-> evaluation scoring
-> results dashboard
```

Include a diagram if useful.

## 5. Data Sources

List the Metro State documents used.

Planned content:

- Document title.
- Source URL or file source.
- Document type.
- Category.
- Date accessed.
- Notes about cleaning or conversion.

Questions to answer:

- Were documents provided by the professor?
- Were documents collected from public Metro State pages?
- Were any documents converted into text files?
- Were older versions included to test document replacement?

## 6. Evaluation Dataset

Describe the fixed question set.

Planned content:

- Number of questions.
- Categories covered.
- Expected answer source.
- Whether unanswerable questions were included.
- How expected answers were created and verified.

Example table:

| Question | Expected Answer | Expected Source | Category |
| --- | --- | --- | --- |
| When does Fall 2026 registration begin? | ... | registration document | Registration |

## 7. RAG Configurations Tested

Explain which settings were compared.

Planned content:

- Chunk size values.
- Chunk overlap values.
- Top-k values.
- Temperature values.
- Provider/model values, if compared.
- Prompt variations, if compared.
- Retrieval/storage option, such as MySQL baseline versus ChromaDB vector search.

Example:

| Config | Chunk Size | Overlap | Top-K | Temperature | Model |
| --- | ---: | ---: | ---: | ---: | --- |
| A | 500 | 100 | 3 | 0.0 | Provider/model |
| B | 800 | 100 | 5 | 0.0 | Provider/model |

## 8. Evaluation Methods

Explain the metrics used.

Likely methods:

- Exact or contains match.
- Semantic similarity.
- Source accuracy.
- Latency.
- Estimated API cost.
- LLM-as-judge, if implemented.
- RAGAS or RAGAS-style metrics, if implemented.

For each method, explain:

- What it measures.
- Why it was used.
- Limitations.

## 9. Test Plan

List what was tested besides the RAG scoring itself.

Functional tests:

- Document upload/import works.
- Chunks are created.
- Embeddings are stored.
- Questions retrieve chunks.
- Answers include sources.
- Evaluation runs store results.
- Dashboard displays results.

Negative/error tests:

- Empty question.
- Unsupported document type.
- Missing API key.
- Missing database connection.
- Unanswerable question.
- Document replacement.

Security/configuration tests:

- API keys are not committed.
- API calls are server-side.
- Database queries use prepared statements.
- Uploaded files are restricted.

Usability/accessibility checks:

- Forms have labels.
- Results are readable.
- Navigation works on mobile.
- Color is not the only indicator of pass/fail.

## 10. Evaluation Results

Fill this section after evaluation runs are implemented.

Planned content:

- Summary table.
- Best configuration.
- Worst configuration.
- Average answer score.
- Source accuracy.
- Latency.
- Cost estimate.
- Examples of successful answers.
- Examples of failures.

Example table:

| Config | Avg Answer Score | Source Accuracy | Avg Latency | Estimated Cost | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| A | TBD | TBD | TBD | TBD | TBD |
| B | TBD | TBD | TBD | TBD | TBD |

## 11. Findings

Explain what the results mean.

Possible finding categories:

- Which chunk size worked best.
- Whether higher top-k helped or hurt.
- Whether temperature affected consistency.
- Whether retrieval or generation caused most failures.
- Whether source accuracy aligned with answer accuracy.
- Whether LLM-as-judge agreed with simpler metrics.

## 12. Recommendations

Translate the findings into practical advice.

Example structure:

- Recommended default configuration.
- When to use a different configuration.
- Which evaluation method was most useful.
- What should be improved next.

## 13. Limitations

Be clear about project constraints.

Possible limitations:

- Small document set.
- Limited number of evaluation questions.
- API cost limited experiment size.
- Metrics do not perfectly match human judgment.
- Some expected answers may require manual review.
- Localhost or course-hosted demo rather than production deployment.

## 14. Future Work

Possible enhancements:

- Add more documents.
- Add more provider comparisons.
- Add RAGAS if not implemented.
- Add ChromaDB if larger scale is needed.
- Add better document parsing.
- Add charts and report export.
- Add authentication only if deployment requires it.

## 15. Final Demo Script

Use this for the final presentation.

1. Show project overview.
2. Show document list.
3. Ask a Metro State question.
4. Show generated answer and retrieved sources.
5. Show evaluation question set.
6. Show evaluation results.
7. Compare two configurations.
8. Explain the best configuration.
9. Explain limitations and next steps.

## 16. Final Submission Checklist

- Application runs locally.
- README has setup instructions.
- `.env.example` is present.
- Real `.env` is not committed.
- Database schema is included.
- Sample data or seed instructions are included.
- Final scope is documented.
- Evaluation results are documented.
- Final report is complete.
- Screenshots or demo notes are ready.
- GitHub repo link is submitted.
