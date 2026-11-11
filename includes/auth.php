<?php

declare(strict_types=1);

/*
 * Basic user accounts for Chat.
 *
 * Accounts use PHP sessions and password_hash()/password_verify(). Every
 * request that changes state (sign in, sign out, create account, ask, archive)
 * must carry the session's CSRF token in the X-CSRF-Token header. Conversations
 * are owned by one user; ownership is checked again in rag/answer.py.
 */

require_once dirname(__DIR__) . '/config/database.php';

const AUTH_USERNAME_PATTERN = '/^[A-Za-z0-9_.-]{3,50}$/';
const AUTH_MIN_PASSWORD_LENGTH = 8;
// bcrypt only uses the first 72 bytes; reject longer passwords instead of truncating silently.
const AUTH_MAX_PASSWORD_BYTES = 72;
const AUTH_MAX_DISPLAY_NAME_LENGTH = 100;

function startAppSession(): void
{
    if (session_status() === PHP_SESSION_ACTIVE) {
        return;
    }
    $secure = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off')
        || (($_SERVER['SERVER_PORT'] ?? '') === '443');
    session_name('rag_session');
    session_set_cookie_params([
        'lifetime' => 0,
        'path' => '/',
        'secure' => $secure,
        'httponly' => true,
        'samesite' => 'Lax',
    ]);
    ini_set('session.use_strict_mode', '1');
    ini_set('session.use_only_cookies', '1');
    session_start();
}

function csrfToken(): string
{
    startAppSession();
    if (!isset($_SESSION['csrf_token']) || !is_string($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }

    return $_SESSION['csrf_token'];
}

function csrfTokenIsValid(): bool
{
    startAppSession();
    $sent = $_SERVER['HTTP_X_CSRF_TOKEN'] ?? '';
    $expected = $_SESSION['csrf_token'] ?? '';

    return is_string($sent) && is_string($expected) && $expected !== '' && hash_equals($expected, $sent);
}

/** The signed-in user as ['user_id' => int, 'username' => string, 'display_name' => string], or null. */
function currentUser(): ?array
{
    startAppSession();
    $user = $_SESSION['user'] ?? null;
    if (!is_array($user) || !isset($user['user_id'], $user['username'], $user['display_name'])) {
        return null;
    }

    return [
        'user_id' => (int) $user['user_id'],
        'username' => (string) $user['username'],
        'display_name' => (string) $user['display_name'],
    ];
}

function publicUser(?array $user): ?array
{
    if ($user === null) {
        return null;
    }

    return ['username' => $user['username'], 'display_name' => $user['display_name']];
}

function signInSession(array $user): void
{
    startAppSession();
    // A new session id on sign-in prevents session fixation.
    session_regenerate_id(true);
    $_SESSION['user'] = [
        'user_id' => (int) $user['user_id'],
        'username' => (string) $user['username'],
        'display_name' => (string) $user['display_name'],
    ];
    $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
}

function signOutSession(): void
{
    startAppSession();
    $_SESSION = [];
    session_regenerate_id(true);
    $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
}

function normalizedUsername(mixed $value): ?string
{
    if (!is_string($value)) {
        return null;
    }
    $username = trim($value);

    return preg_match(AUTH_USERNAME_PATTERN, $username) === 1 ? $username : null;
}

/** Returns an error message, or null when the password is acceptable. */
function passwordProblem(mixed $password): ?string
{
    if (!is_string($password) || $password === '') {
        return 'Enter a password.';
    }
    if (mb_strlen($password) < AUTH_MIN_PASSWORD_LENGTH) {
        return 'Use a password with at least ' . AUTH_MIN_PASSWORD_LENGTH . ' characters.';
    }
    if (strlen($password) > AUTH_MAX_PASSWORD_BYTES) {
        return 'Use a password of ' . AUTH_MAX_PASSWORD_BYTES . ' characters or fewer.';
    }

    return null;
}

function findUserByUsername(PDO $pdo, string $username): ?array
{
    $statement = $pdo->prepare(
        'SELECT user_id, username, display_name, password_hash FROM users WHERE username = ?'
    );
    $statement->execute([$username]);
    $row = $statement->fetch();

    return is_array($row) ? $row : null;
}

/** Verifies credentials in constant-ish time whether or not the username exists. */
function authenticateUser(PDO $pdo, string $username, string $password): ?array
{
    static $dummyHash = null;
    $user = findUserByUsername($pdo, $username);
    if ($user === null) {
        $dummyHash ??= password_hash('not-a-real-password', PASSWORD_DEFAULT);
        password_verify($password, $dummyHash);
        return null;
    }
    if (!password_verify($password, (string) $user['password_hash'])) {
        return null;
    }
    if (password_needs_rehash((string) $user['password_hash'], PASSWORD_DEFAULT)) {
        $pdo->prepare('UPDATE users SET password_hash = ? WHERE user_id = ?')
            ->execute([password_hash($password, PASSWORD_DEFAULT), $user['user_id']]);
    }
    $pdo->prepare('UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE user_id = ?')
        ->execute([$user['user_id']]);

    return $user;
}
