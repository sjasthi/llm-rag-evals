-- A NOT NULL column default filled old rows before migration 003 could label
-- them. Correct only explicitly identified legacy snapshots; never touch new
-- FP8+ runs whose corpus variant was captured at run creation.

UPDATE evaluation_runs
SET corpus_variant_key = 'legacy-unknown'
WHERE JSON_UNQUOTE(JSON_EXTRACT(run_configuration_json, '$.provenance_status')) = 'legacy_partial';
