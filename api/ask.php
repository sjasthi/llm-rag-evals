<?php

declare(strict_types=1);

require_once dirname(__DIR__) . '/config/env.php';

loadEnv();

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

const MAX_QUESTION_BYTES = 2000;
const ANSWER_TIMEOUT_SECONDS = 60;

function jsonResponse(int $status, array $payload): never
{
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    exit;
}

function requestPayload(): array
{
    $contentType = strtolower((string) ($_SERVER['CONTENT_TYPE'] ?? ''));

    if (str_contains($contentType, 'application/json')) {
        $rawBody = file_get_contents('php://input');
        try {
            $payload = json_decode($rawBody ?: '{}', true, 16, JSON_THROW_ON_ERROR);
        } catch (JsonException) {
            jsonResponse(400, ['ok' => false, 'error' => 'Request body must contain valid JSON.']);
        }
        if (!is_array($payload)) {
            jsonResponse(400, ['ok' => false, 'error' => 'Request body must contain a JSON object.']);
        }
        return $payload;
    }

    return $_POST;
}

function requestQuestion(array $payload): string
{
    $question = $payload['question'] ?? '';
    if (!is_string($question)) {
        jsonResponse(400, ['ok' => false, 'error' => 'Question must be text.']);
    }

    $question = trim($question);
    if ($question === '') {
        jsonResponse(422, ['ok' => false, 'error' => 'Enter a question before submitting.']);
    }
    if (strlen($question) > MAX_QUESTION_BYTES) {
        jsonResponse(422, ['ok' => false, 'error' => 'Question is too long.']);
    }

    return $question;
}

function requestConfiguration(array $payload): array
{
    $defaultModel = (string) envValue('LLM_CHAT_MODEL', 'gemini-2.5-flash');
    $allowedModels = array_values(array_unique(array_filter(array_map(
        'trim',
        explode(',', (string) envValue('LLM_CHAT_MODELS', $defaultModel . ',gemini-2.5-flash-lite'))
    ))));
    if (!in_array($defaultModel, $allowedModels, true)) {
        array_unshift($allowedModels, $defaultModel);
    }
    $model = $payload['model'] ?? $defaultModel;
    if (!is_string($model) || !in_array($model, $allowedModels, true)) {
        jsonResponse(422, ['ok' => false, 'error' => 'Choose a model offered by this deployment.']);
    }

    $retrievalMethod = $payload['retrieval_method'] ?? 'chroma_vector';
    if (!is_string($retrievalMethod) || !in_array($retrievalMethod, ['chroma_vector', 'mysql_keyword'], true)) {
        jsonResponse(422, ['ok' => false, 'error' => 'Choose vector or keyword retrieval.']);
    }

    $topK = filter_var(
        $payload['top_k'] ?? envValue('RETRIEVAL_TOP_K', '3'),
        FILTER_VALIDATE_INT,
        ['options' => ['min_range' => 1, 'max_range' => 10]]
    );
    if ($topK === false) {
        jsonResponse(422, ['ok' => false, 'error' => 'Top-k must be an integer from 1 to 10.']);
    }

    $temperatureValue = $payload['temperature'] ?? envValue('LLM_TEMPERATURE', '0.0');
    $topPValue = $payload['top_p'] ?? envValue('LLM_TOP_P', '0.9');
    if (!is_numeric($temperatureValue) || (float) $temperatureValue < 0.0 || (float) $temperatureValue > 1.0) {
        jsonResponse(422, ['ok' => false, 'error' => 'Temperature must be between 0.0 and 1.0.']);
    }
    if (!is_numeric($topPValue) || (float) $topPValue < 0.0 || (float) $topPValue > 1.0) {
        jsonResponse(422, ['ok' => false, 'error' => 'Top-p must be between 0.0 and 1.0.']);
    }

    return [
        'model' => $model,
        'retrieval_method' => $retrievalMethod,
        'top_k' => (int) $topK,
        'temperature' => (float) $temperatureValue,
        'top_p' => (float) $topPValue,
    ];
}

function runAnswerCommand(string $question, array $configuration, bool $previewOnly): array
{
    $root = projectRoot();
    $python = envValue('PYTHON_BIN', $root . '/.venv/Scripts/python.exe');

    if (!is_string($python) || !is_file($python)) {
        throw new RuntimeException(
            'Project Python environment was not found. Create .venv and install rag/requirements.txt.'
        );
    }

    $command = [
        $python,
        $root . '/rag/answer.py',
        $question,
        '--model',
        (string) $configuration['model'],
        '--top-k',
        (string) $configuration['top_k'],
        '--retrieval',
        (string) $configuration['retrieval_method'],
        '--temperature',
        (string) $configuration['temperature'],
        '--top-p',
        (string) $configuration['top_p'],
        '--json',
    ];
    if ($previewOnly) {
        $command[] = '--dry-run';
    } else {
        $command[] = '--allow-paid';
        $command[] = '--max-estimated-cost';
        $command[] = (string) envValue('MAX_GENERATION_COST', '0.25');
        if (filter_var(envValue('ALLOW_UNKNOWN_GENERATION_COST', '0'), FILTER_VALIDATE_BOOLEAN)) {
            $command[] = '--allow-unknown-cost';
        }
    }
    $descriptors = [
        0 => ['pipe', 'r'],
        1 => ['pipe', 'w'],
        2 => ['pipe', 'w'],
    ];
    $pipes = [];
    $process = proc_open(
        $command,
        $descriptors,
        $pipes,
        $root,
        null,
        ['bypass_shell' => true]
    );

    if (!is_resource($process)) {
        throw new RuntimeException('Could not start the RAG answer process.');
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
        if ((microtime(true) - $startedAt) > ANSWER_TIMEOUT_SECONDS) {
            proc_terminate($process);
            fclose($pipes[1]);
            fclose($pipes[2]);
            proc_close($process);
            throw new RuntimeException('Answer generation timed out. Please try again.');
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
        $message = trim($stderr);
        throw new RuntimeException(
            $message !== '' ? $message : 'The RAG answer process failed.'
        );
    }

    try {
        $result = json_decode($stdout, true, 64, JSON_THROW_ON_ERROR);
    } catch (JsonException $error) {
        throw new RuntimeException('The RAG answer process returned invalid JSON.', 0, $error);
    }

    $hasRequiredFields = is_array($result) && ($previewOnly
        ? isset($result['question'], $result['sources'])
        : isset($result['answer'], $result['sources']));
    if (!$hasRequiredFields) {
        throw new RuntimeException('The RAG answer response was incomplete.');
    }

    return $result;
}

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'POST') {
    header('Allow: POST');
    jsonResponse(405, ['ok' => false, 'error' => 'Use POST to submit a question.']);
}

$payload = requestPayload();
$question = requestQuestion($payload);
$configuration = requestConfiguration($payload);
$action = $payload['action'] ?? 'answer';
if (!is_string($action) || !in_array($action, ['answer', 'preview'], true)) {
    jsonResponse(422, ['ok' => false, 'error' => 'Unsupported chat action.']);
}
$previewOnly = $action === 'preview';

if (!$previewOnly && !filter_var(envValue('ALLOW_PAID_GENERATION', '0'), FILTER_VALIDATE_BOOLEAN)) {
    jsonResponse(503, [
        'ok' => false,
        'error' => 'Paid answer generation is paused. Enable it deliberately in the local environment after reviewing provider pricing.',
    ]);
}

try {
    $result = runAnswerCommand($question, $configuration, $previewOnly);
    jsonResponse(200, ['ok' => true, 'data' => $result]);
} catch (Throwable $error) {
    error_log('Ask endpoint failure: ' . $error->getMessage());
    jsonResponse(500, [
        'ok' => false,
        'error' => 'The answer could not be generated. Check the server configuration and try again.',
    ]);
}
