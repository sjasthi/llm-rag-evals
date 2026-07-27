-- Track answer-generation usage without representing unknown price as zero cost.

UPDATE rag_responses
SET generation_cost_status = CASE
        WHEN estimated_cost IS NULL THEN 'unavailable'
        ELSE 'recorded'
    END,
    generation_metadata_json = COALESCE(
        generation_metadata_json,
        JSON_OBJECT(
            'provenance', 'legacy_backfill',
            'note', 'Provider token usage was not captured for this historical response.'
        )
    )
WHERE generation_metadata_json IS NULL;
