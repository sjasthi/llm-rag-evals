USE llm_rag_evals;

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
    CONSTRAINT fk_evaluator_attempts_response FOREIGN KEY (response_id)
        REFERENCES rag_responses (response_id) ON DELETE CASCADE,
    CONSTRAINT fk_evaluator_attempts_evaluator FOREIGN KEY (evaluator_id)
        REFERENCES evaluator_definitions (evaluator_id)
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
    CONSTRAINT fk_human_reviews_response FOREIGN KEY (response_id)
        REFERENCES rag_responses (response_id) ON DELETE CASCADE,
    CONSTRAINT chk_human_review_correctness CHECK (correctness IS NULL OR correctness BETWEEN 1 AND 5),
    CONSTRAINT chk_human_review_completeness CHECK (completeness IS NULL OR completeness BETWEEN 1 AND 5),
    CONSTRAINT chk_human_review_faithfulness CHECK (faithfulness IS NULL OR faithfulness BETWEEN 1 AND 5),
    CONSTRAINT chk_human_review_relevance CHECK (relevance IS NULL OR relevance BETWEEN 1 AND 5),
    CONSTRAINT chk_human_review_refusal CHECK (refusal_correctness IS NULL OR refusal_correctness BETWEEN 1 AND 5)
);

INSERT INTO evaluator_result_attempts (
    response_id, evaluator_id, attempt_number, status, raw_score,
    normalized_score, passed, explanation, details_json, configuration_json,
    runtime_ms, estimated_cost, error_message, created_at
)
SELECT
    er.response_id, er.evaluator_id, 1, er.status, er.raw_score,
    er.normalized_score, er.passed, er.explanation, er.details_json,
    JSON_OBJECT('source', 'fp7_result_backfill', 'canonical_policy', 'latest_attempt'),
    er.runtime_ms, er.estimated_cost, er.error_message, er.created_at
FROM evaluator_results er
LEFT JOIN evaluator_result_attempts attempt
    ON attempt.response_id = er.response_id
   AND attempt.evaluator_id = er.evaluator_id
   AND attempt.attempt_number = 1
WHERE attempt.attempt_id IS NULL;
