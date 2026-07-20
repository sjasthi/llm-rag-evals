<?php

declare(strict_types=1);

require_once dirname(__DIR__) . '/config/database.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function evaluationResponse(int $status, array $payload): never
{
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    exit;
}

function decodedObject(mixed $value): array
{
    if (is_array($value)) {
        return $value;
    }
    if (!is_string($value) || trim($value) === '') {
        return [];
    }
    $decoded = json_decode($value, true);
    return is_array($decoded) ? $decoded : [];
}

function normalizeJsonColumns(array $rows, array $columns): array
{
    foreach ($rows as &$row) {
        foreach ($columns as $column) {
            if (array_key_exists($column, $row)) {
                $row[$column] = decodedObject($row[$column]);
            }
        }
    }
    unset($row);
    return $rows;
}

function evaluatorLayer(array $row): string
{
    $configuration = decodedObject($row['configuration_json'] ?? null);
    return is_string($configuration['layer'] ?? null) ? $configuration['layer'] : 'baseline';
}

function disagreementPrompts(array $results, array $reviews): array
{
    $scores = [];
    foreach ($results as $result) {
        if (($result['status'] ?? '') === 'completed' && $result['normalized_score'] !== null) {
            $scores[$result['evaluator_key']] = (float) $result['normalized_score'];
        }
    }
    $prompts = [];
    if (($scores['semantic_similarity'] ?? -1) >= 0.75 && ($scores['token_f1'] ?? 1) < 0.70) {
        $prompts[] = [
            'key' => 'possible_paraphrase',
            'title' => 'Possible correct paraphrase',
            'explanation' => 'Semantic similarity is above its review threshold while token overlap is below it. Inspect wording and facts.',
        ];
    }
    if (($scores['semantic_similarity'] ?? -1) >= 0.75 && ($scores['llm_judge'] ?? 1) < 0.75) {
        $prompts[] = [
            'key' => 'semantic_judge_conflict',
            'title' => 'Similar wording, judge concern',
            'explanation' => 'The answer resembles the reference semantically, but the rubric judge flagged a quality problem. Check dates, negation, and missing facts.',
        ];
    }
    if (($scores['ragas_response_relevancy'] ?? -1) >= 0.80 && ($scores['ragas_faithfulness'] ?? 1) < 0.60) {
        $prompts[] = [
            'key' => 'relevant_not_grounded',
            'title' => 'Direct but potentially unsupported',
            'explanation' => 'Response relevancy is high while faithfulness is low. A direct answer is not necessarily grounded.',
        ];
    }
    if (($scores['expected_source_accuracy'] ?? 0) >= 1.0 && ($scores['ragas_context_precision'] ?? 1) < 0.60) {
        $prompts[] = [
            'key' => 'source_hit_with_noise',
            'title' => 'Correct source mixed with retrieval noise',
            'explanation' => 'The expected source was retrieved, but context precision suggests distracting chunks may rank alongside it.',
        ];
    }
    $currentReview = $reviews[0] ?? null;
    if (is_array($currentReview) && in_array($currentReview['overall_decision'], ['needs_revision', 'incorrect'], true)
        && ($scores['llm_judge'] ?? 0) >= 0.75) {
        $prompts[] = [
            'key' => 'human_judge_conflict',
            'title' => 'Human and judge disagree',
            'explanation' => 'The automated judge is above its review threshold, but the current human review found a problem. Treat this as calibration evidence.',
        ];
    }
    return $prompts;
}

function validatedRating(mixed $value, string $field): ?int
{
    if ($value === null || $value === '') {
        return null;
    }
    $rating = filter_var($value, FILTER_VALIDATE_INT);
    if ($rating === false || $rating < 1 || $rating > 5) {
        evaluationResponse(422, ['ok' => false, 'error' => "$field must be between 1 and 5."]);
    }
    return (int) $rating;
}

try {
    $database = databaseConnection();
    $method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

    if ($method === 'GET') {
        $responseId = filter_input(INPUT_GET, 'response_id', FILTER_VALIDATE_INT);
        if ($responseId) {
            $statement = $database->prepare(
                "SELECT r.response_id, r.question_text, r.answer_text, r.retrieval_method,
                        r.latency_ms, r.estimated_cost AS answer_estimated_cost, r.created_at,
                        q.expected_answer, q.expected_source, q.expected_evidence,
                        q.required_facts, q.category, q.difficulty, q.is_answerable,
                        q.review_status AS dataset_review_status,
                        run.run_id, run.run_name, run.experiment_key,
                        run.corpus_variant_key, run.run_configuration_json,
                        settings.chat_model, settings.embedding_model, settings.top_k
                 FROM rag_responses r
                 LEFT JOIN evaluation_questions q ON q.question_id = r.question_id
                 LEFT JOIN evaluation_runs run ON run.run_id = r.run_id
                 LEFT JOIN model_settings settings ON settings.setting_id = r.setting_id
                 WHERE r.response_id = ?"
            );
            $statement->execute([$responseId]);
            $response = $statement->fetch();
            if (!$response) {
                evaluationResponse(404, ['ok' => false, 'error' => 'Saved response was not found.']);
            }
            $response['required_facts'] = decodedObject($response['required_facts']);
            $response['run_configuration_json'] = decodedObject($response['run_configuration_json']);

            $statement = $database->prepare(
                "SELECT c.rank_position, c.similarity_score, c.context_excerpt,
                        d.source_path, d.category, c.document_id, c.chunk_id
                 FROM retrieved_contexts c
                 LEFT JOIN documents d ON d.document_id=c.document_id
                 WHERE c.response_id=? ORDER BY c.rank_position"
            );
            $statement->execute([$responseId]);
            $contexts = $statement->fetchAll();
            foreach ($contexts as &$context) {
                $context['is_expected_source'] = $response['expected_source'] !== null
                    && strcasecmp((string) $context['source_path'], (string) $response['expected_source']) === 0;
            }
            unset($context);

            $statement = $database->prepare(
                "SELECT e.display_name, e.evaluator_key, e.family, e.dimension,
                        e.version, e.configuration_json, e.is_local, e.is_deterministic,
                        er.status, er.raw_score, er.normalized_score, er.passed,
                        er.explanation, er.details_json, er.runtime_ms,
                        er.estimated_cost, er.error_message, er.updated_at,
                        COUNT(attempt.attempt_id) AS attempt_count,
                        AVG(CASE WHEN attempt.status='completed' THEN attempt.normalized_score END) AS attempt_mean,
                        MIN(CASE WHEN attempt.status='completed' THEN attempt.normalized_score END) AS attempt_min,
                        MAX(CASE WHEN attempt.status='completed' THEN attempt.normalized_score END) AS attempt_max,
                        STDDEV_POP(CASE WHEN attempt.status='completed' THEN attempt.normalized_score END) AS attempt_stddev
                 FROM evaluator_results er
                 JOIN evaluator_definitions e ON e.evaluator_id=er.evaluator_id
                 LEFT JOIN evaluator_result_attempts attempt
                   ON attempt.response_id=er.response_id AND attempt.evaluator_id=er.evaluator_id
                 WHERE er.response_id=?
                 GROUP BY er.result_id, e.evaluator_id
                 ORDER BY FIELD(JSON_UNQUOTE(JSON_EXTRACT(e.configuration_json, '$.layer')), 'baseline', 'advanced'), e.evaluator_id"
            );
            $statement->execute([$responseId]);
            $results = normalizeJsonColumns($statement->fetchAll(), ['configuration_json', 'details_json']);
            foreach ($results as &$result) {
                $result['layer'] = $result['configuration_json']['layer'] ?? 'baseline';
            }
            unset($result);

            $statement = $database->prepare(
                "SELECT attempt.attempt_id, attempt.attempt_number, attempt.status,
                        attempt.raw_score, attempt.normalized_score, attempt.passed,
                        attempt.explanation, attempt.details_json,
                        attempt.configuration_json, attempt.input_tokens,
                        attempt.output_tokens, attempt.total_tokens, attempt.runtime_ms,
                        attempt.estimated_cost, attempt.error_message, attempt.created_at,
                        e.evaluator_key, e.display_name
                 FROM evaluator_result_attempts attempt
                 JOIN evaluator_definitions e ON e.evaluator_id=attempt.evaluator_id
                 WHERE attempt.response_id=?
                 ORDER BY e.evaluator_id, attempt.attempt_number"
            );
            $statement->execute([$responseId]);
            $attempts = normalizeJsonColumns($statement->fetchAll(), ['configuration_json', 'details_json']);

            $statement = $database->prepare(
                "SELECT review_id, reviewer_alias, rubric_version, correctness,
                        completeness, faithfulness, relevance, refusal_correctness,
                        overall_decision, failure_category, notes, reviewed_at, updated_at
                 FROM human_reviews
                 WHERE response_id=? AND is_current=TRUE
                 ORDER BY reviewed_at DESC, review_id DESC"
            );
            $statement->execute([$responseId]);
            $reviews = $statement->fetchAll();

            evaluationResponse(200, ['ok' => true, 'data' => [
                'response' => $response,
                'contexts' => $contexts,
                'results' => $results,
                'attempts' => $attempts,
                'human_reviews' => $reviews,
                'disagreements' => disagreementPrompts($results, $reviews),
            ]]);
        }

        $dataset = $database->query(
            "SELECT d.dataset_id, d.dataset_name, d.version, d.description, d.status,
                    COUNT(m.question_id) AS question_count,
                    SUM(q.review_status = 'reviewed') AS reviewed_count,
                    SUM(q.is_answerable = FALSE) AS unanswerable_count,
                    COUNT(DISTINCT q.category) AS category_count
             FROM evaluation_datasets d
             LEFT JOIN evaluation_question_memberships m ON m.dataset_id = d.dataset_id
             LEFT JOIN evaluation_questions q ON q.question_id = m.question_id
             GROUP BY d.dataset_id
             ORDER BY d.dataset_id DESC LIMIT 1"
        )->fetch();
        $questions = [];
        if ($dataset) {
            $statement = $database->prepare(
                "SELECT q.question_id, q.question_text, q.expected_answer, q.expected_source,
                        q.expected_evidence, q.required_facts, q.category, q.difficulty,
                        q.is_answerable, q.review_status, m.display_order
                 FROM evaluation_question_memberships m
                 JOIN evaluation_questions q ON q.question_id = m.question_id
                 WHERE m.dataset_id = ? ORDER BY m.display_order"
            );
            $statement->execute([$dataset['dataset_id']]);
            $questions = normalizeJsonColumns($statement->fetchAll(), ['required_facts']);
        }

        $evaluators = normalizeJsonColumns($database->query(
            "SELECT evaluator_key, display_name, family, dimension, version,
                    is_local, is_deterministic, description, configuration_json
             FROM evaluator_definitions WHERE is_active=TRUE ORDER BY evaluator_id"
        )->fetchAll(), ['configuration_json']);
        foreach ($evaluators as &$evaluator) {
            $evaluator['layer'] = $evaluator['configuration_json']['layer'] ?? 'baseline';
        }
        unset($evaluator);

        $runs = normalizeJsonColumns($database->query(
            "SELECT run.run_id, run.run_name, run.status, run.started_at, run.completed_at,
                    run.dataset_id, run.baseline_run_id, run.experiment_key,
                    run.corpus_variant_key, run.run_configuration_json,
                    settings.retrieval_method, settings.chat_model, settings.embedding_model,
                    settings.top_k, COALESCE(response_summary.response_count, 0) AS response_count,
                    COALESCE(result_summary.result_count, 0) AS result_count,
                    COALESCE(result_summary.evaluator_error_count, 0) AS evaluator_error_count,
                    COALESCE(result_summary.evaluator_skipped_count, 0) AS evaluator_skipped_count,
                    COALESCE(response_summary.answer_runtime_ms, 0) AS answer_runtime_ms,
                    COALESCE(attempt_summary.evaluator_attempt_count, 0) AS evaluator_attempt_count,
                    COALESCE(attempt_summary.evaluator_runtime_ms, 0) AS evaluator_runtime_ms,
                    COALESCE(attempt_summary.evaluator_estimated_cost, 0) AS evaluator_estimated_cost,
                    (SELECT COUNT(*) FROM evaluation_question_memberships membership
                     WHERE membership.dataset_id=run.dataset_id) AS dataset_question_count,
                    (SELECT COUNT(*) FROM human_reviews review
                     JOIN rag_responses reviewed_response ON reviewed_response.response_id=review.response_id
                     WHERE reviewed_response.run_id=run.run_id AND review.is_current=TRUE) AS human_review_count
             FROM evaluation_runs run
             JOIN model_settings settings ON settings.setting_id=run.setting_id
             LEFT JOIN (
                 SELECT run_id, COUNT(*) AS response_count,
                        SUM(COALESCE(latency_ms, 0)) AS answer_runtime_ms
                 FROM rag_responses GROUP BY run_id
             ) response_summary ON response_summary.run_id=run.run_id
             LEFT JOIN (
                 SELECT response.run_id, COUNT(result.result_id) AS result_count,
                        SUM(result.status='failed') AS evaluator_error_count,
                        SUM(result.status='skipped') AS evaluator_skipped_count
                 FROM rag_responses response
                 JOIN evaluator_results result ON result.response_id=response.response_id
                 GROUP BY response.run_id
             ) result_summary ON result_summary.run_id=run.run_id
             LEFT JOIN (
                 SELECT response.run_id, COUNT(attempt.attempt_id) AS evaluator_attempt_count,
                        SUM(COALESCE(attempt.runtime_ms, 0)) AS evaluator_runtime_ms,
                        SUM(COALESCE(attempt.estimated_cost, 0)) AS evaluator_estimated_cost
                 FROM rag_responses response
                 JOIN evaluator_result_attempts attempt ON attempt.response_id=response.response_id
                 GROUP BY response.run_id
             ) attempt_summary ON attempt_summary.run_id=run.run_id
             ORDER BY run.run_id DESC LIMIT 25"
        )->fetchAll(), ['run_configuration_json']);

        $responses = $database->query(
            "SELECT response.response_id, response.run_id, response.question_text,
                    response.latency_ms, response.created_at,
                    COUNT(result.result_id) AS result_count,
                    SUM(JSON_UNQUOTE(JSON_EXTRACT(definition.configuration_json, '$.layer'))='baseline') AS baseline_result_count,
                    SUM(JSON_UNQUOTE(JSON_EXTRACT(definition.configuration_json, '$.layer'))='advanced') AS advanced_result_count,
                    SUM(result.status='failed') AS failed_result_count,
                    SUM(result.status='skipped') AS skipped_result_count,
                    (SELECT COUNT(*) FROM human_reviews review
                     WHERE review.response_id=response.response_id AND review.is_current=TRUE) AS human_review_count
             FROM rag_responses response
             JOIN evaluation_runs run ON run.run_id=response.run_id
             LEFT JOIN evaluator_results result ON result.response_id=response.response_id
             LEFT JOIN evaluator_definitions definition ON definition.evaluator_id=result.evaluator_id
             GROUP BY response.response_id ORDER BY response.response_id DESC LIMIT 250"
        )->fetchAll();

        $metricSummaries = normalizeJsonColumns($database->query(
            "SELECT definition.evaluator_key, definition.display_name, definition.family,
                    definition.dimension, definition.configuration_json,
                    COUNT(result.result_id) AS result_count,
                    SUM(result.status='completed') AS completed_count,
                    SUM(result.status='skipped') AS skipped_count,
                    SUM(result.status='failed') AS failed_count,
                    AVG(CASE WHEN result.status='completed' THEN result.normalized_score END) AS mean_score,
                    MIN(CASE WHEN result.status='completed' THEN result.normalized_score END) AS min_score,
                    MAX(CASE WHEN result.status='completed' THEN result.normalized_score END) AS max_score,
                    MAX(COALESCE(attempt_summary.attempt_count, 0)) AS attempt_count,
                    MAX(COALESCE(attempt_summary.mean_runtime_ms, 0)) AS mean_runtime_ms,
                    MAX(COALESCE(attempt_summary.estimated_cost, 0)) AS estimated_cost
             FROM evaluator_definitions definition
             LEFT JOIN evaluator_results result ON result.evaluator_id=definition.evaluator_id
             LEFT JOIN (
                 SELECT evaluator_id, COUNT(*) AS attempt_count,
                        AVG(COALESCE(runtime_ms, 0)) AS mean_runtime_ms,
                        SUM(COALESCE(estimated_cost, 0)) AS estimated_cost
                 FROM evaluator_result_attempts GROUP BY evaluator_id
             ) attempt_summary ON attempt_summary.evaluator_id=definition.evaluator_id
             WHERE definition.is_active=TRUE
             GROUP BY definition.evaluator_id ORDER BY definition.evaluator_id"
        )->fetchAll(), ['configuration_json']);
        foreach ($metricSummaries as &$summary) {
            $summary['layer'] = $summary['configuration_json']['layer'] ?? 'baseline';
        }
        unset($summary);

        $layers = ['baseline' => 0, 'advanced' => 0];
        foreach ($evaluators as $evaluator) {
            $layer = (string) $evaluator['layer'];
            $layers[$layer] = ($layers[$layer] ?? 0) + 1;
        }
        $humanReviewCount = (int) $database->query(
            "SELECT COUNT(*) FROM human_reviews WHERE is_current=TRUE"
        )->fetchColumn();
        $findings = [
            'layers' => $layers,
            'human_review_count' => $humanReviewCount,
            'metric_summaries' => $metricSummaries,
            'interpretation_rules' => [
                'Metrics inspect one saved answer independently; they do not vote on the answer.',
                'Project-defined thresholds create review flags, not factual verdicts.',
                'Skipped and failed evaluators are excluded from score summaries.',
                'Conclusions apply only to the stored dataset, corpus, models, and settings.',
            ],
        ];

        evaluationResponse(200, ['ok' => true, 'data' => compact(
            'dataset', 'questions', 'evaluators', 'runs', 'responses', 'findings'
        )]);
    }

    if ($method === 'POST') {
        $payload = json_decode(file_get_contents('php://input') ?: '{}', true, 8, JSON_THROW_ON_ERROR);
        if (($payload['action'] ?? '') !== 'human_review') {
            evaluationResponse(422, ['ok' => false, 'error' => 'A supported action is required.']);
        }
        $responseId = filter_var($payload['response_id'] ?? null, FILTER_VALIDATE_INT);
        $reviewer = trim((string) ($payload['reviewer_alias'] ?? ''));
        $decision = (string) ($payload['overall_decision'] ?? '');
        $failureCategory = trim((string) ($payload['failure_category'] ?? ''));
        $notes = trim((string) ($payload['notes'] ?? ''));
        $allowedDecisions = ['acceptable', 'needs_revision', 'incorrect', 'not_applicable'];
        $allowedFailures = [
            '', 'none', 'ingestion_parsing', 'expected_data', 'retrieval_miss',
            'source_ranked_low', 'insufficient_context', 'unsupported_generation',
            'incomplete_answer', 'incorrect_answer', 'incorrect_refusal',
            'over_refusal', 'misleading_metric', 'evaluator_failure', 'ambiguous_question',
        ];
        if (!$responseId || $reviewer === '' || strlen($reviewer) > 120
            || !in_array($decision, $allowedDecisions, true)
            || !in_array($failureCategory, $allowedFailures, true)
            || strlen($notes) > 5000) {
            evaluationResponse(422, ['ok' => false, 'error' => 'Review fields are invalid.']);
        }
        $ratings = [
            'correctness' => validatedRating($payload['correctness'] ?? null, 'Correctness'),
            'completeness' => validatedRating($payload['completeness'] ?? null, 'Completeness'),
            'faithfulness' => validatedRating($payload['faithfulness'] ?? null, 'Faithfulness'),
            'relevance' => validatedRating($payload['relevance'] ?? null, 'Relevance'),
            'refusal_correctness' => validatedRating($payload['refusal_correctness'] ?? null, 'Refusal correctness'),
        ];
        $database->beginTransaction();
        try {
            $statement = $database->prepare(
                'SELECT 1 FROM rag_responses WHERE response_id=? FOR UPDATE'
            );
            $statement->execute([$responseId]);
            if (!$statement->fetchColumn()) {
                $database->rollBack();
                evaluationResponse(404, ['ok' => false, 'error' => 'Saved response was not found.']);
            }
            $statement = $database->prepare(
                'UPDATE human_reviews SET is_current=FALSE WHERE response_id=? AND reviewer_alias=? AND is_current=TRUE'
            );
            $statement->execute([$responseId, $reviewer]);
            $statement = $database->prepare(
                "INSERT INTO human_reviews
                 (response_id, reviewer_alias, rubric_version, correctness,
                  completeness, faithfulness, relevance, refusal_correctness,
                  overall_decision, failure_category, notes)
                 VALUES (?,?, '1.0', ?,?,?,?,?,?,?,?)"
            );
            $statement->execute([
                $responseId, $reviewer, $ratings['correctness'], $ratings['completeness'],
                $ratings['faithfulness'], $ratings['relevance'], $ratings['refusal_correctness'],
                $decision, $failureCategory === '' || $failureCategory === 'none' ? null : $failureCategory,
                $notes === '' ? null : $notes,
            ]);
            $reviewId = (int) $database->lastInsertId();
            $database->commit();
        } catch (Throwable $error) {
            if ($database->inTransaction()) {
                $database->rollBack();
            }
            throw $error;
        }
        evaluationResponse(201, ['ok' => true, 'data' => ['review_id' => $reviewId]]);
    }

    if ($method !== 'PATCH') {
        header('Allow: GET, POST, PATCH');
        evaluationResponse(405, ['ok' => false, 'error' => 'Use GET, POST, or PATCH for evaluation data.']);
    }

    $payload = json_decode(file_get_contents('php://input') ?: '{}', true, 8, JSON_THROW_ON_ERROR);
    $questionId = filter_var($payload['question_id'] ?? null, FILTER_VALIDATE_INT);
    $status = is_string($payload['review_status'] ?? null) ? $payload['review_status'] : '';
    if (!$questionId || !in_array($status, ['draft', 'reviewed', 'needs_revision'], true)) {
        evaluationResponse(422, ['ok' => false, 'error' => 'A valid question and review status are required.']);
    }
    $statement = $database->prepare('UPDATE evaluation_questions SET review_status = ? WHERE question_id = ?');
    $statement->execute([$status, $questionId]);
    if ($statement->rowCount() !== 1) {
        evaluationResponse(404, ['ok' => false, 'error' => 'Evaluation question was not found or already has that status.']);
    }
    evaluationResponse(200, ['ok' => true, 'data' => ['question_id' => (int) $questionId, 'review_status' => $status]]);
} catch (JsonException) {
    evaluationResponse(400, ['ok' => false, 'error' => 'Request body must contain valid JSON.']);
} catch (Throwable $error) {
    error_log('Evaluations endpoint failure: ' . $error->getMessage());
    evaluationResponse(500, ['ok' => false, 'error' => 'Evaluation data could not be loaded.']);
}
