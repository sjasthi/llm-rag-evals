-- Preserve the exact reviewed inputs and retrieval evidence used by each response.

UPDATE rag_responses response
LEFT JOIN evaluation_questions question ON question.question_id=response.question_id
SET response.evaluation_snapshot_json = CASE
        WHEN question.question_id IS NULL THEN NULL
        ELSE JSON_OBJECT(
            'snapshot_schema_version', 1,
            'question_id', question.question_id,
            'question_key', question.question_key,
            'question_text', question.question_text,
            'expected_answer', question.expected_answer,
            'expected_source', question.expected_source,
            'expected_evidence', question.expected_evidence,
            'accepted_answers', question.accepted_answers,
            'required_facts', question.required_facts,
            'category', question.category,
            'difficulty', question.difficulty,
            'is_answerable', question.is_answerable,
            'review_status', question.review_status,
            'question_updated_at', question.updated_at,
            'snapshot_note', 'Legacy backfill from the current question row; not original run-time evidence.'
        )
    END,
    response.snapshot_provenance = CASE
        WHEN question.question_id IS NULL THEN 'not_applicable'
        ELSE 'legacy_backfill'
    END,
    response.code_version = COALESCE(response.code_version, 'legacy-unavailable')
WHERE response.evaluation_snapshot_json IS NULL;

UPDATE retrieved_contexts context
LEFT JOIN documents document ON document.document_id=context.document_id
LEFT JOIN document_chunks chunk ON chunk.chunk_id=context.chunk_id
SET context.source_path_snapshot=COALESCE(context.source_path_snapshot, document.source_path),
    context.category_snapshot=COALESCE(context.category_snapshot, document.category),
    context.chunk_index_snapshot=COALESCE(context.chunk_index_snapshot, chunk.chunk_index),
    context.document_hash_snapshot=COALESCE(context.document_hash_snapshot, document.source_hash),
    context.chunk_hash_snapshot=COALESCE(context.chunk_hash_snapshot, SHA2(context.context_excerpt, 256)),
    context.semantic_distance=COALESCE(
        context.semantic_distance,
        CASE
            WHEN context.similarity_score IS NULL OR context.similarity_score <= 0 THEN NULL
            ELSE (1 / context.similarity_score) - 1
        END
    ),
    context.retrieval_metadata_json=COALESCE(
        context.retrieval_metadata_json,
        JSON_OBJECT(
            'version', 'legacy-unavailable',
            'score_provenance', 'semantic distance approximately recovered when similarity was present; lexical and final scores unavailable'
        )
    );
