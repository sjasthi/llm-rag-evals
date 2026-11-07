<?php
declare(strict_types=1);

require_once __DIR__ . '/evaluation_diagnostics.php';
require_once __DIR__ . '/evaluation_process.php';
require_once dirname(__DIR__) . '/config/env.php';

loadEnv();

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

const RUN_EVALUATION_TIMEOUT_SECONDS = 300;

// Allow the PHP request to wait for advanced Python evaluations.
set_time_limit(RUN_EVALUATION_TIMEOUT_SECONDS + 30);

function runEvaluationResponse(int $status, array $payload): never
{
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    exit;
}

function runEvaluationUserError(string $technicalError): string
{
    error_log('Saved-answer scoring process failed: ' . $technicalError);
    $fallback = 'Scoring could not be completed. No saved answer was regenerated or removed. Try again or contact the application administrator.';
    if (preg_match('/error:\s*([^\r\n]+)$/mi', $technicalError, $matches) === 1) {
        $message = trim($matches[1]);
        if (
            strlen($message) <= 300
            && preg_match('/api[ _-]?key|\.env|environment|traceback|mysql|database|python|chroma|gemini|file path|directory/i', $message) !== 1
        ) {
            return ucfirst($message);
        }
    }
    return $fallback;
}

function runEvaluationCommand(array $payload): array
{
    $runId = filter_var($payload['run_id'] ?? null, FILTER_VALIDATE_INT);
    $responseId = isset($payload['response_id'])
        ? filter_var($payload['response_id'], FILTER_VALIDATE_INT)
        : null;
    $limit = filter_var(
        $payload['limit'] ?? 1,
        FILTER_VALIDATE_INT,
        ['options' => ['min_range' => 1, 'max_range' => 100]]
    );
    $action = $payload['action'] ?? '';
    if (
        !$runId
        || $limit === false
        || $responseId === false
        || !in_array($action, ['preflight', 'evaluate'], true)
    ) {
        runEvaluationResponse(422, [
            'ok' => false,
            'error' => 'Choose a saved run, a response limit from 1 to 100, and a supported action.',
        ]);
    }

    $includeAdvanced = filter_var(
        $payload['include_advanced'] ?? false,
        FILTER_VALIDATE_BOOLEAN
    );
    $force = filter_var($payload['force'] ?? false, FILTER_VALIDATE_BOOLEAN);
    $root = projectRoot();
    $python = envValue('PYTHON_BIN', $root . '/.venv/Scripts/python.exe');
    if (!is_string($python) || !is_file($python)) {
        throw new RuntimeException('Project Python environment was not found.');
    }

    $command = [
        $python,
        $root . '/rag/evaluate_saved_run.py',
        '--run-id',
        (string) $runId,
        '--limit',
        (string) $limit,
        '--max-advanced-applications',
        (string) envValue('MAX_EVALUATOR_APPLICATIONS', '5'),
        '--max-estimated-cost',
        (string) envValue('MAX_EVALUATION_COST', '1.00'),
        '--json',
    ];
    if ($includeAdvanced) {
        $command[] = '--include-advanced';
    }
    if ($responseId !== null) {
        $command[] = '--response-id';
        $command[] = (string) $responseId;
    }
    if ($force) {
        $command[] = '--force';
    }
    if ($action === 'preflight') {
        $command[] = '--dry-run';
    } elseif ($includeAdvanced) {
        if (filter_var(envValue('ALLOW_PAID_EVALUATION', '0'), FILTER_VALIDATE_BOOLEAN)) {
            $command[] = '--allow-paid';
        }
        if (filter_var(envValue('ALLOW_UNKNOWN_EVALUATION_COST', '0'), FILTER_VALIDATE_BOOLEAN)) {
            $command[] = '--allow-unknown-cost';
        }
    }

    $startedAt = microtime(true);

    $execution = evaluationRunSupervisedCommand(
        $command,
        $python,
        $root,
        RUN_EVALUATION_TIMEOUT_SECONDS
    );

    $stdout = $execution['stdout'];
    $stderr = $execution['stderr'];
    $exitCode = $execution['exit_code'];

    if ($execution['timed_out']) {
        testRunDiagnosticLog('saved_answer_scoring_timeout', [
            'elapsed_seconds' => round(microtime(true) - $startedAt, 2),
            'timeout_seconds' => RUN_EVALUATION_TIMEOUT_SECONDS,
            'process_id' => null,
            'stderr_bytes' => strlen($stderr),
            'stdout_bytes' => strlen($stdout),
        ]);

        runEvaluationResponse(504, [
            'ok' => false,
            'error' => 'Scoring exceeded the 5-minute execution limit and was stopped. Previously saved answers remain available. Some scoring results may already have been saved. Check Evaluation before retrying with fewer responses.',
        ]);
    }

    if ($exitCode !== 0) {
        $errorLogFile = testRunSavePythonError($stderr);

        testRunDiagnosticLog('saved_answer_scoring_failed', [
            'exit_code' => $exitCode,
            'elapsed_seconds' => round(microtime(true) - $startedAt, 2),
            'stderr_bytes' => strlen($stderr),
            'stdout_bytes' => strlen($stdout),
            'error_log_file' => $errorLogFile,
        ]);

        runEvaluationResponse(422, [
            'ok' => false,
            'error' => runEvaluationUserError(trim($stderr)),
        ]);
    }
    $result = json_decode($stdout, true, 32, JSON_THROW_ON_ERROR);
    if (!is_array($result) || !isset($result['preflight'])) {
        throw new RuntimeException('Evaluation returned incomplete data.');
    }
    return $result;
}

try {
    if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'POST') {
        header('Allow: POST');
        runEvaluationResponse(405, ['ok' => false, 'error' => 'Use POST to evaluate a saved run.']);
    }
    try {
        $payload = json_decode(file_get_contents('php://input') ?: '{}', true, 16, JSON_THROW_ON_ERROR);
    } catch (JsonException) {
        runEvaluationResponse(400, ['ok' => false, 'error' => 'Request body must contain valid JSON.']);
    }
    if (!is_array($payload)) {
        runEvaluationResponse(400, ['ok' => false, 'error' => 'Request body must contain a JSON object.']);
    }
    runEvaluationResponse(200, ['ok' => true, 'data' => runEvaluationCommand($payload)]);
} catch (Throwable $error) {
    testRunDiagnosticLog('saved_answer_scoring_exception', [
        'exception_type' => get_class($error),
        'message_length' => strlen($error->getMessage()),
        'file' => basename($error->getFile()),
        'line' => $error->getLine(),
    ]);

    error_log('Run evaluation endpoint failure: ' . $error->getMessage());
    runEvaluationResponse(500, [
        'ok' => false,
        'error' => 'Scoring is temporarily unavailable. No saved answer was changed; try again or contact the application administrator.',
    ]);
}
