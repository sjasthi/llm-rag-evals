<?php

declare(strict_types=1);

require_once dirname(__DIR__) . '/config/database.php';

const EXPORT_SCHEMA_VERSION = '1.0';

function exportError(int $status, string $message): never
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode(['ok' => false, 'error' => $message], JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    exit;
}

function decodedExportValue(mixed $value): mixed
{
    if (!is_string($value) || trim($value) === '') {
        return $value;
    }
    try {
        return json_decode($value, true, 64, JSON_THROW_ON_ERROR);
    } catch (JsonException) {
        return $value;
    }
}

function decodeExportColumns(array $rows, array $columns): array
{
    foreach ($rows as &$row) {
        foreach ($columns as $column) {
            if (array_key_exists($column, $row)) {
                $row[$column] = decodedExportValue($row[$column]);
            }
        }
    }
    unset($row);
    return $rows;
}

function exportFilename(array $run, string $extension): string
{
    $slug = preg_replace('/[^a-z0-9]+/i', '-', (string) $run['run_name']);
    $slug = trim(strtolower((string) $slug), '-');
    if ($slug === '') {
        $slug = 'evaluation-run';
    }
    return sprintf('%s-run-%d.%s', substr($slug, 0, 70), (int) $run['run_id'], $extension);
}

function loadRunExport(PDO $database, int $runId): ?array
{
    $statement = $database->prepare(
        "SELECT run.run_id, run.run_name, run.status, run.baseline_run_id,
                run.experiment_key, run.corpus_variant_key, run.run_configuration_json,
                run.notes, run.started_at, run.completed_at, run.created_at,
                dataset.dataset_id, dataset.dataset_name, dataset.version AS dataset_version,
                settings.setting_id, settings.setting_name, settings.retrieval_method,
                settings.llm_provider, settings.chat_model, settings.embedding_model,
                settings.chunk_size, settings.chunk_overlap, settings.top_k,
                settings.temperature, settings.top_p
         FROM evaluation_runs run
         JOIN model_settings settings ON settings.setting_id=run.setting_id
         LEFT JOIN evaluation_datasets dataset ON dataset.dataset_id=run.dataset_id
         WHERE run.run_id=?"
    );
    $statement->execute([$runId]);
    $run = $statement->fetch();
    if (!$run) {
        return null;
    }
    $run['run_configuration_json'] = decodedExportValue($run['run_configuration_json']);

    $statement = $database->prepare(
        "SELECT response.response_id, response.question_id,
                membership.display_order AS dataset_question_number,
                response.question_text, response.answer_text, response.retrieval_method,
                response.latency_ms, response.estimated_cost, response.input_tokens,
                response.output_tokens, response.total_tokens,
                response.generation_cost_status, response.generation_metadata_json,
                response.evaluation_snapshot_json, response.snapshot_provenance,
                response.code_version, response.created_at
         FROM rag_responses response
         LEFT JOIN evaluation_question_memberships membership
           ON membership.dataset_id=? AND membership.question_id=response.question_id
         WHERE response.run_id=?
         ORDER BY COALESCE(membership.display_order, 2147483647), response.response_id"
    );
    $statement->execute([(int) ($run['dataset_id'] ?? 0), $runId]);
    $responses = decodeExportColumns(
        $statement->fetchAll(),
        ['generation_metadata_json', 'evaluation_snapshot_json']
    );
    $responseIds = array_map(static fn(array $row): int => (int) $row['response_id'], $responses);

    $contextsByResponse = [];
    $resultsByResponse = [];
    $attemptsByResponse = [];
    $reviewsByResponse = [];
    if ($responseIds !== []) {
        $placeholders = implode(',', array_fill(0, count($responseIds), '?'));

        $statement = $database->prepare(
            "SELECT context.response_id, context.context_id, context.rank_position,
                    context.source_path_snapshot, context.category_snapshot,
                    context.chunk_index_snapshot, context.document_hash_snapshot,
                    context.chunk_hash_snapshot, context.similarity_score,
                    context.semantic_distance, context.lexical_score,
                    context.retrieval_score, context.retrieval_metadata_json,
                    context.context_excerpt
             FROM retrieved_contexts context
             WHERE context.response_id IN ($placeholders)
             ORDER BY context.response_id, context.rank_position"
        );
        $statement->execute($responseIds);
        foreach (decodeExportColumns($statement->fetchAll(), ['retrieval_metadata_json']) as $context) {
            $contextsByResponse[(int) $context['response_id']][] = $context;
        }

        $statement = $database->prepare(
            "SELECT result.response_id, result.result_id, definition.evaluator_key,
                    definition.display_name, definition.family, definition.dimension,
                    definition.version, definition.configuration_json,
                    definition.is_local, definition.is_deterministic,
                    result.status, result.raw_score, result.normalized_score,
                    result.passed, result.explanation, result.details_json,
                    result.runtime_ms, result.estimated_cost, result.error_message,
                    result.created_at, result.updated_at
             FROM evaluator_results result
             JOIN evaluator_definitions definition ON definition.evaluator_id=result.evaluator_id
             WHERE result.response_id IN ($placeholders)
             ORDER BY result.response_id, definition.evaluator_id"
        );
        $statement->execute($responseIds);
        foreach (decodeExportColumns($statement->fetchAll(), ['configuration_json', 'details_json']) as $result) {
            $resultsByResponse[(int) $result['response_id']][] = $result;
        }

        $statement = $database->prepare(
            "SELECT attempt.response_id, attempt.attempt_id, attempt.attempt_number,
                    definition.evaluator_key, definition.display_name,
                    definition.version, attempt.status, attempt.raw_score,
                    attempt.normalized_score, attempt.passed, attempt.explanation,
                    attempt.details_json, attempt.configuration_json,
                    attempt.raw_provider_output, attempt.input_tokens,
                    attempt.output_tokens, attempt.total_tokens, attempt.runtime_ms,
                    attempt.estimated_cost, attempt.error_message, attempt.created_at
             FROM evaluator_result_attempts attempt
             JOIN evaluator_definitions definition ON definition.evaluator_id=attempt.evaluator_id
             WHERE attempt.response_id IN ($placeholders)
             ORDER BY attempt.response_id, definition.evaluator_id, attempt.attempt_number"
        );
        $statement->execute($responseIds);
        foreach (decodeExportColumns($statement->fetchAll(), ['details_json', 'configuration_json']) as $attempt) {
            $attemptsByResponse[(int) $attempt['response_id']][] = $attempt;
        }

        $statement = $database->prepare(
            "SELECT response_id, review_id, reviewer_alias, rubric_version,
                    correctness, completeness, faithfulness, relevance,
                    refusal_correctness, overall_decision, failure_category,
                    notes, is_current, reviewed_at, updated_at
             FROM human_reviews
             WHERE response_id IN ($placeholders)
             ORDER BY response_id, reviewed_at, review_id"
        );
        $statement->execute($responseIds);
        foreach ($statement->fetchAll() as $review) {
            $reviewsByResponse[(int) $review['response_id']][] = $review;
        }
    }

    foreach ($responses as &$response) {
        $responseId = (int) $response['response_id'];
        $response['contexts'] = $contextsByResponse[$responseId] ?? [];
        $response['results'] = $resultsByResponse[$responseId] ?? [];
        $response['attempts'] = $attemptsByResponse[$responseId] ?? [];
        $response['human_reviews'] = $reviewsByResponse[$responseId] ?? [];
    }
    unset($response);

    $statement = $database->prepare(
        "SELECT comparison_run.run_id AS comparison_run_id,
                comparison_run.run_name AS comparison_run_name,
                baseline_run.run_id AS baseline_run_id,
                baseline_run.run_name AS baseline_run_name,
                comparison_run.experiment_key,
                definition.evaluator_key, definition.display_name,
                COUNT(*) AS paired_question_count,
                AVG(baseline_result.normalized_score) AS baseline_mean,
                AVG(comparison_result.normalized_score) AS comparison_mean,
                AVG(comparison_result.normalized_score - baseline_result.normalized_score) AS mean_delta
         FROM evaluation_runs comparison_run
         JOIN evaluation_runs baseline_run ON baseline_run.run_id=comparison_run.baseline_run_id
         JOIN rag_responses comparison_response
           ON comparison_response.run_id=comparison_run.run_id
          AND comparison_response.question_id IS NOT NULL
         JOIN rag_responses baseline_response
           ON baseline_response.run_id=baseline_run.run_id
          AND baseline_response.question_id=comparison_response.question_id
         JOIN evaluator_results comparison_result
           ON comparison_result.response_id=comparison_response.response_id
          AND comparison_result.status='completed'
         JOIN evaluator_results baseline_result
           ON baseline_result.response_id=baseline_response.response_id
          AND baseline_result.evaluator_id=comparison_result.evaluator_id
          AND baseline_result.status='completed'
         JOIN evaluator_definitions definition ON definition.evaluator_id=comparison_result.evaluator_id
         WHERE comparison_run.status='completed' AND baseline_run.status='completed'
           AND (comparison_run.run_id=? OR baseline_run.run_id=?)
         GROUP BY comparison_run.run_id, baseline_run.run_id, definition.evaluator_id
         ORDER BY comparison_run.run_id DESC, definition.evaluator_id"
    );
    $statement->execute([$runId, $runId]);

    return [
        'export_schema_version' => EXPORT_SCHEMA_VERSION,
        'exported_at' => gmdate('c'),
        'run' => $run,
        'responses' => $responses,
        'matched_comparisons' => $statement->fetchAll(),
    ];
}

function csvScalar(mixed $value): string|int|float|null
{
    if (is_array($value) || is_object($value)) {
        return json_encode(
            $value,
            JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR
        );
    }
    if (is_bool($value)) {
        return $value ? 1 : 0;
    }
    return $value;
}

function outputCsv(array $export): never
{
    $run = $export['run'];
    $filename = exportFilename($run, 'csv');
    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename="' . $filename . '"');
    header('Cache-Control: no-store');
    $output = fopen('php://output', 'wb');
    if ($output === false) {
        exportError(500, 'The export stream could not be opened.');
    }
    fwrite($output, "\xEF\xBB\xBF");
    $headers = [
        'run_id', 'run_name', 'run_status', 'dataset_name', 'dataset_version',
        'experiment_key', 'baseline_run_id', 'corpus_variant', 'retrieval_method',
        'chat_model', 'embedding_model', 'chunk_size', 'chunk_overlap', 'top_k',
        'temperature', 'top_p', 'run_configuration', 'response_id',
        'dataset_question_number', 'question_id', 'question', 'expected_answer',
        'expected_source', 'expected_evidence', 'is_answerable',
        'generated_answer', 'snapshot_provenance',
        'latency_ms', 'generation_tokens', 'generation_cost', 'generation_cost_status',
        'retrieved_sources', 'evaluator_key', 'evaluator_name', 'evaluator_version',
        'evaluator_family', 'evaluator_dimension', 'result_status', 'raw_score',
        'normalized_score', 'above_review_threshold', 'result_explanation',
        'result_runtime_ms', 'result_cost', 'result_error', 'current_human_reviews',
        'matched_comparisons',
    ];
    fputcsv($output, $headers, ',', '"', '');

    foreach ($export['responses'] as $response) {
        $results = $response['results'] !== [] ? $response['results'] : [null];
        $snapshot = is_array($response['evaluation_snapshot_json'])
            ? $response['evaluation_snapshot_json']
            : [];
        $sourceSummary = array_map(
            static fn(array $context): array => [
                'rank' => (int) $context['rank_position'],
                'source' => $context['source_path_snapshot'],
                'chunk_index' => $context['chunk_index_snapshot'],
                'retrieval_score' => $context['retrieval_score'],
            ],
            $response['contexts']
        );
        $currentReviews = array_values(array_filter(
            $response['human_reviews'],
            static fn(array $review): bool => (bool) $review['is_current']
        ));
        foreach ($results as $result) {
            $row = [
                $run['run_id'], $run['run_name'], $run['status'], $run['dataset_name'],
                $run['dataset_version'], $run['experiment_key'], $run['baseline_run_id'],
                $run['corpus_variant_key'], $run['retrieval_method'], $run['chat_model'],
                $run['embedding_model'], $run['chunk_size'], $run['chunk_overlap'],
                $run['top_k'], $run['temperature'], $run['top_p'],
                $run['run_configuration_json'],
                $response['response_id'], $response['dataset_question_number'],
                $response['question_id'], $response['question_text'],
                $snapshot['expected_answer'] ?? null,
                $snapshot['expected_source'] ?? null,
                $snapshot['expected_evidence'] ?? null,
                $snapshot['is_answerable'] ?? null,
                $response['answer_text'],
                $response['snapshot_provenance'], $response['latency_ms'],
                $response['total_tokens'], $response['estimated_cost'],
                $response['generation_cost_status'], $sourceSummary,
                $result['evaluator_key'] ?? null, $result['display_name'] ?? null,
                $result['version'] ?? null, $result['family'] ?? null,
                $result['dimension'] ?? null, $result['status'] ?? 'not_run',
                $result['raw_score'] ?? null, $result['normalized_score'] ?? null,
                $result['passed'] ?? null, $result['explanation'] ?? null,
                $result['runtime_ms'] ?? null, $result['estimated_cost'] ?? null,
                $result['error_message'] ?? null, $currentReviews,
                $export['matched_comparisons'],
            ];
            fputcsv($output, array_map('csvScalar', $row), ',', '"', '');
        }
    }
    fclose($output);
    exit;
}

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'GET') {
    header('Allow: GET');
    exportError(405, 'Use GET to download evaluation evidence.');
}

$runId = filter_input(INPUT_GET, 'run_id', FILTER_VALIDATE_INT);
$format = strtolower(trim((string) ($_GET['format'] ?? 'json')));
if (!$runId || !in_array($format, ['json', 'csv'], true)) {
    exportError(422, 'Choose a saved run and JSON or CSV format.');
}

try {
    $export = loadRunExport(databaseConnection(), (int) $runId);
    if ($export === null) {
        exportError(404, 'The saved run was not found.');
    }
    if ($format === 'csv') {
        outputCsv($export);
    }

    header('Content-Type: application/json; charset=utf-8');
    header('Content-Disposition: attachment; filename="' . exportFilename($export['run'], 'json') . '"');
    header('Cache-Control: no-store');
    echo json_encode($export, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);
} catch (Throwable $error) {
    error_log('Evaluation export failure: ' . $error->getMessage());
    exportError(500, 'Evaluation evidence could not be exported.');
}
