# RAG Evals Version 2.0 Database Schema Plan

## Purpose

Version 2.0 will extend the existing Version 1 MySQL schema rather than
replace it. The schema changes support two V2 features: **multimodal PDF
ingestion** and **conversation context**. Existing Version 1 response
and evaluation tables should be reused wherever possible.

## 1. Add `document_elements`

### Change

Create a new `document_elements` table between `documents` and
`document_chunks`.

``` text
documents
    1
    |
    N
document_elements
    1
    |
    N
document_chunks
```

Suggested fields:

  -----------------------------------------------------------------------
  Field                               Purpose
  ----------------------------------- -----------------------------------
  `element_id`                        Unique identifier for the document
                                      element

  `document_id`                       Links the element to its source
                                      document

  `element_index`                     Preserves element order within the
                                      document

  `page_number`                       Identifies the source PDF page

  `content_type`                      Identifies text, table, chart,
                                      diagram, image, or OCR-derived text

  `normalized_content`                Searchable textual representation
                                      of the element

  `extraction_method`                 Records how the content was
                                      extracted

  `extraction_model`                  Records the model used when
                                      AI-based extraction is required

  `created_at`                        Records when the element was
                                      created
  -----------------------------------------------------------------------

### Why

V1 moves directly from a document to text chunks. V2 needs an
intermediate representation so different PDF content types can be
identified, processed, and traced to their original page and extraction
method.

## 2. Update `document_chunks`

### Change

Add an `element_id` foreign key to `document_chunks`. Keep the existing
`document_id` for V1 compatibility.

### Why

A single document element may produce multiple searchable chunks. For
example, one large table may need to be divided into several row-group
chunks.

## 3. Add Multimodal Provenance to `retrieved_contexts`

### Change

Extend `retrieved_contexts` with multimodal provenance. Suggested
additions are:

  -----------------------------------------------------------------------
  Field                               Purpose
  ----------------------------------- -----------------------------------
  `element_id`                        Links retrieved evidence to its
                                      document element

  `page_number_snapshot`              Preserves the page number used
                                      during retrieval

  `content_type_snapshot`             Preserves whether evidence came
                                      from text, a table, chart, diagram,
                                      or image

  `extraction_method_snapshot`        Preserves how the original element
                                      was extracted
  -----------------------------------------------------------------------

Existing retrieval fields such as `document_id`, `chunk_id`, rank,
scores, and context excerpts should remain unchanged.

### Why

V2 needs to identify and display where multimodal evidence originated
while preserving provenance for historical RAG responses.

## 4. Add `conversations`

### Change

Create a new `conversations` table for individual chat sessions.

  Field               Purpose
  ------------------- ----------------------------------------------------------
  `conversation_id`   Unique identifier for the conversation
  `title`             Optional conversation name
  `status`            Indicates whether the conversation is active or archived
  `created_at`        Conversation creation time
  `updated_at`        Last conversation update

### Why

V1 stores individual RAG responses but does not have a persistent object
representing a multi-turn conversation.

## 5. Add `conversation_messages`

### Change

Create a new `conversation_messages` table linked to `conversations`.

  -----------------------------------------------------------------------
  Field                               Purpose
  ----------------------------------- -----------------------------------
  `message_id`                        Unique identifier for the message

  `conversation_id`                   Links the message to its
                                      conversation

  `role`                              Identifies the message as `user` or
                                      `assistant`

  `content`                           Stores the message text

  `sequence_number`                   Preserves message order

  `response_id`                       Links an assistant message to an
                                      existing RAG response when
                                      applicable

  `created_at`                        Records when the message was
                                      created
  -----------------------------------------------------------------------

``` text
conversations
    1
    |
    N
conversation_messages
          |
          | response_id
          v
     rag_responses
          |
          v
 retrieved_contexts
```

### Why

Conversation context requires ordered user and assistant messages.
Linking assistant messages to existing `rag_responses` avoids
duplicating response, retrieval, provenance, token, latency, and
evaluation data.

## 6. Update `model_settings`

### Change

Keep the existing `chunk_size` and `chunk_overlap` fields for backward
compatibility, but add:

  -----------------------------------------------------------------------
  Field                               Purpose
  ----------------------------------- -----------------------------------
  `chunking_strategy`                 Identifies the chunking method,
                                      such as fixed-character or
                                      content-aware

  `chunking_configuration_json`       Stores configuration specific to
                                      the selected strategy
  -----------------------------------------------------------------------

### Why

V1's size and overlap values describe fixed-character chunking. V2 uses
different rules for text, tables, and visual descriptions, so additional
configuration is needed for reproducible V1-versus-V2 experiments.

## 7. Preserve the Existing Evaluation Schema

### Change

No major initial changes are planned for:

``` text
evaluation_questions
evaluation_datasets
evaluation_question_memberships
evaluation_runs
evaluation_scores
evaluator_definitions
evaluator_results
evaluator_result_attempts
human_reviews
```

### Why

The existing evaluation infrastructure can continue evaluating V2 RAG
responses. Additional evaluation schema changes should only be
introduced later if multimodal or multi-turn evaluation demonstrates a
need for them.

## Proposed V2 Schema Structure

``` text
DOCUMENT / MULTIMODAL DATA

documents
    1
    |
    N
document_elements            [NEW]
    1
    |
    N
document_chunks              [UPDATED]
    |
    +--> ChromaDB embeddings


CHAT / RAG DATA

conversations                [NEW]
    1
    |
    N
conversation_messages        [NEW]
    |
    | response_id
    v
rag_responses                [EXISTING]
    |
    N
retrieved_contexts           [UPDATED]


EVALUATION DATA

evaluation_datasets
    |
evaluation_question_memberships
    |
evaluation_questions

model_settings               [UPDATED]
    |
evaluation_runs
    |
rag_responses
    |
    +--> evaluation_scores
    +--> evaluator_results
    |       |
    |       +--> evaluator_result_attempts
    |
    +--> human_reviews
```

## Summary of Required Changes

  -------------------------------------------------------------------------
  Schema Area               Change                  V2 Requirement
  ------------------------- ----------------------- -----------------------
  `document_elements`       **New table**           Represent multimodal
                                                    PDF elements before
                                                    chunking

  `document_chunks`         **Update**              Link chunks to their
                                                    source elements

  `retrieved_contexts`      **Update**              Preserve
                                                    multimodal/page-level
                                                    retrieval provenance

  `conversations`           **New table**           Represent persistent
                                                    chat sessions

  `conversation_messages`   **New table**           Store ordered
                                                    conversation history

  `model_settings`          **Update**              Record the V2
                                                    content-aware chunking
                                                    strategy

  Evaluation tables         **Reuse initially**     Preserve the existing
                                                    V1 evaluation framework
  -------------------------------------------------------------------------

## Implementation Principle

Version 2 should make the smallest schema changes necessary to support
multimodal ingestion and conversation context. Existing V1 tables,
relationships, response records, and evaluation infrastructure should
remain intact wherever possible so V1 baselines remain reproducible and
can be compared directly with V2.
