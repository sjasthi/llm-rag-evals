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
| FP5 | Implement Metro State document management | Upload/list/delete workflow, metadata persistence, sample public documents |
| FP6 | Build the baseline RAG pipeline | Text extraction, chunking, embeddings, retrieval, question-answer page with sources |
| FP7 | Create the evaluation test set and baseline metrics | Managed questions/expected answers, exact match and semantic similarity results |
| FP8 | Add advanced evaluation and comparison features | LLM-as-judge or RAGAS-style metrics, configuration comparison, stored runs |
| FP9 | Complete dashboard, reports, and system testing | Charts/tables, recommendations, accessibility/security checks, resolved defects |
| FP10 | Stabilize and deliver the final application | Deployment guide, final demo data, presentation, final report, tagged release |

## Working Agreement

- Review the iteration scope at the start of each iteration.
- Work on feature branches and merge only runnable changes.
- Never commit API keys, passwords, uploaded private documents, or `.env` files.
- Record unresolved scope questions and ask the professor early.
- Demonstrate the current working increment at each iteration review.

## FP3 Exit Criteria

- Requirements are updated based on professor feedback.
- FP3-FP10 milestones have owners and dates.
- Stakeholders and their primary workflows are documented.
- The proposed code structure and conventions are documented.
- `index.php` loads successfully and is responsive on mobile and desktop.
- The FP3 files are committed and ready to push when repository access is available.
