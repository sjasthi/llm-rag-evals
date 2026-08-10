<?php

declare(strict_types=1);

require_once dirname(__DIR__) . '/config/env.php';

$overrideKey = 'LLM_RAG_TEST_PROCESS_OVERRIDE';
$fileOnlyKey = 'LLM_RAG_TEST_FILE_ONLY';
$originalOverride = getenv($overrideKey);
$originalFileOnly = getenv($fileOnlyKey);
$fixturePath = tempnam(sys_get_temp_dir(), 'llm-rag-env-');

if ($fixturePath === false) {
    fwrite(STDERR, "Could not create the temporary environment fixture.\n");
    exit(1);
}

try {
    file_put_contents(
        $fixturePath,
        $overrideKey . "=from-file\n" . $fileOnlyKey . "=file-value\n"
    );
    putenv($overrideKey . '=from-process');
    $_ENV[$overrideKey] = 'from-process';
    putenv($fileOnlyKey);
    unset($_ENV[$fileOnlyKey]);

    $loaded = loadEnv($fixturePath);
    if (($loaded[$overrideKey] ?? null) !== 'from-process') {
        throw new RuntimeException('Process environment did not override the file value.');
    }
    if (envValue($overrideKey) !== 'from-process') {
        throw new RuntimeException('The effective process value was replaced.');
    }
    if (($loaded[$fileOnlyKey] ?? null) !== 'file-value') {
        throw new RuntimeException('A file-only value was not loaded.');
    }

    fwrite(STDOUT, "php-env-precedence-ok\n");
} catch (Throwable $error) {
    fwrite(STDERR, $error->getMessage() . "\n");
    exit(1);
} finally {
    @unlink($fixturePath);

    if ($originalOverride === false) {
        putenv($overrideKey);
        unset($_ENV[$overrideKey]);
    } else {
        putenv($overrideKey . '=' . $originalOverride);
        $_ENV[$overrideKey] = $originalOverride;
    }

    if ($originalFileOnly === false) {
        putenv($fileOnlyKey);
        unset($_ENV[$fileOnlyKey]);
    } else {
        putenv($fileOnlyKey . '=' . $originalFileOnly);
        $_ENV[$fileOnlyKey] = $originalFileOnly;
    }
}
