# FP3-FP10 Project Plan

## Project Deadline

The project must be completed by August 3, 2026. Each iteration should produce a
working, reviewable increment rather than leaving integration until the final
iteration.

## Project Responsibilities

The roles below organize the project work by responsibility area. They can be
assigned to people if collaborators are added, or used as planning categories if
the work remains centralized.

| Role | Primary responsibilities |
| --- | --- |
| Project coordinator | Iteration planning, meeting notes, requirements, professor questions |
| Front-end developer | Bootstrap interface, accessibility, charts, browser behavior |
| Back-end developer | PHP services, validation, database access, API integration |
| RAG/evaluation developer | Chunking, retrieval, model calls, evaluation methods |
| Test/documentation owner | Test data, acceptance tests, setup guide, final report |

Each iteration should include a short review before committing or submitting
work.

## Iteration Milestones

| Iteration | Planned milestone | Completion evidence |
| --- | --- | --- |
| FP3 | Finalize requirements, project plan, UX direction, code structure, and starter page | `requirements.md`, FP3 documents, responsive `index.php` |
| FP4 | Establish application shell and database foundation | Shared layout, environment configuration, MySQL schema, database connection test |
| FP5 | Complete the core RAG round trip and first web workflow | MySQL/ChromaDB ingestion, retrieval, grounded Gemini answer, PHP Ask page, stored sources |
| FP6 | Add document administration and multi-format ingestion | Browser upload/list/replace flow, TXT/PDF/DOCX extraction, ingestion status and regression tests |
| FP7 | Create the research dataset and baseline metrics | At least 25 reviewed questions, managed expected answers/sources, normalized match, semantic, source, refusal and latency results |
| FP8 | Compare advanced metrics and controlled experiments | Faithfulness/relevance or LLM-judge metrics, metric-disagreement analysis, retrieval and corpus-size/composition experiments |
| FP9 | Complete research dashboard, interpretation, and system testing | Metric explanations, comparisons, failure analysis, preliminary findings, accessibility/security checks |
| FP10 | Stabilize and deliver the research application | Reproducible experiment guide, findings and limitations, presentation, final report, tagged release |

## Revised Research Direction After FP5 Review

The application is the instrument used to run controlled RAG experiments. The
final value of the project is not only the working question-answer interface;
it is the evidence and explanation produced from comparing evaluation methods.

The research should determine what each metric is specifically useful for,
where automated metrics agree or disagree, and which combination provides a
defensible evaluation of retrieval, correctness, grounding, and refusal
behavior. The number of evaluation questions should be justified by coverage;
at least 25 reviewed questions is the initial target rather than a fixed ratio
between questions and documents.

The professor also emphasized that real organizations may search hundreds to
millions of documents. The local project is not expected to reproduce that
scale. It should run a controlled collection-size or collection-composition
experiment and clearly state the limits of generalizing from the local corpus.

See `docs/research-plan.md` for the detailed experiment design and FP6-FP10
implementation sequence.

## Working Agreement

- Review the iteration scope at the start of each iteration.
- Push completed, runnable checkpoint work to `main`, following the professor's preferred workflow.
- Never commit API keys, passwords, uploaded private documents, or `.env` files.
- Record unresolved scope questions and ask the professor early.
- Demonstrate the current working increment at each iteration review.

## FP3 Exit Criteria

- Requirements are updated based on professor feedback.
- FP3-FP10 milestones have owners and dates.
- Stakeholders and their primary workflows are documented.
- The proposed code structure and conventions are documented.
- `index.php` loads successfully and is responsive on mobile and desktop.
- The FP3 files are committed and available in the GitHub repository.
