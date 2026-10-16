-- RAG EVAL 2.0: Hybrid Retrieval
-- Adds hybrid_rrf to the supported retrieval methods.
-- Existing retrieval methods and stored records are preserved.

ALTER TABLE model_settings
MODIFY COLUMN retrieval_method
ENUM('mysql_keyword', 'chroma_vector', 'hybrid_rrf')
COLLATE utf8mb4_unicode_ci
NOT NULL;

ALTER TABLE rag_responses
MODIFY COLUMN retrieval_method
ENUM('mysql_keyword', 'chroma_vector', 'hybrid_rrf')
COLLATE utf8mb4_unicode_ci
NOT NULL DEFAULT 'chroma_vector';