<?php

/**
 * Write diagnostic information for evaluation execution.
 *
 * Logs are stored locally and are not returned directly
 * to the browser.
 */
function testRunDiagnosticLog(
    string $event,
    array $context = []
): void {
    $root = dirname(__DIR__);
    $logDirectory = $root . DIRECTORY_SEPARATOR . 'storage'
        . DIRECTORY_SEPARATOR . 'logs';

    if (!is_dir($logDirectory)) {
        if (!mkdir($logDirectory, 0700, true) && !is_dir($logDirectory)) {
            error_log('Could not create evaluation log directory.');
            return;
        }
    }

    $logFile = $logDirectory
        . DIRECTORY_SEPARATOR . 'evaluation_diagnostics.log';

    $entry = [
        'timestamp' => date('c'),
        'event' => $event,
        'context' => $context,
    ];

    $json = json_encode(
        $entry,
        JSON_UNESCAPED_SLASHES | JSON_INVALID_UTF8_SUBSTITUTE
    );

    if ($json === false) {
        error_log('Could not encode evaluation diagnostic entry.');
        return;
    }

    if (file_put_contents($logFile, $json . PHP_EOL, FILE_APPEND | LOCK_EX) === false) {
        error_log('Could not write evaluation diagnostic entry.');
    }
}

/**
 * Save Python stderr to a local diagnostic file.
 *
 * This file must remain outside the public web directory.
 */
function testRunSavePythonError(string $stderr): ?string
{
    if (trim($stderr) === '') {
        return null;
    }

    $root = dirname(__DIR__);
    $logDirectory = $root . DIRECTORY_SEPARATOR
        . 'storage' . DIRECTORY_SEPARATOR . 'logs';

    if (!is_dir($logDirectory)) {
        if (!mkdir($logDirectory, 0700, true) && !is_dir($logDirectory)) {
            error_log('Could not create Python error log directory.');
            return null;
        }
    }

    try {
        $errorId = bin2hex(random_bytes(8));
    } catch (Throwable $error) {
        error_log('Could not generate Python error log identifier.');
        return null;
    }

    $filename = 'python_error_' . $errorId . '.log';
    $filepath = $logDirectory . DIRECTORY_SEPARATOR . $filename;

    // Bound the amount of output retained per failure.
    $content = substr($stderr, 0, 65536);

    if (file_put_contents($filepath, $content, LOCK_EX) === false) {
        error_log('Could not save Python error details.');
        return null;
    }

    return $filename;
}
