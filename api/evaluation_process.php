<?php
declare(strict_types=1);

/**
 * Shared subprocess lifecycle utilities.
 *
 * Intended for test-run generation and saved-answer scoring.
 * This module does not launch or terminate processes yet.
 */

/**
 * Return elapsed seconds from a monotonic start timestamp.
 */
function evaluationProcessElapsed(int $startedAtNs): float
{
    return max(0.0, (hrtime(true) - $startedAtNs) / 1_000_000_000);
}

/**
 * Return a normalized snapshot of a PHP subprocess.
 *
 * The process resource remains owned by the caller.
 */
function evaluationProcessSnapshot($process, int $startedAtNs): array
{
    if (!is_resource($process)) {
        throw new InvalidArgumentException('Invalid subprocess resource.');
    }

    $status = proc_get_status($process);

    return [
        'pid' => (int) ($status['pid'] ?? 0),
        'running' => (bool) ($status['running'] ?? false),
        'exit_code' => (int) ($status['exitcode'] ?? -1),
        'elapsed_seconds' => round(
            evaluationProcessElapsed($startedAtNs),
            3
        ),
    ];
}
/**
 * Terminate a Windows process tree.
 *
 * Only call with a PID obtained from a subprocess
 * launched and tracked by the current PHP request.
 *
 * Windows PID reuse means this is not an atomic
 * process-ownership guarantee.
 */
function evaluationTerminateWindowsTree(int $pid): array
{
    if (PHP_OS_FAMILY !== 'Windows') {
        throw new RuntimeException(
            'Windows process-tree termination is unavailable.'
        );
    }

    if ($pid <= 0 || $pid === getmypid()) {
        throw new InvalidArgumentException(
            'Invalid subprocess PID.'
        );
    }

    $command = [
        'C:\Windows\System32\taskkill.exe',
        '/PID',
        (string) $pid,
        '/T',
        '/F',
    ];

    $process = proc_open(
        $command,
        [
            0 => ['pipe', 'r'],
            1 => ['pipe', 'w'],
            2 => ['pipe', 'w'],
        ],
        $pipes,
        null,
        null,
        ['bypass_shell' => true]
    );

    if (!is_resource($process)) {
        throw new RuntimeException(
            'Could not launch Windows process-tree cleanup.'
        );
    }

    fclose($pipes[0]);

    $stdout = stream_get_contents($pipes[1]);
    $stderr = stream_get_contents($pipes[2]);

    fclose($pipes[1]);
    fclose($pipes[2]);

    $exitCode = proc_close($process);

    return [
        'success' => $exitCode === 0,
        'exit_code' => $exitCode,
        'stdout' => trim($stdout),
        'stderr' => trim($stderr),
    ];
}
/**
 * Clean up a tracked subprocess and its output pipes.
 *
 * Intended for subprocesses launched by the current PHP request.
 * This function must not be called twice for the same process.
 */
function evaluationProcessCleanup(
    $process,
    array $pipes,
    int $startedAtNs
): array {
    if (!is_resource($process)) {
        throw new InvalidArgumentException(
            'Invalid subprocess resource.'
        );
    }

    $snapshot = evaluationProcessSnapshot(
        $process,
        $startedAtNs
    );

    $termination = null;
    $fallbackUsed = false;

    if ($snapshot['running']) {
        if (PHP_OS_FAMILY === 'Windows' && $snapshot['pid'] > 0) {
            try {
                $termination = evaluationTerminateWindowsTree(
                    $snapshot['pid']
                );
            } catch (Throwable $error) {
                $termination = [
                    'success' => false,
                    'error_type' => get_class($error),
                ];
            }
        }

        if (
            PHP_OS_FAMILY !== 'Windows'
            || !($termination['success'] ?? false)
        ) {
            $fallbackUsed = true;
            proc_terminate($process);
        }
    }

    foreach ($pipes as $pipe) {
        if (is_resource($pipe)) {
            fclose($pipe);
        }
    }

    $closeCode = proc_close($process);

    return [
        'pid' => $snapshot['pid'],
        'was_running' => $snapshot['running'],
        'elapsed_seconds' => $snapshot['elapsed_seconds'],
        'termination' => $termination,
        'fallback_used' => $fallbackUsed,
        'close_exit_code' => $closeCode,
    ];
}

/**
 * Create temporary files for subprocess stdout and stderr.
 *
 * The caller is responsible for deleting both files.
 */
function evaluationCreateOutputFiles(): array
{
    $stdoutFile = tempnam(sys_get_temp_dir(), 'rag_out_');

    if ($stdoutFile === false) {
        throw new RuntimeException(
            'Could not create temporary stdout file.'
        );
    }

    $stderrFile = tempnam(sys_get_temp_dir(), 'rag_err_');

    if ($stderrFile === false) {
        @unlink($stdoutFile);

        throw new RuntimeException(
            'Could not create temporary stderr file.'
        );
    }

    return [
        'stdout_file' => $stdoutFile,
        'stderr_file' => $stderrFile,
    ];
}

/**
 * Launch a subprocess with file-backed stdout and stderr.
 *
 * The caller owns the returned process and temporary files.
 */
function evaluationStartFileProcess(
    array $command,
    ?string $workingDirectory = null
): array {
    if ($command === []) {
        throw new InvalidArgumentException(
            'Subprocess command cannot be empty.'
        );
    }

    $files = evaluationCreateOutputFiles();

    try {
        $startedAtNs = hrtime(true);

        $process = proc_open(
            $command,
            [
                0 => ['pipe', 'r'],
                1 => ['file', $files['stdout_file'], 'w'],
                2 => ['file', $files['stderr_file'], 'w'],
            ],
            $pipes,
            $workingDirectory,
            null,
            ['bypass_shell' => true]
        );

        if (!is_resource($process)) {
            throw new RuntimeException(
                'Could not launch subprocess.'
            );
        }

        fclose($pipes[0]);

        return [
            'process' => $process,
            'started_at_ns' => $startedAtNs,
            'stdout_file' => $files['stdout_file'],
            'stderr_file' => $files['stderr_file'],
        ];
    } catch (Throwable $error) {
        foreach ($files as $path) {
            if (is_file($path)) {
                @unlink($path);
            }
        }

        throw $error;
    }
}

/**
 * Read subprocess output with a maximum byte limit.
 *
 * Returns at most $maxBytes bytes from the beginning
 * of the output file.
 */
function evaluationReadOutputFile(
    string $path,
    int $maxBytes = 1048576
): string {
    if ($maxBytes <= 0) {
        throw new InvalidArgumentException(
            'Maximum output size must be positive.'
        );
    }

    if (!is_file($path)) {
        throw new RuntimeException(
            'Subprocess output file does not exist.'
        );
    }

    $handle = fopen($path, 'rb');

    if ($handle === false) {
        throw new RuntimeException(
            'Could not open subprocess output file.'
        );
    }

    try {
        $output = stream_get_contents($handle, $maxBytes);

        if ($output === false) {
            throw new RuntimeException(
                'Could not read subprocess output file.'
            );
        }

        return $output;
    } finally {
        fclose($handle);
    }
}

/**
 * Clean up a file-backed subprocess and its temporary files.
 *
 * Call once per subprocess. The caller must finish reading
 * any required output before invoking this function.
 */
function evaluationCleanupFileProcess(array $run): array
{
    $required = [
        'process',
        'started_at_ns',
        'stdout_file',
        'stderr_file',
    ];

    foreach ($required as $key) {
        if (!array_key_exists($key, $run)) {
            throw new InvalidArgumentException(
                'Missing subprocess field: ' . $key
            );
        }
    }

    $deleted = [
        'stdout_file' => false,
        'stderr_file' => false,
    ];

    try {
        return evaluationProcessCleanup(
            $run['process'],
            [],
            $run['started_at_ns']
        );
    } finally {
        foreach (['stdout_file', 'stderr_file'] as $key) {
            $file = $run[$key];

            if (is_string($file) && is_file($file)) {
                $deleted[$key] = @unlink($file);
            }
        }
    }
}

/**
 * Wait for a file-backed subprocess with a wall-clock timeout.
 *
 * Does not read stdout/stderr or clean up the process.
 * The caller must invoke evaluationCleanupFileProcess().
 */
function evaluationWaitForFileProcess(
    array $run,
    int $timeoutSeconds,
    int $pollMilliseconds = 100
): array {
    if ($timeoutSeconds <= 0) {
        throw new InvalidArgumentException(
            'Subprocess timeout must be positive.'
        );
    }

    if ($pollMilliseconds <= 0) {
        throw new InvalidArgumentException(
            'Polling interval must be positive.'
        );
    }

    $deadlineNs = $run['started_at_ns']
        + ($timeoutSeconds * 1_000_000_000);

    while (true) {
        $snapshot = evaluationProcessSnapshot(
            $run['process'],
            $run['started_at_ns']
        );

        if (!$snapshot['running']) {
            return [
                'timed_out' => false,
                'snapshot' => $snapshot,
            ];
        }

        $remainingNs = $deadlineNs - hrtime(true);

        if ($remainingNs <= 0) {
            return [
                'timed_out' => true,
                'snapshot' => $snapshot,
            ];
        }

        $sleepMicroseconds = (int) min(
            $pollMilliseconds * 1000,
            max(1, intdiv($remainingNs, 1000))
        );

        usleep($sleepMicroseconds);
    }
}


/**
 * Execute a Python command through the Windows Job Object supervisor.
 *
 * Returns the supervisor's structured result:
 * supervisor_ok, timed_out, exit_code, stdout, stderr.
 *
 * The caller is responsible for interpreting child exit codes
 * and preserving endpoint-specific HTTP responses.
 */
function evaluationRunSupervisedCommand(
    array $command,
    string $python,
    string $root,
    int $timeoutSeconds
): array {
    if ($command === [] || $timeoutSeconds <= 0) {
        throw new InvalidArgumentException(
            'Invalid supervised command or timeout.'
        );
    }

    $supervisor = $root . '/api/evaluation_supervisor.py';

    if (!is_file($python) || !is_file($supervisor)) {
        throw new RuntimeException(
            'Python supervisor environment was not found.'
        );
    }

    $requestFile = tempnam(sys_get_temp_dir(), 'rag_req_');

    if ($requestFile === false) {
        throw new RuntimeException(
            'Could not create supervisor request file.'
        );
    }

    $run = null;

    try {
        $request = [
            'command' => $command,
            'timeout_seconds' => $timeoutSeconds,
            'working_directory' => $root,
        ];

        $requestJson = json_encode(
            $request,
            JSON_THROW_ON_ERROR
        );

        if (file_put_contents($requestFile, $requestJson) === false) {
            throw new RuntimeException(
                'Could not write supervisor request file.'
            );
        }

        $run = evaluationStartFileProcess(
            [$python, $supervisor, $requestFile],
            $root
        );

        $wait = evaluationWaitForFileProcess(
            $run,
            $timeoutSeconds + 10
        );

        if ($wait['timed_out']) {
            throw new RuntimeException(
                'Supervisor process exceeded its outer timeout.'
            );
        }

        // Supervisor JSON contains up to 1 MiB each of child
        // stdout and stderr, plus JSON escaping overhead.
        $stdout = evaluationReadOutputFile(
            $run['stdout_file'],
            12582912
        );

        $stderr = evaluationReadOutputFile(
            $run['stderr_file'],
            1048576
        );

        $response = json_decode(
            $stdout,
            true,
            64,
            JSON_THROW_ON_ERROR
        );

        if (
            !is_array($response)
            || !array_key_exists('supervisor_ok', $response)
        ) {
            throw new RuntimeException(
                'Supervisor returned an invalid response.'
            );
        }

        if ($response['supervisor_ok'] !== true) {
            throw new RuntimeException(
                'Supervisor failed: '
                . (string) ($response['error'] ?? 'Unknown error')
            );
        }

        foreach (['timed_out', 'exit_code', 'stdout', 'stderr'] as $key) {
            if (!array_key_exists($key, $response)) {
                throw new RuntimeException(
                    'Supervisor response missing field: ' . $key
                );
            }
        }

        if (
            !is_bool($response['timed_out'])
            || (
                $response['exit_code'] !== null
                && !is_int($response['exit_code'])
            )
            || !is_string($response['stdout'])
            || !is_string($response['stderr'])
        ) {
            throw new RuntimeException(
                'Supervisor returned invalid field types.'
            );
        }

        return $response;

    } finally {
        try {
            if ($run !== null) {
                evaluationCleanupFileProcess($run);
            }
        } finally {
            @unlink($requestFile);
        }
    }
}
