CREATE DATABASE IF NOT EXISTS llm_rag_evals
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE llm_rag_evals;

CREATE TABLE IF NOT EXISTS documents (
    document_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    source_path VARCHAR(500) NOT NULL,
    source_type VARCHAR(50) NOT NULL DEFAULT 'txt',
    original_filename VARCHAR(255) NULL,
    status ENUM('pending', 'ingested', 'failed', 'archived') NOT NULL DEFAULT 'pending',
    source_hash CHAR(64) NULL,
    chunk_size INT UNSIGNED NULL,
    chunk_overlap INT UNSIGNED NULL,
    ingestion_error TEXT NULL,
    imported_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_documents_source_path (source_path)
);

CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    document_id BIGINT UNSIGNED NOT NULL,
    chunk_index INT UNSIGNED NOT NULL,
    chunk_text MEDIUMTEXT NOT NULL,
    token_estimate INT UNSIGNED NULL,
    chroma_id VARCHAR(255) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_document_chunks_document_index (document_id, chunk_index),
    UNIQUE KEY uq_document_chunks_chroma_id (chroma_id),
    FULLTEXT KEY ft_document_chunks_text (chunk_text),
    CONSTRAINT fk_document_chunks_document
        FOREIGN KEY (document_id) REFERENCES documents (document_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evaluation_questions (
    question_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    question_key CHAR(64) NULL,
    question_text TEXT NOT NULL,
    expected_answer TEXT NOT NULL,
    expected_source VARCHAR(500) NULL,
    expected_evidence TEXT NULL,
    accepted_answers JSON NULL,
    required_facts JSON NULL,
    category VARCHAR(100) NULL,
    difficulty ENUM('easy', 'medium', 'hard') NOT NULL DEFAULT 'medium',
    is_answerable BOOLEAN NOT NULL DEFAULT TRUE,
    reviewer_notes TEXT NULL,
    review_status ENUM('draft', 'reviewed', 'needs_revision') NOT NULL DEFAULT 'draft',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evaluation_datasets (
    dataset_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    dataset_name VARCHAR(160) NOT NULL,
    version VARCHAR(50) NOT NULL,
    description TEXT NULL,
    status ENUM('draft', 'reviewed', 'archived') NOT NULL DEFAULT 'draft',
    reviewed_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_evaluation_datasets_name_version (dataset_name, version)
);

CREATE TABLE IF NOT EXISTS evaluation_question_memberships (
    dataset_id BIGINT UNSIGNED NOT NULL,
    question_id BIGINT UNSIGNED NOT NULL,
    display_order INT UNSIGNED NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (dataset_id, question_id),
    UNIQUE KEY uq_dataset_question_order (dataset_id, display_order),
    CONSTRAINT fk_question_memberships_dataset
        FOREIGN KEY (dataset_id) REFERENCES evaluation_datasets (dataset_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_question_memberships_question
        FOREIGN KEY (question_id) REFERENCES evaluation_questions (question_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS model_settings (
    setting_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    setting_name VARCHAR(120) NOT NULL,
    retrieval_method ENUM('mysql_keyword', 'chroma_vector') NOT NULL,
    llm_provider VARCHAR(80) NOT NULL,
    chat_model VARCHAR(120) NOT NULL,
    embedding_model VARCHAR(120) NULL,
    chunk_size INT UNSIGNED NULL,
    chunk_overlap INT UNSIGNED NULL,
    top_k INT UNSIGNED NOT NULL DEFAULT 5,
    temperature DECIMAL(3,2) NOT NULL DEFAULT 0.00,
    top_p DECIMAL(3,2) NOT NULL DEFAULT 1.00,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evaluation_runs (
    run_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    setting_id BIGINT UNSIGNED NOT NULL,
    dataset_id BIGINT UNSIGNED NULL,
    baseline_run_id BIGINT UNSIGNED NULL,
    run_name VARCHAR(160) NOT NULL,
    experiment_key VARCHAR(120) NULL,
    corpus_variant_key VARCHAR(120) NOT NULL DEFAULT 'full_current',
    run_configuration_json JSON NULL,
    status ENUM('planned', 'running', 'completed', 'failed') NOT NULL DEFAULT 'planned',
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    notes TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_evaluation_runs_setting
        FOREIGN KEY (setting_id) REFERENCES model_settings (setting_id),
    CONSTRAINT fk_evaluation_runs_dataset
        FOREIGN KEY (dataset_id) REFERENCES evaluation_datasets (dataset_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_evaluation_runs_baseline
        FOREIGN KEY (baseline_run_id) REFERENCES evaluation_runs (run_id)
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS rag_responses (
    response_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    run_id BIGINT UNSIGNED NULL,
    setting_id BIGINT UNSIGNED NULL,
    question_id BIGINT UNSIGNED NULL,
    question_text TEXT NOT NULL,
    answer_text MEDIUMTEXT NOT NULL,
    retrieval_method ENUM('mysql_keyword', 'chroma_vector') NOT NULL,
    latency_ms INT UNSIGNED NULL,
    estimated_cost DECIMAL(12,8) NULL,
    evaluation_snapshot_json JSON NULL,
    snapshot_provenance VARCHAR(32) NOT NULL DEFAULT 'missing',
    code_version VARCHAR(160) NULL,
    input_tokens INT UNSIGNED NULL,
    output_tokens INT UNSIGNED NULL,
    total_tokens INT UNSIGNED NULL,
    generation_cost_status VARCHAR(32) NOT NULL DEFAULT 'unavailable',
    generation_metadata_json JSON NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_rag_responses_run_question (run_id, question_id),
    CONSTRAINT fk_rag_responses_run
        FOREIGN KEY (run_id) REFERENCES evaluation_runs (run_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_rag_responses_setting
        FOREIGN KEY (setting_id) REFERENCES model_settings (setting_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_rag_responses_question
        FOREIGN KEY (question_id) REFERENCES evaluation_questions (question_id)
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS retrieved_contexts (
    context_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    response_id BIGINT UNSIGNED NOT NULL,
    document_id BIGINT UNSIGNED NULL,
    chunk_id BIGINT UNSIGNED NULL,
    source_path_snapshot VARCHAR(500) NULL,
    category_snapshot VARCHAR(100) NULL,
    chunk_index_snapshot INT UNSIGNED NULL,
    document_hash_snapshot CHAR(64) NULL,
    chunk_hash_snapshot CHAR(64) NULL,
    rank_position INT UNSIGNED NOT NULL,
    similarity_score DECIMAL(8,6) NULL,
    semantic_distance DECIMAL(12,8) NULL,
    lexical_score DECIMAL(12,8) NULL,
    retrieval_score DECIMAL(12,8) NULL,
    retrieval_metadata_json JSON NULL,
    context_excerpt TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_retrieved_contexts_response
        FOREIGN KEY (response_id) REFERENCES rag_responses (response_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_retrieved_contexts_document
        FOREIGN KEY (document_id) REFERENCES documents (document_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_retrieved_contexts_chunk
        FOREIGN KEY (chunk_id) REFERENCES document_chunks (chunk_id)
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS evaluation_scores (
    score_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    response_id BIGINT UNSIGNED NOT NULL,
    exact_match_score DECIMAL(5,4) NULL,
    semantic_similarity_score DECIMAL(5,4) NULL,
    source_accuracy_score DECIMAL(5,4) NULL,
    judge_score DECIMAL(5,4) NULL,
    notes TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_evaluation_scores_response
        FOREIGN KEY (response_id) REFERENCES rag_responses (response_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evaluator_definitions (
    evaluator_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    evaluator_key VARCHAR(80) NOT NULL,
    display_name VARCHAR(160) NOT NULL,
    family ENUM('lexical', 'semantic', 'retrieval', 'judged', 'ragas', 'supporting') NOT NULL,
    dimension ENUM('retrieval', 'generation', 'both', 'operational') NOT NULL,
    version VARCHAR(80) NOT NULL,
    description TEXT NOT NULL,
    configuration_json JSON NULL,
    is_local BOOLEAN NOT NULL DEFAULT TRUE,
    is_deterministic BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_evaluator_definitions_key_version (evaluator_key, version)
);

CREATE TABLE IF NOT EXISTS evaluator_results (
    result_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    response_id BIGINT UNSIGNED NOT NULL,
    evaluator_id BIGINT UNSIGNED NOT NULL,
    status ENUM('completed', 'skipped', 'failed') NOT NULL DEFAULT 'completed',
    raw_score DECIMAL(12,8) NULL,
    normalized_score DECIMAL(12,8) NULL,
    passed BOOLEAN NULL,
    explanation TEXT NULL,
    details_json JSON NULL,
    runtime_ms INT UNSIGNED NULL,
    estimated_cost DECIMAL(12,8) NULL,
    error_message TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_evaluator_results_response_evaluator (response_id, evaluator_id),
    CONSTRAINT fk_evaluator_results_response
        FOREIGN KEY (response_id) REFERENCES rag_responses (response_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_evaluator_results_evaluator
        FOREIGN KEY (evaluator_id) REFERENCES evaluator_definitions (evaluator_id)
);

CREATE TABLE IF NOT EXISTS evaluator_result_attempts (
    attempt_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    response_id BIGINT UNSIGNED NOT NULL,
    evaluator_id BIGINT UNSIGNED NOT NULL,
    attempt_number INT UNSIGNED NOT NULL,
    status ENUM('completed', 'skipped', 'failed') NOT NULL DEFAULT 'completed',
    raw_score DECIMAL(12,8) NULL,
    normalized_score DECIMAL(12,8) NULL,
    passed BOOLEAN NULL,
    explanation TEXT NULL,
    details_json JSON NULL,
    configuration_json JSON NULL,
    raw_provider_output MEDIUMTEXT NULL,
    input_tokens INT UNSIGNED NULL,
    output_tokens INT UNSIGNED NULL,
    total_tokens INT UNSIGNED NULL,
    runtime_ms INT UNSIGNED NULL,
    estimated_cost DECIMAL(12,8) NULL,
    error_message TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_evaluator_attempt_number (response_id, evaluator_id, attempt_number),
    KEY idx_evaluator_attempts_evaluator (evaluator_id),
    CONSTRAINT fk_evaluator_attempts_response
        FOREIGN KEY (response_id) REFERENCES rag_responses (response_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_evaluator_attempts_evaluator
        FOREIGN KEY (evaluator_id) REFERENCES evaluator_definitions (evaluator_id)
);

CREATE TABLE IF NOT EXISTS human_reviews (
    review_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    response_id BIGINT UNSIGNED NOT NULL,
    reviewer_alias VARCHAR(120) NOT NULL,
    rubric_version VARCHAR(40) NOT NULL DEFAULT '1.0',
    correctness TINYINT UNSIGNED NULL,
    completeness TINYINT UNSIGNED NULL,
    faithfulness TINYINT UNSIGNED NULL,
    relevance TINYINT UNSIGNED NULL,
    refusal_correctness TINYINT UNSIGNED NULL,
    overall_decision ENUM('acceptable', 'needs_revision', 'incorrect', 'not_applicable') NOT NULL,
    failure_category VARCHAR(80) NULL,
    notes TEXT NULL,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    reviewed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_human_reviews_response_current (response_id, is_current),
    CONSTRAINT fk_human_reviews_response
        FOREIGN KEY (response_id) REFERENCES rag_responses (response_id)
        ON DELETE CASCADE,
    CONSTRAINT chk_human_review_correctness CHECK (correctness IS NULL OR correctness BETWEEN 1 AND 5),
    CONSTRAINT chk_human_review_completeness CHECK (completeness IS NULL OR completeness BETWEEN 1 AND 5),
    CONSTRAINT chk_human_review_faithfulness CHECK (faithfulness IS NULL OR faithfulness BETWEEN 1 AND 5),
    CONSTRAINT chk_human_review_relevance CHECK (relevance IS NULL OR relevance BETWEEN 1 AND 5),
    CONSTRAINT chk_human_review_refusal CHECK (refusal_correctness IS NULL OR refusal_correctness BETWEEN 1 AND 5)
);
