<?php

declare(strict_types=1);

/**
 * Development-server router for RAG EVAL 2.0.
 *
 * Start with:
 * php -S localhost:8000 -t . router.php
 */

$path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);
$path = is_string($path) ? $path : '/';

$decodedPath = rawurldecode($path);
$normalizedPath = str_replace('\\', '/', $decodedPath);

$segments = explode('/', trim($normalizedPath, '/'));

$blockedDirectories = [
    'storage',
    'config',
    'database',
    'rag',
    'backups',
    'data',
    'docs',
    'demo',
    'includes',
    'scripts',
    'tests',
    'test_image_pdf',
    'test_pdf_ingestion',
    '.venv',
    '.git',
    '__pycache__',
];

$blocked = false;

foreach ($segments as $segment) {
    if (
        $segment === '.' ||
        $segment === '..' ||
        str_starts_with($segment, '.')
    ) {
        $blocked = true;
        break;
    }
}

if (
    in_array($segments[0] ?? '', $blockedDirectories, true) ||
    in_array($normalizedPath, [
        '/router.php',
        '/api/evaluation_diagnostics.php',
        '/api/evaluation_process.php',
    ], true)
) {
    $blocked = true;
}

if (preg_match('/\.(?:env|ini|log|py|sql|bak|sqlite|db)$/i', $normalizedPath)) {
    $blocked = true;
}

if ($blocked) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=utf-8');
    echo 'Forbidden';
    return true;
}

return false;
