<?php

declare(strict_types=1);

require_once dirname(__DIR__) . '/includes/auth.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function authResponse(int $status, array $payload): never
{
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    exit;
}

function authPayload(): array
{
    $raw = file_get_contents('php://input');
    try {
        $payload = json_decode($raw ?: '{}', true, 8, JSON_THROW_ON_ERROR);
    } catch (JsonException) {
        authResponse(400, ['ok' => false, 'error' => 'Request body must contain valid JSON.']);
    }

    return is_array($payload) ? $payload : [];
}

function registrationAllowed(): bool
{
    return filter_var(envValue('ALLOW_ACCOUNT_REGISTRATION', '1'), FILTER_VALIDATE_BOOLEAN);
}

function sessionState(): array
{
    return [
        'ok' => true,
        'user' => publicUser(currentUser()),
        'csrf_token' => csrfToken(),
        'registration_allowed' => registrationAllowed(),
    ];
}

startAppSession();
$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

if ($method === 'GET') {
    authResponse(200, sessionState());
}
if ($method !== 'POST') {
    header('Allow: GET, POST');
    authResponse(405, ['ok' => false, 'error' => 'Use GET or POST.']);
}
if (!csrfTokenIsValid()) {
    authResponse(403, ['ok' => false, 'error' => 'Your session expired. Reload the page and try again.']);
}

$payload = authPayload();
$action = $payload['action'] ?? '';

if ($action === 'logout') {
    signOutSession();
    authResponse(200, sessionState());
}

if (!in_array($action, ['login', 'register'], true)) {
    authResponse(422, ['ok' => false, 'error' => 'Unsupported account action.']);
}

$username = normalizedUsername($payload['username'] ?? null);
$password = $payload['password'] ?? null;

try {
    $pdo = databaseConnection();

    if ($action === 'login') {
        $user = ($username !== null && is_string($password) && $password !== ''
            && strlen($password) <= AUTH_MAX_PASSWORD_BYTES)
            ? authenticateUser($pdo, $username, $password)
            : null;
        if ($user === null) {
            authResponse(401, ['ok' => false, 'error' => 'That username and password do not match.']);
        }
        signInSession($user);
        authResponse(200, sessionState());
    }

    if (!registrationAllowed()) {
        authResponse(403, ['ok' => false, 'error' => 'New accounts are turned off. Ask the administrator for an account.']);
    }
    if ($username === null) {
        authResponse(422, ['ok' => false, 'error' => 'Use 3 to 50 letters, numbers, dots, dashes or underscores for your username.']);
    }
    $problem = passwordProblem($password);
    if ($problem !== null) {
        authResponse(422, ['ok' => false, 'error' => $problem]);
    }
    $displayName = trim((string) ($payload['display_name'] ?? ''));
    if ($displayName === '') {
        $displayName = $username;
    }
    if (mb_strlen($displayName) > AUTH_MAX_DISPLAY_NAME_LENGTH) {
        authResponse(422, ['ok' => false, 'error' => 'Use a display name of 100 characters or fewer.']);
    }

    try {
        $pdo->prepare('INSERT INTO users (username, display_name, password_hash) VALUES (?, ?, ?)')
            ->execute([$username, $displayName, password_hash((string) $password, PASSWORD_DEFAULT)]);
    } catch (PDOException $error) {
        if (($error->errorInfo[1] ?? null) === 1062) {
            authResponse(409, ['ok' => false, 'error' => 'That username is already taken. Choose another one.']);
        }
        throw $error;
    }
    signInSession([
        'user_id' => (int) $pdo->lastInsertId(),
        'username' => $username,
        'display_name' => $displayName,
    ]);
    authResponse(201, sessionState());
} catch (Throwable $error) {
    error_log('Account endpoint failure: ' . $error->getMessage());
    authResponse(500, ['ok' => false, 'error' => 'Accounts are unavailable right now. Try again or contact the application administrator.']);
}
