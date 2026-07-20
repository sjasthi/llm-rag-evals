-- FP9 gives pre-FP8 runs an explicit, honest provenance record.
-- The old rows remain the same experiments; this only labels metadata that was
-- not captured when those rows were originally created.

UPDATE evaluation_runs AS run
JOIN model_settings AS settings ON settings.setting_id = run.setting_id
SET
    run.dataset_id = COALESCE(
        run.dataset_id,
        (SELECT dataset.dataset_id
         FROM evaluation_datasets AS dataset
         WHERE dataset.dataset_id = CAST(
             SUBSTRING_INDEX(SUBSTRING_INDEX(run.notes, 'dataset_id=', -1), ';', 1)
             AS UNSIGNED
         )
         LIMIT 1)
    ),
    run.experiment_key = COALESCE(run.experiment_key, CONCAT('legacy-run-', run.run_id)),
    run.corpus_variant_key = COALESCE(run.corpus_variant_key, 'legacy-unknown'),
    run.run_configuration_json = COALESCE(
        run.run_configuration_json,
        JSON_OBJECT(
            'schema_version', 'fp9-legacy-backfill-1',
            'provenance_status', 'legacy_partial',
            'note', 'Run predates FP8 configuration snapshots; only database-backed settings can be recovered.',
            'dataset_recovery', 'parsed_from_legacy_notes_when_available',
            'retrieval_method', settings.retrieval_method,
            'chat_model', settings.chat_model,
            'embedding_model', settings.embedding_model,
            'top_k', settings.top_k,
            'temperature', settings.temperature
        )
    );
