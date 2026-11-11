<?php

declare(strict_types=1);

require_once dirname(__DIR__) . '/includes/auth.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

const RECENT_CONVERSATION_LIMIT = 20;
const CONVERSATION_MESSAGE_LIMIT = 200;

function conversationResponse(int $status, array $payload): never
{
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    exit;
}

function notFound(): never
{
    // Another user's conversation is reported exactly like a missing one.
    conversationResponse(404, [
        'ok' => false,
        'conversation_reset' => true,
        'error' => 'That conversation is no longer available.',
    ]);
}

/** Loads an active conversation only if it belongs to the signed-in user. */
function ownedConversation(PDO $pdo, int $conversationId, int $userId): ?array
{
    $statement = $pdo->prepare(
        "SELECT conversation_id, title, created_at, updated_at
         FROM conversations
         WHERE conversation_id = ? AND user_id = ? AND status = 'active'"
    );
    $statement->execute([$conversationId, $userId]);
    $row = $statement->fetch();

    return is_array($row) ? $row : null;
}

startAppSession();
$user = currentUser();
if ($user === null) {
    conversationResponse(401, ['ok' => false, 'error' => 'Sign in to see your chats.']);
}
$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

try {
    $pdo = databaseConnection();

    if ($method === 'GET') {
        $rawId = $_GET['conversation_id'] ?? null;
        if ($rawId === null || $rawId === '') {
            $statement = $pdo->prepare(
                "SELECT c.conversation_id, c.title, c.created_at, c.updated_at,
                        COUNT(m.message_id) AS message_count
                 FROM conversations c
                 LEFT JOIN conversation_messages m ON m.conversation_id = c.conversation_id
                 WHERE c.user_id = ? AND c.status = 'active'
                 GROUP BY c.conversation_id, c.title, c.created_at, c.updated_at
                 ORDER BY c.updated_at DESC, c.conversation_id DESC
                 LIMIT " . RECENT_CONVERSATION_LIMIT
            );
            $statement->execute([$user['user_id']]);
            $conversations = array_map(static fn (array $row): array => [
                'conversation_id' => (int) $row['conversation_id'],
                'title' => (string) ($row['title'] ?? 'Untitled chat'),
                'created_at' => (string) $row['created_at'],
                'updated_at' => (string) $row['updated_at'],
                'question_count' => intdiv((int) $row['message_count'], 2),
            ], $statement->fetchAll());
            conversationResponse(200, ['ok' => true, 'data' => ['conversations' => $conversations]]);
        }

        $conversationId = filter_var($rawId, FILTER_VALIDATE_INT, ['options' => ['min_range' => 1]]);
        if ($conversationId === false) {
            conversationResponse(422, ['ok' => false, 'error' => 'Conversation id must be a positive integer.']);
        }
        $conversation = ownedConversation($pdo, (int) $conversationId, $user['user_id']);
        if ($conversation === null) {
            notFound();
        }
        $statement = $pdo->prepare(
            'SELECT role, content, sequence_number, response_id, created_at
             FROM conversation_messages
             WHERE conversation_id = ?
             ORDER BY sequence_number
             LIMIT ' . CONVERSATION_MESSAGE_LIMIT
        );
        $statement->execute([$conversationId]);
        $messages = array_map(static fn (array $row): array => [
            'role' => (string) $row['role'],
            'content' => (string) $row['content'],
            'sequence_number' => (int) $row['sequence_number'],
            'response_id' => $row['response_id'] === null ? null : (int) $row['response_id'],
            'created_at' => (string) $row['created_at'],
        ], $statement->fetchAll());
        conversationResponse(200, ['ok' => true, 'data' => [
            'conversation' => [
                'conversation_id' => (int) $conversation['conversation_id'],
                'title' => (string) ($conversation['title'] ?? 'Untitled chat'),
                'created_at' => (string) $conversation['created_at'],
                'updated_at' => (string) $conversation['updated_at'],
            ],
            'messages' => $messages,
        ]]);
    }

    if ($method !== 'POST') {
        header('Allow: GET, POST');
        conversationResponse(405, ['ok' => false, 'error' => 'Use GET or POST.']);
    }
    if (!csrfTokenIsValid()) {
        conversationResponse(403, ['ok' => false, 'error' => 'Your session expired. Reload the page and try again.']);
    }
    try {
        $payload = json_decode(file_get_contents('php://input') ?: '{}', true, 8, JSON_THROW_ON_ERROR);
    } catch (JsonException) {
        conversationResponse(400, ['ok' => false, 'error' => 'Request body must contain valid JSON.']);
    }
    if (!is_array($payload) || ($payload['action'] ?? '') !== 'archive') {
        conversationResponse(422, ['ok' => false, 'error' => 'Unsupported conversation action.']);
    }
    $conversationId = filter_var($payload['conversation_id'] ?? null, FILTER_VALIDATE_INT, ['options' => ['min_range' => 1]]);
    if ($conversationId === false) {
        conversationResponse(422, ['ok' => false, 'error' => 'Conversation id must be a positive integer.']);
    }
    // Archiving hides the chat from Recent chats; messages and saved answers stay for research.
    $statement = $pdo->prepare(
        "UPDATE conversations SET status = 'archived'
         WHERE conversation_id = ? AND user_id = ? AND status = 'active'"
    );
    $statement->execute([$conversationId, $user['user_id']]);
    if ($statement->rowCount() === 0) {
        notFound();
    }
    conversationResponse(200, ['ok' => true]);
} catch (Throwable $error) {
    error_log('Conversations endpoint failure: ' . $error->getMessage());
    conversationResponse(500, ['ok' => false, 'error' => 'Your chats could not be loaded. Try again or contact the application administrator.']);
}
