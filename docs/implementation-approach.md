# Recommended Implementation Approach

## What to Reuse From the Reference Projects

The reference repositories should be treated as examples of workflows and data,
not as codebases to copy directly. Both use React and Flask, while this project
requires Bootstrap, PHP, and MySQL.

Reuse these concepts:

- Admin document upload, listing, replacement, and deletion.
- Document parsing, chunking, embedding, and retrieval.
- Answers constrained to retrieved context with source citations.
- A gold test set of approximately 50 Metro State questions and expected answers.
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

For class demonstration, assume the application runs locally unless the
professor says otherwise. Localhost deployment keeps the project focused on RAG
evaluation rather than hosting, accounts, and production infrastructure.

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

## Storage Recommendation

Use MySQL and ChromaDB together.

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

### Phase 1: Prove Retrieval Without a Web Interface

1. Select 3-5 public Metro State text documents.
2. Parse and chunk the documents.
3. Generate and store embeddings in ChromaDB.
4. Hard-code a question and retrieve the top matching chunks.
5. Generate an answer using only those chunks.
6. Print the answer and source filenames.

This proves the complete RAG round trip before UI work expands.

### Phase 2: Create the Gold Dataset

1. Collect approximately 20 approved public Metro State documents.
2. Write approximately 50 answerable questions.
3. Record a concise expected answer and correct source for each question.
4. Include some questions that cannot be answered from the documents.

The test set is central to the project. Evaluation results are not meaningful
without stable questions and expected answers.

### Phase 3: Add the PHP Application

Implement three primary areas:

- Ask: question input, answer, sources, and suggested questions.
- Admin: upload/list/replace/delete documents and show chunk counts.
- Evaluate: choose settings, run the gold questions, and compare results.

### Phase 4: Add Evaluation Incrementally

Start with:

1. Exact or normalized string match.
2. Semantic similarity between expected and generated answers.
3. Retrieval source accuracy.
4. Latency and estimated API cost.

Then add:

5. LLM-as-judge scoring.
6. Faithfulness and answer relevancy.
7. Optional RAGAS runs through an offline Python script.

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
configurations against all 50 questions.

## First Architecture Decision to Confirm

Ask the professor:

> Since the required web stack is PHP and MySQL, may we use an offline Python
> helper/service for ChromaDB ingestion and retrieval while keeping PHP as the
> main application server? MySQL would store structured app data and results,
> while ChromaDB would store chunks and embeddings.
