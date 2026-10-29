<?php
declare(strict_types=1);

require_once dirname(__DIR__) . '/config/env.php';
require_once dirname(__DIR__) . '/includes/standalone_preflight_validation.php';

loadEnv();

header('Content-Type: application/json; charset=utf-8');

$root = projectRoot();
$python = envValue('PYTHON_BIN', $root . '/.venv/Scripts/python.exe');

$command = [
    $python,
    $root . '/rag/run_advanced_evaluation.py',
    '--response-id', '147',
    '--evaluators', 'citation_support,citation_coverage',
    '--max-applications', '2',
    '--max-estimated-cost', '0.25',
    '--dry-run',
    '--json',
];

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
    throw new RuntimeException('Unable to start dry-run test.');
}

fclose($pipes[0]);

$stdout = stream_get_contents($pipes[1]);
$stderr = stream_get_contents($pipes[2]);

fclose($pipes[1]);
fclose($pipes[2]);

$exitCode = proc_close($process);

if ($exitCode !== 0) {
    throw new RuntimeException('Dry-run failed: ' . $stderr);
}

$result = json_decode($stdout, true, 32, JSON_THROW_ON_ERROR);
$plan = $result['preflight'] ?? null;

$valid = is_array($plan) && validateStandalonePreflight(
    $plan,
    ['citation_support', 'citation_coverage'],
    0.25
);

echo json_encode([
    'ok' => $valid,
    'response_id' => 147,
    'dry_run' => true,
    'validation_passed' => $valid,
    'estimated_cost' => $plan['estimated_cost'] ?? null,
], JSON_PRETTY_PRINT);
