<?php

declare(strict_types=1);

require_once dirname(__DIR__) . '/config/env.php';

loadEnv();

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

const TEST_RUN_TIMEOUT_SECONDS = 300;

function testRunResponse(int $status, array $payload): never
{
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    exit;
}

function testRunUserError(string $technicalError): string
{
    error_log('Browser test-run process failed: ' . $technicalError);
    $fallback = 'The test run could not be completed. Any answer saved before the interruption remains available in Evaluation. Try again or contact the application administrator.';
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

function runTestCommand(array $payload): array
{
    $action = (string) ($payload['action'] ?? '');
    $datasetId = filter_var($payload['dataset_id'] ?? null, FILTER_VALIDATE_INT);
    $name = trim((string) ($payload['name'] ?? ''));
    $maxResponses = max(1, (int) envValue('MAX_TEST_RUN_RESPONSES', '5'));
    $rawQuestionIds = $payload['question_ids'] ?? [];
    if (!is_array($rawQuestionIds)) {
        testRunResponse(422, ['ok' => false, 'error' => 'Choose reviewed questions from the Gold Standard.']);
    }
    $questionIds = [];
    foreach ($rawQuestionIds as $rawQuestionId) {
        $questionId = filter_var($rawQuestionId, FILTER_VALIDATE_INT);
        if ($questionId === false || (int) $questionId <= 0) {
            testRunResponse(422, ['ok' => false, 'error' => 'One selected Gold Standard question is invalid.']);
        }
        $questionIds[] = (int) $questionId;
    }
    if (count($questionIds) !== count(array_unique($questionIds))) {
        testRunResponse(422, ['ok' => false, 'error' => 'Choose each reviewed question only once.']);
    }
    $limit = count($questionIds);
    $retrieval = (string) ($payload['retrieval_method'] ?? 'chroma_vector');
    $topK = filter_var(
        $payload['top_k'] ?? 3,
        FILTER_VALIDATE_INT,
        ['options' => ['min_range' => 1, 'max_range' => 10]]
    );
    $temperature = filter_var($payload['temperature'] ?? 0.0, FILTER_VALIDATE_FLOAT);
    $topP = filter_var($payload['top_p'] ?? 0.9, FILTER_VALIDATE_FLOAT);
    $model = trim((string) ($payload['model'] ?? ''));
    $experimentMode = trim((string) ($payload['experiment_mode'] ?? 'standalone'));
    $experimentKey = trim((string) ($payload['experiment_key'] ?? ''));
    $baselineRunId = null;
    if (($payload['baseline_run_id'] ?? null) !== null && ($payload['baseline_run_id'] ?? '') !== '') {
        $validatedBaselineRunId = filter_var($payload['baseline_run_id'], FILTER_VALIDATE_INT);
        $baselineRunId = $validatedBaselineRunId === false ? false : (int) $validatedBaselineRunId;
    }
    $controlledVariable = trim((string) ($payload['controlled_variable'] ?? ''));
    $changeFromBaseline = trim((string) ($payload['change_from_baseline'] ?? ''));
    $corpusVariantKey = trim((string) ($payload['corpus_variant_key'] ?? 'full_current'));
    $rawCategories = $payload['categories'] ?? [];
    if (!is_array($rawCategories)) {
        testRunResponse(422, ['ok' => false, 'error' => 'Choose source categories from the application.']);
    }
    $categories = [];
    foreach ($rawCategories as $category) {
        if (!is_string($category) || preg_match('/^[a-z0-9][a-z0-9_-]{1,49}$/', $category) !== 1) {
            testRunResponse(422, ['ok' => false, 'error' => 'One selected source category is invalid. Refresh the page and try again.']);
        }
        $categories[] = $category;
    }
    $categories = array_values(array_unique($categories));
    sort($categories);
    $allowedModels = array_values(array_unique(array_filter(array_map(
        'trim',
        explode(',', (string) envValue('LLM_CHAT_MODELS', (string) envValue('LLM_CHAT_MODEL', 'gemini-2.5-flash')))
    ))));

    if (!in_array($action, ['preflight', 'create'], true)) {
        testRunResponse(422, ['ok' => false, 'error' => 'Choose Preview test or Generate test.']);
    }
    if (!$datasetId || $limit < 1 || $limit > $maxResponses) {
        testRunResponse(422, [
            'ok' => false,
            'error' => "Choose between 1 and {$maxResponses} exact reviewed questions.",
        ]);
    }
    if ($name === '' || strlen($name) > 120) {
        testRunResponse(422, ['ok' => false, 'error' => 'Give the saved test a name of 1 to 120 characters.']);
    }
    if (!in_array($retrieval, ['chroma_vector', 'mysql_keyword'], true)) {
        testRunResponse(422, ['ok' => false, 'error' => 'Choose vector or keyword retrieval.']);
    }
    if ($topK === false || $temperature === false || $topP === false) {
        testRunResponse(422, ['ok' => false, 'error' => 'Choose valid generation settings.']);
    }
    if ($temperature < 0.0 || $temperature > 1.0 || $topP < 0.0 || $topP > 1.0) {
        testRunResponse(422, ['ok' => false, 'error' => 'Temperature and top-p must be between 0.0 and 1.0.']);
    }
    if ($model === '' || !in_array($model, $allowedModels, true)) {
        testRunResponse(422, ['ok' => false, 'error' => 'Choose a deployment-approved model.']);
    }
    if (!in_array($experimentMode, ['standalone', 'baseline', 'comparison'], true)) {
        testRunResponse(422, ['ok' => false, 'error' => 'Choose a quick test, controlled baseline, or baseline comparison.']);
    }
    if (strlen($experimentKey) > 120) {
        testRunResponse(422, ['ok' => false, 'error' => 'Keep the experiment label to 120 characters or fewer.']);
    }
    if (preg_match('/^[a-z0-9][a-z0-9_-]{1,119}$/', $corpusVariantKey) !== 1) {
        testRunResponse(422, ['ok' => false, 'error' => 'The selected source collection could not be identified. Refresh the page and try again.']);
    }
    if (count($categories) > 50) {
        testRunResponse(422, ['ok' => false, 'error' => 'Choose no more than 50 source categories in one test.']);
    }
    $allowedControlledVariables = ['retrieval_method', 'top_k', 'model', 'temperature', 'top_p', 'corpus'];
    if ($experimentMode === 'standalone') {
        if ($baselineRunId !== null || $controlledVariable !== '' || $changeFromBaseline !== '') {
            testRunResponse(422, ['ok' => false, 'error' => 'A standalone test cannot be attached to a comparison baseline.']);
        }
    } elseif ($experimentMode === 'baseline') {
        if ($experimentKey === '') {
            testRunResponse(422, ['ok' => false, 'error' => 'Give the controlled experiment a short label.']);
        }
        if ($baselineRunId !== null || $controlledVariable !== '' || $changeFromBaseline !== '') {
            testRunResponse(422, ['ok' => false, 'error' => 'A baseline starts an experiment and cannot reference another baseline.']);
        }
    } else {
        if ($experimentKey === '' || !is_int($baselineRunId) || $baselineRunId <= 0) {
            testRunResponse(422, ['ok' => false, 'error' => 'Choose a completed baseline and label the experiment.']);
        }
        if (!in_array($controlledVariable, $allowedControlledVariables, true)) {
            testRunResponse(422, ['ok' => false, 'error' => 'Choose the one setting changed from the baseline.']);
        }
        if ($changeFromBaseline === '' || strlen($changeFromBaseline) > 500) {
            testRunResponse(422, ['ok' => false, 'error' => 'The comparison must describe its one changed setting.']);
        }
    }

    $root = projectRoot();
    $python = envValue('PYTHON_BIN', $root . '/.venv/Scripts/python.exe');
    if (!is_string($python) || !is_file($python)) {
        throw new RuntimeException('Project Python environment was not found.');
    }
    $command = [
        $python,
        $root . '/rag/run_evaluation.py',
        '--dataset-id',
        (string) $datasetId,
        '--name',
        $name,
        '--limit',
        (string) $limit,
        '--question-ids',
        implode(',', $questionIds),
        '--retrieval',
        $retrieval,
        '--top-k',
        (string) $topK,
        '--model',
        $model,
        '--temperature',
        (string) $temperature,
        '--top-p',
        (string) $topP,
        '--max-responses',
        (string) $maxResponses,
        '--max-estimated-cost',
        (string) envValue('MAX_GENERATION_COST', '0.25'),
        '--json',
    ];
    if ($experimentKey !== '') {
        $command[] = '--experiment-key';
        $command[] = $experimentKey;
    }
    $command[] = '--corpus-variant';
    $command[] = $corpusVariantKey;
    if ($categories !== []) {
        $command[] = '--categories';
        $command[] = implode(',', $categories);
    }
    if (is_int($baselineRunId)) {
        $command[] = '--baseline-run-id';
        $command[] = (string) $baselineRunId;
        $command[] = '--change-from-baseline';
        $command[] = $changeFromBaseline;
    }
    if ($action === 'preflight') {
        $command[] = '--dry-run';
    } else {
        if (filter_var(envValue('ALLOW_PAID_GENERATION', '0'), FILTER_VALIDATE_BOOLEAN)) {
            $command[] = '--allow-paid';
        }
        if (filter_var(envValue('ALLOW_UNKNOWN_GENERATION_COST', '0'), FILTER_VALIDATE_BOOLEAN)) {
            $command[] = '--allow-unknown-cost';
        }
    }

    $process = proc_open(
        $command,
        [0 => ['pipe', 'r'], 1 => ['pipe', 'w'], 2 => ['pipe', 'w']],
        $pipes,
        $root,
        null,
        ['bypass_shell' => true]
    );
    if (!is_resource($process)) {
        throw new RuntimeException('Could not start the test-run process.');
    }
    fclose($pipes[0]);
    stream_set_blocking($pipes[1], false);
    stream_set_blocking($pipes[2], false);
    $stdout = '';
    $stderr = '';
    $startedAt = microtime(true);
    $lastStatus = null;
    while (true) {
        $stdout .= stream_get_contents($pipes[1]);
        $stderr .= stream_get_contents($pipes[2]);
        $lastStatus = proc_get_status($process);
        if (!$lastStatus['running']) {
            break;
        }
        if ((microtime(true) - $startedAt) > TEST_RUN_TIMEOUT_SECONDS) {
            proc_terminate($process);
            fclose($pipes[1]);
            fclose($pipes[2]);
            proc_close($process);
            throw new RuntimeException('Test run timed out.');
        }
        usleep(100000);
    }
    $stdout .= stream_get_contents($pipes[1]);
    $stderr .= stream_get_contents($pipes[2]);
    fclose($pipes[1]);
    fclose($pipes[2]);
    $closeCode = proc_close($process);
    $exitCode = (int) ($lastStatus['exitcode'] ?? $closeCode);
    if ($exitCode !== 0) {
        testRunResponse(422, ['ok' => false, 'error' => testRunUserError(trim($stderr))]);
    }
    $result = json_decode($stdout, true, 64, JSON_THROW_ON_ERROR);
    if (!is_array($result) || !isset($result['preflight'])) {
        throw new RuntimeException('Test-run process returned incomplete data.');
    }
    return $result;
}

try {
    if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'POST') {
        header('Allow: POST');
        testRunResponse(405, ['ok' => false, 'error' => 'Use POST to preview or generate a test run.']);
    }
    try {
        $payload = json_decode(file_get_contents('php://input') ?: '{}', true, 16, JSON_THROW_ON_ERROR);
    } catch (JsonException) {
        testRunResponse(400, ['ok' => false, 'error' => 'Request body must contain valid JSON.']);
    }
    if (!is_array($payload)) {
        testRunResponse(400, ['ok' => false, 'error' => 'Request body must contain a JSON object.']);
    }
    testRunResponse(200, ['ok' => true, 'data' => runTestCommand($payload)]);
} catch (Throwable $error) {
    error_log('Browser test-run endpoint failure: ' . $error->getMessage());
    testRunResponse(500, [
        'ok' => false,
        'error' => 'New test runs are temporarily unavailable. No existing test was changed.',
    ]);
}
