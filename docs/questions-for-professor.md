# Questions for the Professor

Use this list to clarify the project before building the FP4/FP5 backend work.

## Main Questions

1. Will you provide the Metro State documents for the RAG evaluations, or should
   I collect them myself?

2. If I need to collect the documents, what kinds of Metro State information
   should I look for? For example: admissions, registration, tuition,
   financial aid, academic policies, graduation, course delivery, or advising.

3. How many documents are required for the project?

4. Are specific document formats required, such as PDF, DOCX, TXT, HTML/web
   pages, or PPTX?

5. For model providers, I remember you saying we could use API keys from
   providers such as ChatGPT/OpenAI, Claude, Gemini, etc. Are students expected
   to pay for those API credits out of pocket for development and demonstration,
   or is there any school/course-provided credit?

6. Is the final project expected to use cloud storage, or can uploaded files
   remain in local storage for localhost/class demonstration purposes?

7. Is public deployment required, or is a localhost demo during class/Zoom
   acceptable?

8. For evaluation, is a fixed set of around 50 questions with expected answers
   required?

9. Should the expected answers be written manually from the source documents, or
   may another LLM help generate draft expected answers that I verify?

10. Are other LLMs supposed to evaluate the generated answers, or should the
    project mainly compare generated answers against the fixed expected-answer
    dataset?

11. Which evaluation methods are required? For example: exact/contains match,
    semantic similarity, source accuracy, LLM-as-judge, or RAGAS.

12. Is RAGAS required, or is it optional as an advanced/offline evaluator?

13. Is authentication required, or can this project skip login since it is mainly
    for local demonstration?

14. If some separation is needed, is a simple admin passcode acceptable instead
    of a full user account system?

15. Is ChromaDB required, or may this project store embeddings in MySQL and use
    cosine similarity for the small document set?

16. May the main application stay in PHP/MySQL while optional Python scripts are
    used only for advanced evaluation tools such as RAGAS?

17. For FP3 specifically, is a responsive `index.php` with planning, UX, scope,
    and code-structure documentation enough, or should any forms already be
    functional?

## Short Email Version

Hi Professor,

I reviewed the starter repo and the reference projects. Before I continue into
FP4/FP5, could you clarify a few things?

1. Will you provide the Metro State documents, or should I collect them myself?
   If I collect them, what categories and formats should I use?
2. How many documents are required?
3. Are API credits for providers such as ChatGPT/OpenAI, Claude, or Gemini paid
   by students, or is there any school/course-provided credit?
4. Is cloud storage or public deployment required, or is local file storage and a
   localhost class demo acceptable?
5. Is a fixed set of around 50 evaluation questions with expected answers
   required?
6. Should LLM-as-judge or RAGAS be required, or are simpler metrics such as
   semantic similarity and source accuracy acceptable?
7. Is authentication required, or can the project skip login for a local demo?
8. Is ChromaDB required, or can embeddings be stored in MySQL for this small
   dataset?

Thank you.
