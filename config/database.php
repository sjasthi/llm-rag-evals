<?php

declare(strict_types=1);

require_once __DIR__ . '/env.php';

loadEnv();

function databaseConfig(): array
{
    return [
        'host' => envValue('DB_HOST', '127.0.0.1'),
        'port' => envValue('DB_PORT', '3306'),
        'name' => envValue('DB_NAME', 'llm_rag_evals'),
        'user' => envValue('DB_USER', 'root'),
        'password' => envValue('DB_PASSWORD', ''),
        'charset' => 'utf8mb4',
    ];
}

function databaseConnection(): PDO
{
    $config = databaseConfig();
    $dsn = sprintf(
        'mysql:host=%s;port=%s;dbname=%s;charset=%s',
        $config['host'],
        $config['port'],
        $config['name'],
        $config['charset']
    );

    return new PDO($dsn, $config['user'], $config['password'], [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
    ]);
}
