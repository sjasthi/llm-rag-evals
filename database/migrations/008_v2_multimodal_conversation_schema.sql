-- V2 adds document_elements, conversations, and conversation_messages, links
-- chunks and retrieved contexts to their source elements, and records the
-- chunking strategy on model_settings. Tables and columns are created by
-- schema.sql and initialize_schema(); this migration labels existing rows.
--
-- Every pre-V2 setting used V1 fixed-character chunking, so its size and
-- overlap fully describe the strategy. Existing chunks and retrieved contexts
-- keep element_id and multimodal snapshots NULL: that provenance was not
-- captured when they were created, and re-ingestion will populate it.

UPDATE model_settings
SET chunking_strategy = 'fixed_character',
    chunking_configuration_json = JSON_OBJECT(
        'chunk_size', chunk_size,
        'chunk_overlap', chunk_overlap,
        'provenance', 'legacy_backfill'
    )
WHERE chunking_configuration_json IS NULL;
