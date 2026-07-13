USE llm_rag_evals;

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
    CONSTRAINT fk_question_memberships_dataset FOREIGN KEY (dataset_id)
        REFERENCES evaluation_datasets (dataset_id) ON DELETE CASCADE,
    CONSTRAINT fk_question_memberships_question FOREIGN KEY (question_id)
        REFERENCES evaluation_questions (question_id) ON DELETE CASCADE
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
    UNIQUE KEY uq_evaluator_results_response_evaluator (response_id, evaluator_id),
    CONSTRAINT fk_evaluator_results_response FOREIGN KEY (response_id)
        REFERENCES rag_responses (response_id) ON DELETE CASCADE,
    CONSTRAINT fk_evaluator_results_evaluator FOREIGN KEY (evaluator_id)
        REFERENCES evaluator_definitions (evaluator_id)
);
