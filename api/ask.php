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

function requestQuestion(): string
{
    $contentType = strtolower((string) ($_SERVER['CONTENT_TYPE'] ?? ''));

    if (str_contains($contentType, 'application/json')) {
        $rawBody = file_get_contents('php://input');
        try {
            $payload = json_decode($rawBody ?: '{}', true, 16, JSON_THROW_ON_ERROR);
        } catch (JsonException) {
            jsonResponse(400, ['ok' => false, 'error' => 'Request body must contain valid JSON.']);
        }
        $question = is_array($payload) ? ($payload['question'] ?? '') : '';
    } else {
        $question = $_POST['question'] ?? '';
    }

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

function runAnswerCommand(string $question): array
{
    $root = projectRoot();
    $python = envValue('PYTHON_BIN', $root . '/.venv/Scripts/python.exe');

    if (!is_string($python) || !is_file($python)) {
        throw new RuntimeException(
            'Project Python environment was not found. Create .venv and install rag/requirements.txt.'
        );
    }

    $topK = filter_var(
        envValue('RETRIEVAL_TOP_K', '3'),
        FILTER_VALIDATE_INT,
        ['options' => ['min_range' => 1, 'max_range' => 10]]
    );
    if ($topK === false) {
        throw new RuntimeException('RETRIEVAL_TOP_K must be an integer from 1 to 10.');
    }

    $command = [
        $python,
        $root . '/rag/answer.py',
        $question,
        '--top-k',
        (string) $topK,
        '--json',
    ];
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

    if (!is_array($result) || !isset($result['answer'], $result['sources'])) {
        throw new RuntimeException('The RAG answer response was incomplete.');
    }

    return $result;
}

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'POST') {
    header('Allow: POST');
    jsonResponse(405, ['ok' => false, 'error' => 'Use POST to submit a question.']);
}

$question = requestQuestion();

try {
    $result = runAnswerCommand($question);
    jsonResponse(200, ['ok' => true, 'data' => $result]);
} catch (Throwable $error) {
    error_log('Ask endpoint failure: ' . $error->getMessage());
    jsonResponse(500, [
        'ok' => false,
        'error' => 'The answer could not be generated. Check the server configuration and try again.',
    ]);
}
