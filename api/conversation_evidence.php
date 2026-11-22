<?php

declare(strict_types=1);

require_once dirname(__DIR__) . '/includes/auth.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

function evidenceResponse(int $status, array $payload): never
{
    http_response_code($status);

    echo json_encode(
        $payload,
        JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE
    );

    exit;
}

function evidenceNotFound(): never
{
    // Do not disclose whether another user's response exists.
    evidenceResponse(404, [
        'ok' => false,
        'error' => 'Saved evidence is not available.',
    ]);
}

function evidencePositiveId(mixed $value): ?int
{
    if (
        !is_string($value) ||
        $value === '' ||
        strlen($value) > 20 ||
        !ctype_digit($value)
    ) {
        return null;
    }

    $number = filter_var(
        $value,
        FILTER_VALIDATE_INT,
        ['options' => ['min_range' => 1]]
    );

    return is_int($number) ? $number : null;
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'GET') {
    header('Allow: GET');

    evidenceResponse(405, [
        'ok' => false,
        'error' => 'Use GET for saved conversation evidence.',
    ]);
}

startAppSession();

$user = currentUser();

if ($user === null) {
    evidenceResponse(401, [
        'ok' => false,
        'error' => 'Sign in to inspect saved evidence.',
    ]);
}

$conversationId = evidencePositiveId(
    $_GET['conversation_id'] ?? null
);

$responseId = evidencePositiveId(
    $_GET['response_id'] ?? null
);

if ($conversationId === null || $responseId === null) {
    evidenceResponse(422, [
        'ok' => false,
        'error' => 'Valid conversation and response IDs are required.',
    ]);
}

try {
    $pdo = databaseConnection();

    // Ownership and response membership must BOTH be verified.
    // Checking a response ID alone is not sufficient.
    $authorization = $pdo->prepare(
        "SELECT 1
         FROM conversations c
         INNER JOIN conversation_messages m
             ON m.conversation_id = c.conversation_id
         WHERE c.conversation_id = ?
           AND c.user_id = ?
           AND c.status = 'active'
           AND m.role = 'assistant'
           AND m.response_id = ?
         LIMIT 1"
    );

    $authorization->execute([
        $conversationId,
        (int) $user['user_id'],
        $responseId,
    ]);

    if ($authorization->fetchColumn() === false) {
        evidenceNotFound();
    }

    // Read immutable source snapshots instead of performing
    // a new retrieval against the current document index.
    $statement = $pdo->prepare(
        "SELECT context_id,
                document_id,
                chunk_id,
                rank_position,
                source_path_snapshot,
                category_snapshot,
                page_number_snapshot,
                chunk_index_snapshot,
                content_type_snapshot,
                extraction_method_snapshot,
                semantic_distance,
                lexical_score,
                retrieval_score,
                context_excerpt
         FROM retrieved_contexts
         WHERE response_id = ?
         ORDER BY rank_position, context_id
         LIMIT 100"
    );

    $statement->execute([$responseId]);

    $sources = [];

    foreach ($statement->fetchAll(PDO::FETCH_ASSOC) as $row) {
        $sourcePath = (string) (
            $row['source_path_snapshot'] ?? ''
        );

        $filename = $sourcePath !== ''
            ? basename(str_replace('\\', '/', $sourcePath))
            : 'Unknown document';

        $sources[] = [
            'rank' => (int) $row['rank_position'],
            'document_id' => $row['document_id'] === null
                ? null : (int) $row['document_id'],
            'chunk_id' => $row['chunk_id'] === null
                ? null : (int) $row['chunk_id'],
            'source_path' => $sourcePath,
            'original_filename' => $filename,
            'category' => $row['category_snapshot'],
            'page_number' => $row['page_number_snapshot'] === null
                ? null : (int) $row['page_number_snapshot'],
            'chunk_index' => $row['chunk_index_snapshot'] === null
                ? null : (int) $row['chunk_index_snapshot'],
            'content_type' => $row['content_type_snapshot'],
            'extraction_method' =>
                $row['extraction_method_snapshot'],
            'distance' => $row['semantic_distance'] === null
                ? null : (float) $row['semantic_distance'],
            'keyword_score' => $row['lexical_score'] === null
                ? null : (float) $row['lexical_score'],
            'retrieval_score' => $row['retrieval_score'] === null
                ? null : (float) $row['retrieval_score'],
            'text' => (string) $row['context_excerpt'],
        ];
    }

    evidenceResponse(200, [
        'ok' => true,
        'data' => [
            'conversation_id' => $conversationId,
            'response_id' => $responseId,
            'sources' => $sources,
        ],
    ]);
} catch (Throwable $exception) {
    error_log(
        'Conversation evidence retrieval failed: ' .
        $exception->getMessage()
    );

    evidenceResponse(500, [
        'ok' => false,
        'error' => 'Saved evidence could not be loaded.',
    ]);
}
