-- Migration 003 originally associated all legacy runs with the newest reviewed
-- dataset. FP7 stored the real dataset ID in run notes, so recover that exact
-- value when it references an existing dataset and label the recovery source.

UPDATE evaluation_runs AS run
JOIN evaluation_datasets AS dataset
  ON dataset.dataset_id = CAST(
      SUBSTRING_INDEX(SUBSTRING_INDEX(run.notes, 'dataset_id=', -1), ';', 1)
      AS UNSIGNED
  )
SET
    run.dataset_id = dataset.dataset_id,
    run.run_configuration_json = JSON_SET(
        COALESCE(run.run_configuration_json, JSON_OBJECT()),
        '$.dataset_recovery', 'parsed_from_legacy_notes'
    )
WHERE JSON_UNQUOTE(JSON_EXTRACT(run.run_configuration_json, '$.provenance_status')) = 'legacy_partial'
  AND run.notes LIKE '%dataset_id=%';
