<?php

declare(strict_types=1);

function projectRoot(): string
{
    return dirname(__DIR__);
}

function loadEnv(?string $path = null): array
{
    $path ??= projectRoot() . DIRECTORY_SEPARATOR . '.env';

    if (!is_file($path)) {
        return [];
    }

    $values = [];
    $lines = file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);

    foreach ($lines ?: [] as $line) {
        $line = trim($line);

        if ($line === '' || str_starts_with($line, '#') || !str_contains($line, '=')) {
            continue;
        }

        [$key, $value] = explode('=', $line, 2);
        $key = trim($key);
        $value = trim($value);

        if ($key === '') {
            continue;
        }

        $value = trim($value, "\"'");
        $values[$key] = $value;
        $_ENV[$key] = $value;
        putenv($key . '=' . $value);
    }

    return $values;
}

function envValue(string $key, ?string $default = null): ?string
{
    $value = $_ENV[$key] ?? getenv($key);

    if ($value === false || $value === '') {
        return $default;
    }

    return (string) $value;
}
