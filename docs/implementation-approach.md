# Recommended Implementation Approach

## What to Reuse From the Reference Projects

The reference repositories should be treated as examples of workflows and data,
not as codebases to copy directly. Both use React and Flask, while this project
requires Bootstrap, PHP, and MySQL.

Reuse these concepts:

- Admin document upload, listing, replacement, and deletion.
- Document parsing, chunking, embedding, and retrieval.
- Answers constrained to retrieved context with source citations.
- A gold test set starting with at least 25 reviewed Metro State questions,
  expected answers, expected sources, and answerability labels.
- Configurable chunk size, overlap, top-k, temperature, and top-p.
- Stored evaluation runs and a comparison table.
- Separate fast evaluation and deeper RAG-specific evaluation.

Do not initially copy:

- React or Tailwind front ends.
- Flask as the primary web server.
- Google Cloud Storage.
- Streaming responses.
- Optuna hyperparameter optimization.
- Full authentication or conversation history.

These features add complexity without proving the central project goal.

For class demonstration, assume local development first and standard PHP/MySQL
hosting if the professor wants to view the application through a hosted
environment. This keeps the project focused on RAG evaluation rather than custom
production infrastructure.

## Recommended Architecture

```text
Browser
  |
  v
PHP + Bootstrap application
  |-- document administration
  |-- question form and source display
  |-- evaluation configuration and dashboard
  |-- validation and access control
  |
  +--> MySQL
  |     |-- document metadata
  |     |-- questions and expected answers
  |     `-- responses, settings, and evaluation scores
  |
  +--> Python RAG helper/service
  |     |-- document parsing
  |     |-- chunking
  |     |-- embeddings
  |     `-- ChromaDB retrieval
  |
  +--> ChromaDB
  |     |-- chunk text
  |     |-- embeddings
  |     `-- source metadata
  |
  +--> LLM provider API
  |     |-- embeddings
  |     |-- answer generation
  |     `-- optional LLM-as-judge scoring
  |
  `--> Optional Python evaluation script
        `-- RAGAS or other Python-only evaluation libraries
```

PHP remains the main application server. Python handles the RAG layer because
the reference projects use ChromaDB and ChromaDB is easiest to operate from
Python. MySQL stores structured application data and evaluation results.

Format-specific text extraction should also remain in Python. TXT, PDF, and
DOCX parsers should return one normalized document representation so the
existing chunking and persistence logic does not branch by file format. Use
`pypdf` for text-based PDFs and `python-docx` for DOCX initially. Treat OCR for
scanned PDFs as a separate enhancement.

## Storage Recommendation

Use MySQL and ChromaDB together, and compare them where practical.

MySQL should store structured project data:

- document records,
- evaluation questions,
- expected answers,
- generated answers,
- evaluation runs,
- scores,
- model/settings metadata.

ChromaDB should store RAG/vector data:

- chunk text,
- embeddings,
- source document metadata,
- chunk IDs used during retrieval.

This matches the reference repositories more closely than storing embeddings in
MySQL.

The instructor also noted to use both MySQL and ChromaDB as two options for
comparison. The practical interpretation is:

- MySQL remains the source of structured records and can support simple keyword
  or SQL-based retrieval baselines.
- ChromaDB is the vector database for embedding-based semantic retrieval.
- Evaluation results should compare the retrieval/answer quality of those
  approaches when the implementation reaches FP7/FP8.

## API Keys and Secrets

The project can support any approved LLM provider, including OpenAI/ChatGPT,
Gemini, Claude, or another model provider. The specific provider can be selected
through configuration rather than hardcoded into the interface.

Your development API key must never be committed or sent to the browser.

Store local secrets in an ignored `.env` file:

```env
LLM_PROVIDER=replace_with_provider_name
LLM_API_KEY=replace_with_your_key
LLM_CHAT_MODEL=replace_with_approved_chat_model
LLM_EMBEDDING_MODEL=replace_with_approved_embedding_model

# Optional provider-specific keys if the implementation supports multiple providers.
OPENAI_API_KEY=
GEMINI_API_KEY=
ANTHROPIC_API_KEY=

DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=llm_rag_evals
DB_USER=root
DB_PASSWORD=replace_with_local_password
```

Commit an `.env.example` containing names and safe placeholders only. All API
requests must originate from PHP or an approved server-side evaluation script.
Never place a secret in JavaScript, HTML, screenshots, sample data, or Git
history.

Clarify whether:

- Any model provider is acceptable for the final demo, including
  OpenAI/ChatGPT, Gemini, Claude, or local models.
- API usage is covered by the school/course or paid out of pocket.
- A separate demonstration key is permitted.
- The professor provides any course credits or usage limits.

## Development Sequence

### Phase 1: Prove Retrieval and Grounded Answers

1. Select 3-5 public Metro State text documents.
2. Parse and chunk the documents.
3. Generate and store embeddings in ChromaDB.
4. Hard-code a question and retrieve the top matching chunks.
5. Generate an answer using only those chunks.
6. Print the answer and source filenames.

This proves the complete RAG round trip before UI work expands.

Status: completed in FP5, including the PHP Ask workflow, MySQL persistence,
and source display.

### Phase 2: Add Multi-Format Document Administration

1. Add browser upload/list/replace/delete controls and live indexed counts.
2. Validate TXT, PDF, and DOCX uploads in PHP.
3. Extract normalized text in Python.
4. Send parsed documents through the existing chunking, MySQL, and ChromaDB
   ingestion path.
5. Display ingestion status, chunk count, and actionable parsing errors.

This is the primary FP6 implementation target because the Ask page planned for
FP6 was completed early during FP5.

Status: implemented, verified, and pushed in FP6. The PHP endpoint validates and stores
uploads, `rag/document_loader.py` extracts normalized TXT/PDF/DOCX text, and
`rag/admin.py` bridges the browser request to the shared MySQL/ChromaDB
ingestion path. The UI lists document type, status, chunk count, and parser
errors and permits same-format replacement or deletion of browser-managed
uploads. Document/category summary counts update from the API response without
a page reload, while bundled source documents remain protected.

### Phase 3: Create the Gold Dataset

1. Start from the current 27 approved Metro State documents.
2. Write at least 25 manually reviewed questions, expanding the set when more
   questions improve research coverage.
3. Cover all categories and multiple types of factual or policy questions.
4. Record a concise expected answer, correct source, category, difficulty, and
   answerability for each question.
5. Include deliberately unanswerable questions to measure correct refusal and
   hallucination behavior.

The test set is central to the project. Evaluation results are not meaningful
without stable questions and expected answers.

The dataset size and evaluator count are separate requirements. The working
dataset target remains at least 25 reviewed questions, while the professor's
confirmed research direction is approximately ten evaluator types applied to
the same saved responses.

### Phase 4: Add Evaluation Management to the PHP Application

Implement three primary areas:

- Questions: manage expected answers, sources, categories, and answerability.
- Evaluate: choose settings, run selected gold questions, and persist results.
- Results: compare metrics and inspect individual responses and contexts.

### Phase 5: Add Evaluation Incrementally

Implement evaluator families in phases. Start with inexpensive local methods:

1. Exact/contains match.
2. BLEU/ROUGE/METEOR token-overlap family.
3. Embedding semantic similarity.
4. BERTScore.
5. Expected-source accuracy.
6. Refusal correctness, latency, evaluator runtime, and estimated cost.

Then add judged/RAG-specific methods:

7. A versioned LLM-as-judge rubric.
8. RAGAS Faithfulness.
9. RAGAS Response Relevancy.
10. RAGAS Context Precision and Context Recall.

Apply multiple metrics to the same stored responses. Record where metrics agree
or disagree, and label whether each failure originated in parsing, retrieval,
generation, expected data, or the metric itself.

See `docs/evaluation-strategy.md` for the authoritative evaluator definitions,
inputs, limitations, controlled protocol, and teaching requirements.

## Minimum Comparison Experiment

Keep most settings fixed and vary one parameter at a time:

| Experiment | Values |
| --- | --- |
| Chunk size | 300, 600, 900 |
| Chunk overlap | 50, 100, 150 |
| Top-k | 3, 5, 8 |
| Temperature | 0.0, 0.3 |

For each configuration, store:

- Average answer score.
- Average source/retrieval score.
- Average faithfulness score when available.
- Average latency.
- Estimated API cost.
- Per-question failures.

Avoid running every possible combination at first. A full grid can create many
paid API calls. Begin with a small question subset, then run the strongest
configurations against the full reviewed question set.

## Corpus Size and Composition Experiment

The professor noted that organizational RAG collections may range from hundreds
to millions of documents. This project should study that concern without
claiming to reproduce enterprise infrastructure.

1. Define reproducible collections, such as a focused category subset and the
   full 27-document corpus.
2. If more approved documents become available, add a larger collection or
   similar distractor documents.
3. Keep questions and RAG settings fixed where applicable.
4. Compare expected-source hit rate/rank, irrelevant contexts, answer quality,
   refusal behavior, latency, and metric agreement.
5. Report observations from the tested collections and explicitly limit any
   extrapolation to enterprise scale.

Do not assume the number of evaluation questions must grow at the same ratio as
the number of documents. Increase the question set when it improves coverage of
topics, document types, difficulty, answerability, or known failure modes.

## Confirmed Architecture Direction

PHP remains the main web application and Python handles parsing, ChromaDB,
retrieval, generation, and advanced evaluation. MySQL stores structured app
data and results, while ChromaDB stores chunks and embeddings. FP5 verified this
architecture end to end through the PHP Ask page.
