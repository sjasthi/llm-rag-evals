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

try {
    $database = databaseConnection();
    $method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
    if ($method === 'GET') {
        $responseId = filter_input(INPUT_GET, 'response_id', FILTER_VALIDATE_INT);
        if ($responseId) {
            $statement = $database->prepare(
                "SELECT r.response_id, r.question_text, r.answer_text, r.latency_ms, r.created_at,
                        q.expected_answer, q.expected_source, q.is_answerable,
                        run.run_id, run.run_name
                 FROM rag_responses r
                 LEFT JOIN evaluation_questions q ON q.question_id = r.question_id
                 LEFT JOIN evaluation_runs run ON run.run_id = r.run_id
                 WHERE r.response_id = ?"
            );
            $statement->execute([$responseId]);
            $response = $statement->fetch();
            if (!$response) {
                evaluationResponse(404, ['ok' => false, 'error' => 'Saved response was not found.']);
            }
            $statement = $database->prepare(
                "SELECT c.rank_position, c.similarity_score, c.context_excerpt, d.source_path
                 FROM retrieved_contexts c LEFT JOIN documents d ON d.document_id=c.document_id
                 WHERE c.response_id=? ORDER BY c.rank_position"
            );
            $statement->execute([$responseId]);
            $contexts = $statement->fetchAll();
            $statement = $database->prepare(
                "SELECT e.display_name, e.evaluator_key, e.family, e.dimension, e.version,
                        er.status, er.normalized_score, er.passed, er.explanation,
                        er.details_json, er.runtime_ms, er.estimated_cost, er.error_message
                 FROM evaluator_results er
                 JOIN evaluator_definitions e ON e.evaluator_id=er.evaluator_id
                 WHERE er.response_id=? ORDER BY e.evaluator_id"
            );
            $statement->execute([$responseId]);
            evaluationResponse(200, ['ok' => true, 'data' => [
                'response' => $response,
                'contexts' => $contexts,
                'results' => $statement->fetchAll(),
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
                        q.category, q.difficulty, q.is_answerable, q.review_status,
                        m.display_order
                 FROM evaluation_question_memberships m
                 JOIN evaluation_questions q ON q.question_id = m.question_id
                 WHERE m.dataset_id = ? ORDER BY m.display_order"
            );
            $statement->execute([$dataset['dataset_id']]);
            $questions = $statement->fetchAll();
        }
        $evaluators = $database->query(
            "SELECT evaluator_key, display_name, family, dimension, version, is_local,
                    is_deterministic, description
             FROM evaluator_definitions WHERE is_active = TRUE ORDER BY evaluator_id"
        )->fetchAll();
        $runs = $database->query(
            "SELECT run.run_id, run.run_name, run.status, run.started_at, run.completed_at,
                    s.retrieval_method, s.chat_model, s.top_k,
                    COUNT(DISTINCT r.response_id) AS response_count,
                    COUNT(er.result_id) AS result_count,
                    SUM(er.status = 'failed') AS evaluator_error_count
             FROM evaluation_runs run
             JOIN model_settings s ON s.setting_id=run.setting_id
             LEFT JOIN rag_responses r ON r.run_id=run.run_id
             LEFT JOIN evaluator_results er ON er.response_id=r.response_id
             GROUP BY run.run_id ORDER BY run.run_id DESC LIMIT 10"
        )->fetchAll();
        $responses = $database->query(
            "SELECT r.response_id, r.run_id, r.question_text, r.latency_ms, r.created_at,
                    COUNT(er.result_id) AS result_count,
                    AVG(er.normalized_score) AS descriptive_average
             FROM rag_responses r
             JOIN evaluation_runs run ON run.run_id=r.run_id
             LEFT JOIN evaluator_results er ON er.response_id=r.response_id
             GROUP BY r.response_id ORDER BY r.response_id DESC LIMIT 25"
        )->fetchAll();
        evaluationResponse(200, ['ok' => true, 'data' => compact('dataset', 'questions', 'evaluators', 'runs', 'responses')]);
    }

    if ($method !== 'PATCH') {
        header('Allow: GET, PATCH');
        evaluationResponse(405, ['ok' => false, 'error' => 'Use GET or PATCH for evaluation data.']);
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
