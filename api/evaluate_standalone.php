<?php
declare(strict_types=1);

require_once dirname(__DIR__) . '/config/env.php';
require_once dirname(__DIR__) . '/includes/standalone_preflight_validation.php';

loadEnv();

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function standaloneResponse(int $status, array $data): never
{
    http_response_code($status);
    echo json_encode($data, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    exit;
}

function runStandalonePython(array $command, string $root): array
{
    $process = proc_open(
        $command,
        [
            0 => ['pipe', 'r'],
            1 => ['pipe', 'w'],
            2 => ['pipe', 'w'],
        ],
        $pipes,
        $root,
        null,
        ['bypass_shell' => true]
    );

    if (!is_resource($process)) {
        throw new RuntimeException('Unable to start citation scoring process.');
    }

    fclose($pipes[0]);

    $stdout = stream_get_contents($pipes[1]);
    $stderr = stream_get_contents($pipes[2]);

    fclose($pipes[1]);
    fclose($pipes[2]);

    $exitCode = proc_close($process);

    if ($exitCode !== 0) {
        error_log('Standalone citation scoring failed: ' . $stderr);

        throw new RuntimeException(
            'Citation scoring process failed with exit code ' . $exitCode
        );
    }

    $result = json_decode($stdout, true, 32, JSON_THROW_ON_ERROR);

    if (!is_array($result)) {
        throw new RuntimeException('Invalid citation scoring response.');
    }

    return $result;
}

try {
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
        header('Allow: POST');
        standaloneResponse(405, [
            'ok' => false,
            'error' => 'Use POST for standalone evaluation preflight.',
        ]);
    }

    $payload = json_decode(
        file_get_contents('php://input') ?: '{}',
        true,
        16,
        JSON_THROW_ON_ERROR
    );

    if (!is_array($payload)) {
        standaloneResponse(400, [
            'ok' => false,
            'error' => 'Expected a JSON object.',
        ]);
    }

    $responseId = filter_var(
        $payload['response_id'] ?? null,
        FILTER_VALIDATE_INT,
        ['options' => ['min_range' => 1]]
    );

    $action = $payload['action'] ?? '';

    if (!$responseId || !in_array($action, ['preflight', 'execute'], true)) {
        standaloneResponse(422, [
            'ok' => false,
            'error' => 'Provide a valid response_id and action=preflight or execute.',
        ]);
    }

    // Execution remains disabled until explicitly enabled in server configuration.
    $executionEnabled = envValue('ENABLE_STANDALONE_EVALUATION', '0') === '1';

    if ($action === 'execute') {
        if (!$executionEnabled) {
            standaloneResponse(403, [
                'ok' => false,
                'error' => 'Standalone evaluation execution is disabled.',
            ]);
        }

        if (($payload['confirm_execution'] ?? null) !== true) {
            standaloneResponse(422, [
                'ok' => false,
                'error' => 'Explicit execution confirmation is required.',
            ]);
        }
    }

    // Only these two citation evaluators are supported initially.
    $evaluatorKeys = [
        'citation_support',
        'citation_coverage',
    ];

    $root = projectRoot();
    $python = envValue(
        'PYTHON_BIN',
        $root . '/.venv/Scripts/python.exe'
    );

    if (!is_string($python) || !is_file($python)) {
        throw new RuntimeException('Python environment unavailable.');
    }

    $command = [
        $python,
        $root . '/rag/run_advanced_evaluation.py',
        '--response-id',
        (string) $responseId,
        '--evaluators',
        implode(',', $evaluatorKeys),
        '--max-applications',
        '2',
        '--max-estimated-cost',
        '0.25',
        '--json',
    ];

    // Stage 1: Always generate a fresh, read-only preflight.
    $preflightCommand = $command;
    $preflightCommand[] = '--dry-run';

    $preflightResult = runStandalonePython($preflightCommand, $root);

    if (
        !isset($preflightResult['preflight']) ||
        !is_array($preflightResult['preflight'])
    ) {
        throw new RuntimeException('Incomplete citation scoring preflight.');
    }

    // Preview requests stop here. No evaluators are executed.
    if ($action === 'preflight') {
        standaloneResponse(200, [
            'ok' => true,
            'data' => $preflightResult,
        ]);
    }

    // Stage 2: Validate the fresh plan before execution.
    $plan = $preflightResult['preflight'];

    if (!validateStandalonePreflight($plan, $evaluatorKeys, 0.25)) {
        standaloneResponse(422, [
            'ok' => false,
            'error' => 'Citation scoring plan failed server-side safety validation.',
        ]);
    }

    // Stage 3: Execute the permitted citation evaluators.
    // The execution gate and explicit confirmation were checked above.
    $executeCommand = $command;
    $executeCommand[] = '--allow-paid';

    $executionResult = runStandalonePython($executeCommand, $root);

    // Return the runner's result, including any saved evaluation metadata.
    standaloneResponse(200, [
        'ok' => true,
        'data' => $executionResult,
    ]);

} catch (JsonException) {
    standaloneResponse(400, [
        'ok' => false,
        'error' => 'Invalid JSON request or response.',
    ]);
} catch (Throwable $error) {
    error_log('Standalone evaluation endpoint: ' . $error->getMessage());

    standaloneResponse(500, [
        'ok' => false,
        'error' => 'Standalone evaluation preview is temporarily unavailable.',
    ]);
}
