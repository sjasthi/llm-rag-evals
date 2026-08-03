<?php

declare(strict_types=1);

require_once dirname(__DIR__) . '/config/database.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

const MAX_UPLOAD_BYTES = 10485760;
const DOCUMENT_TIMEOUT_SECONDS = 120;
const BUNDLED_RESTORE_TIMEOUT_SECONDS = 300;
const ALLOWED_UPLOADS = [
    'txt' => ['text/plain'],
    'pdf' => ['application/pdf'],
    'docx' => [
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/zip',
    ],
];

function documentResponse(int $status, array $payload): never
{
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    exit;
}

function listDocuments(PDO $database): array
{
    $statement = $database->query(
        "SELECT d.document_id, d.title, d.category, d.source_path, d.source_type,
                COALESCE(d.original_filename, d.title) AS original_filename,
                d.status, d.ingestion_error, d.imported_at, d.created_at,
                COUNT(c.chunk_id) AS chunk_count
         FROM documents d
         LEFT JOIN document_chunks c ON c.document_id = d.document_id
         GROUP BY d.document_id
         ORDER BY d.updated_at DESC, d.document_id DESC"
    );
    return $statement->fetchAll();
}

function validatedCategory(mixed $value): string
{
    $category = is_string($value) ? trim($value) : '';
    if (!preg_match('/^[a-z0-9][a-z0-9_-]{1,49}$/', $category)) {
        documentResponse(422, [
            'ok' => false,
            'error' => 'Category must use 2-50 lowercase letters, numbers, hyphens, or underscores.',
        ]);
    }
    return $category;
}

function validatedUpload(array $file): array
{
    $error = $file['error'] ?? UPLOAD_ERR_NO_FILE;
    if ($error !== UPLOAD_ERR_OK) {
        $messages = [
            UPLOAD_ERR_INI_SIZE => 'The file exceeds the server upload limit.',
            UPLOAD_ERR_FORM_SIZE => 'The file exceeds the form upload limit.',
            UPLOAD_ERR_PARTIAL => 'The file upload was incomplete.',
            UPLOAD_ERR_NO_FILE => 'Choose a document to upload.',
        ];
        documentResponse(422, ['ok' => false, 'error' => $messages[$error] ?? 'File upload failed.']);
    }

    $name = basename((string) ($file['name'] ?? ''));
    $temporaryPath = (string) ($file['tmp_name'] ?? '');
    $size = (int) ($file['size'] ?? 0);
    $extension = strtolower(pathinfo($name, PATHINFO_EXTENSION));
    if (!isset(ALLOWED_UPLOADS[$extension])) {
        documentResponse(415, ['ok' => false, 'error' => 'Only TXT, PDF, and DOCX files are supported.']);
    }
    if ($size < 1 || $size > MAX_UPLOAD_BYTES) {
        documentResponse(422, ['ok' => false, 'error' => 'Document must be between 1 byte and 10 MB.']);
    }
    if (!is_uploaded_file($temporaryPath)) {
        documentResponse(400, ['ok' => false, 'error' => 'The request did not contain a valid HTTP upload.']);
    }

    $mime = (new finfo(FILEINFO_MIME_TYPE))->file($temporaryPath);
    if (!is_string($mime) || !in_array($mime, ALLOWED_UPLOADS[$extension], true)) {
        documentResponse(415, ['ok' => false, 'error' => 'File contents do not match the selected file type.']);
    }
    return [$name, $temporaryPath, $extension];
}

function documentJsonPayload(): array
{
    try {
        $payload = json_decode(file_get_contents('php://input') ?: '{}', true, 8, JSON_THROW_ON_ERROR);
    } catch (JsonException) {
        documentResponse(400, ['ok' => false, 'error' => 'Request body must contain valid JSON.']);
    }
    if (!is_array($payload)) {
        documentResponse(400, ['ok' => false, 'error' => 'Request body must contain a JSON object.']);
    }
    return $payload;
}

function uploadedStoragePath(string $sourcePath): ?string
{
    $prefix = 'storage/uploads/';
    if (!str_starts_with($sourcePath, $prefix)) {
        return null;
    }
    $filename = substr($sourcePath, strlen($prefix));
    if ($filename === '' || $filename === '.' || $filename === '..' || basename($filename) !== $filename) {
        return null;
    }
    return projectRoot() . '/storage/uploads/' . $filename;
}

function runDocumentIngestion(
    string $absolutePath,
    string $sourcePath,
    string $category,
    string $title,
    string $originalFilename
): array {
    $root = projectRoot();
    $python = envValue('PYTHON_BIN', $root . '/.venv/Scripts/python.exe');
    if (!is_string($python) || !is_file($python)) {
        throw new RuntimeException('Project Python environment was not found.');
    }

    $command = [
        $python, $root . '/rag/admin.py', $absolutePath,
        '--source-path', $sourcePath,
        '--category', $category,
        '--title', $title,
        '--original-filename', $originalFilename,
    ];
    $process = proc_open(
        $command,
        [0 => ['pipe', 'r'], 1 => ['pipe', 'w'], 2 => ['pipe', 'w']],
        $pipes,
        $root,
        null,
        ['bypass_shell' => true]
    );
    if (!is_resource($process)) {
        throw new RuntimeException('Could not start document ingestion.');
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
        if ((microtime(true) - $startedAt) > DOCUMENT_TIMEOUT_SECONDS) {
            proc_terminate($process);
            fclose($pipes[1]);
            fclose($pipes[2]);
            proc_close($process);
            throw new RuntimeException('Document ingestion timed out.');
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
        throw new RuntimeException(trim($stderr) ?: 'Document ingestion failed.');
    }
    $result = json_decode($stdout, true, 16, JSON_THROW_ON_ERROR);
    if (!is_array($result) || !isset($result['document_id'], $result['chunk_count'])) {
        throw new RuntimeException('Document ingestion returned incomplete data.');
    }
    return $result;
}

function runBundledDocumentRestore(): array
{
    $root = projectRoot();
    $python = envValue('PYTHON_BIN', $root . '/.venv/Scripts/python.exe');
    if (!is_string($python) || !is_file($python)) {
        throw new RuntimeException('Project Python environment was not found.');
    }
    $sourceDirectory = $root . '/data/metrostate_documents';
    if (!is_dir($sourceDirectory)) {
        throw new RuntimeException('Bundled source collection was not found.');
    }
    $command = [
        $python,
        $root . '/rag/ingest.py',
        '--source-dir',
        $sourceDirectory,
        '--json',
    ];
    $process = proc_open(
        $command,
        [0 => ['pipe', 'r'], 1 => ['pipe', 'w'], 2 => ['pipe', 'w']],
        $pipes,
        $root,
        null,
        ['bypass_shell' => true]
    );
    if (!is_resource($process)) {
        throw new RuntimeException('Could not start bundled-source restoration.');
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
        if ((microtime(true) - $startedAt) > BUNDLED_RESTORE_TIMEOUT_SECONDS) {
            proc_terminate($process);
            fclose($pipes[1]);
            fclose($pipes[2]);
            proc_close($process);
            throw new RuntimeException('Bundled-source restoration timed out.');
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
        throw new RuntimeException(trim($stderr) ?: 'Bundled-source restoration failed.');
    }
    $result = json_decode($stdout, true, 16, JSON_THROW_ON_ERROR);
    if (!is_array($result) || !isset($result['documents'], $result['chunks'])) {
        throw new RuntimeException('Bundled-source restoration returned incomplete data.');
    }
    return $result;
}

function runDocumentDeletion(?string $sourcePath = null, bool $deleteAll = false): array
{
    $root = projectRoot();
    $python = envValue('PYTHON_BIN', $root . '/.venv/Scripts/python.exe');
    if (!is_string($python) || !is_file($python)) {
        throw new RuntimeException('Project Python environment was not found.');
    }

    $command = [$python, $root . '/rag/admin.py'];
    if ($deleteAll) {
        $command[] = '--delete-all';
    } else {
        if ($sourcePath === null || trim($sourcePath) === '') {
            throw new InvalidArgumentException('A source path is required for document deletion.');
        }
        $command[] = '--source-path';
        $command[] = $sourcePath;
        $command[] = '--delete';
    }
    $process = proc_open(
        $command,
        [0 => ['pipe', 'r'], 1 => ['pipe', 'w'], 2 => ['pipe', 'w']],
        $pipes,
        $root,
        null,
        ['bypass_shell' => true]
    );
    if (!is_resource($process)) {
        throw new RuntimeException('Could not start document deletion.');
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
        if ((microtime(true) - $startedAt) > DOCUMENT_TIMEOUT_SECONDS) {
            proc_terminate($process);
            fclose($pipes[1]);
            fclose($pipes[2]);
            proc_close($process);
            throw new RuntimeException('Document deletion timed out.');
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
        throw new RuntimeException(trim($stderr) ?: 'Document deletion failed.');
    }
    $result = json_decode($stdout, true, 16, JSON_THROW_ON_ERROR);
    if (!is_array($result) || ($result['deleted'] ?? false) !== true) {
        throw new RuntimeException('Document deletion returned incomplete data.');
    }
    return $result;
}

try {
    $database = databaseConnection();
    $method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
    if ($method === 'GET') {
        documentResponse(200, ['ok' => true, 'data' => listDocuments($database)]);
    }
    if ($method === 'DELETE') {
        $payload = documentJsonPayload();
        if (($payload['action'] ?? '') === 'delete_all') {
            if (($payload['confirmation'] ?? '') !== 'DELETE ALL') {
                documentResponse(422, ['ok' => false, 'error' => 'Type DELETE ALL to confirm clearing the active index.']);
            }
            $result = runDocumentDeletion(null, true);
            foreach (($result['source_paths'] ?? []) as $sourcePath) {
                if (!is_string($sourcePath)) {
                    continue;
                }
                $absolutePath = uploadedStoragePath($sourcePath);
                if ($absolutePath === null) {
                    continue;
                }
                if (is_file($absolutePath) && !unlink($absolutePath)) {
                    error_log('Indexed upload removed but its stored file could not be removed: ' . $sourcePath);
                }
            }
            documentResponse(200, ['ok' => true, 'data' => [
                'deleted_count' => (int) ($result['deleted_count'] ?? 0),
                'deleted_chunk_count' => (int) ($result['deleted_chunk_count'] ?? 0),
            ]]);
        }

        $documentId = filter_var($payload['document_id'] ?? null, FILTER_VALIDATE_INT);
        if (!$documentId) {
            documentResponse(422, ['ok' => false, 'error' => 'A valid document ID is required.']);
        }

        $statement = $database->prepare('SELECT source_path FROM documents WHERE document_id = ?');
        $statement->execute([$documentId]);
        $document = $statement->fetch();
        if (!$document) {
            documentResponse(404, ['ok' => false, 'error' => 'Indexed document was not found.']);
        }

        $sourcePath = $document['source_path'];
        $result = runDocumentDeletion($sourcePath);
        $absolutePath = uploadedStoragePath($sourcePath);
        $isUploaded = $absolutePath !== null;
        if ($isUploaded) {
            if (is_file($absolutePath) && !unlink($absolutePath)) {
                error_log('Indexed document deleted but upload file could not be removed: ' . $sourcePath);
            }
        }
        documentResponse(200, ['ok' => true, 'data' => [
            'document_id' => (int) $documentId,
            'deleted_chunk_count' => (int) ($result['deleted_chunk_count'] ?? 0),
            'source_file_retained' => !$isUploaded,
        ]]);
    }
    if ($method !== 'POST') {
        header('Allow: GET, POST, DELETE');
        documentResponse(405, ['ok' => false, 'error' => 'Use GET, POST, or DELETE for documents.']);
    }

    $contentType = strtolower((string) ($_SERVER['CONTENT_TYPE'] ?? ''));
    if (str_starts_with($contentType, 'application/json')) {
        $payload = documentJsonPayload();
        if (($payload['action'] ?? '') !== 'restore_bundled' || ($payload['confirmation'] ?? '') !== 'RESTORE') {
            documentResponse(422, ['ok' => false, 'error' => 'Confirm bundled-source restoration from the Documents page.']);
        }
        $result = runBundledDocumentRestore();
        documentResponse(200, ['ok' => true, 'data' => $result]);
    }

    [$originalName, $temporaryPath, $extension] = validatedUpload($_FILES['document'] ?? []);
    $category = validatedCategory($_POST['category'] ?? '');
    $title = trim((string) ($_POST['title'] ?? pathinfo($originalName, PATHINFO_FILENAME)));
    if ($title === '' || strlen($title) > 255) {
        documentResponse(422, ['ok' => false, 'error' => 'Title must be between 1 and 255 characters.']);
    }

    $uploadDirectory = projectRoot() . '/storage/uploads';
    if (!is_dir($uploadDirectory) && !mkdir($uploadDirectory, 0700, true) && !is_dir($uploadDirectory)) {
        throw new RuntimeException('Upload storage could not be created.');
    }

    $replaceId = filter_var($_POST['replace_document_id'] ?? null, FILTER_VALIDATE_INT);
    $replacementDocuments = [];
    if ($replaceId) {
        $statement = $database->prepare(
            'SELECT document_id, source_path, source_type, original_filename FROM documents WHERE document_id = ?'
        );
        $statement->execute([$replaceId]);
        $existing = $statement->fetch();
        if (!$existing) {
            documentResponse(404, ['ok' => false, 'error' => 'The document selected for replacement was not found.']);
        }
        $replacementDocuments = [$existing];
    } else {
        $statement = $database->prepare(
            'SELECT document_id, source_path, source_type, original_filename '
            . 'FROM documents WHERE original_filename = ? ORDER BY document_id'
        );
        $statement->execute([$originalName]);
        $replacementDocuments = $statement->fetchAll();
    }

    $sourcePath = 'storage/uploads/' . bin2hex(random_bytes(16)) . '.' . $extension;
    $absolutePath = projectRoot() . '/' . $sourcePath;

    if (!move_uploaded_file($temporaryPath, $absolutePath)) {
        throw new RuntimeException('The uploaded file could not be stored.');
    }

    try {
        $result = runDocumentIngestion($absolutePath, $sourcePath, $category, $title, $originalName);
        foreach ($replacementDocuments as $existing) {
            $oldSourcePath = (string) $existing['source_path'];
            runDocumentDeletion($oldSourcePath);
            $oldAbsolutePath = uploadedStoragePath($oldSourcePath);
            if ($oldAbsolutePath !== null) {
                if (is_file($oldAbsolutePath) && !unlink($oldAbsolutePath)) {
                    error_log('Replaced upload was de-indexed but its stored file could not be removed: ' . $oldSourcePath);
                }
            }
        }
    } catch (Throwable $error) {
        try {
            runDocumentDeletion($sourcePath);
        } catch (Throwable $rollbackError) {
            error_log('Replacement rollback could not clear the new index record: ' . $rollbackError->getMessage());
        }
        if (is_file($absolutePath)) {
            unlink($absolutePath);
        }
        throw $error;
    }

    $result['replaced_document_count'] = count($replacementDocuments);
    $result['auto_replaced'] = !$replaceId && count($replacementDocuments) > 0;
    documentResponse(201, ['ok' => true, 'data' => $result]);
} catch (Throwable $error) {
    error_log('Documents endpoint failure: ' . $error->getMessage());
    documentResponse(500, [
        'ok' => false,
        'error' => 'Document operation failed. Try again or contact the application administrator.',
    ]);
}
