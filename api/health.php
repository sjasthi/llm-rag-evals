<?php

declare(strict_types=1);

require_once dirname(__DIR__) . '/config/database.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function healthResponse(int $status, array $payload): never
{
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    exit;
}

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'GET') {
    header('Allow: GET');
    healthResponse(405, ['ok' => false, 'error' => 'Use GET to check application readiness.']);
}

try {
    $database = databaseConnection();
    $database->query('SELECT 1')->fetchColumn();
    healthResponse(200, [
        'ok' => true,
        'data' => [
            'status' => 'ready',
            'message' => 'Application data is ready.',
        ],
    ]);
} catch (Throwable $error) {
    error_log('Application health check failed: ' . $error->getMessage());
    healthResponse(503, [
        'ok' => false,
        'data' => ['status' => 'unavailable'],
        'error' => 'Application data is temporarily unavailable. Try again shortly or contact the application administrator.',
    ]);
}
