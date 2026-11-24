<?php

declare(strict_types=1);

/*
 * Evaluation ownership.
 *
 * Every saved answer (rag_responses.user_id) and test run
 * (evaluation_runs.user_id) belongs to the account that created it. Endpoints
 * that read, score, review, export or compare evaluation data call these
 * helpers before touching an ID from the request. Another account's record is
 * reported exactly like a missing one (404), so IDs cannot be probed.
 * Unowned rows from before accounts are visible to no one; see
 * rag/claim_evaluations.py.
 */

require_once dirname(__DIR__) . '/config/database.php';

function userOwnsResponse(PDO $database, int $responseId, int $userId): bool
{
    $statement = $database->prepare(
        'SELECT 1 FROM rag_responses WHERE response_id = ? AND user_id = ?'
    );
    $statement->execute([$responseId, $userId]);

    return $statement->fetchColumn() !== false;
}

function userOwnsRun(PDO $database, int $runId, int $userId): bool
{
    $statement = $database->prepare(
        'SELECT 1 FROM evaluation_runs WHERE run_id = ? AND user_id = ?'
    );
    $statement->execute([$runId, $userId]);

    return $statement->fetchColumn() !== false;
}

/** True when the saved answer is part of the run and both belong to the user. */
function userOwnsRunResponse(PDO $database, int $runId, int $responseId, int $userId): bool
{
    $statement = $database->prepare(
        'SELECT 1
         FROM rag_responses response
         JOIN evaluation_runs run ON run.run_id = response.run_id
         WHERE response.response_id = ? AND run.run_id = ?
           AND response.user_id = ? AND run.user_id = ?'
    );
    $statement->execute([$responseId, $runId, $userId, $userId]);

    return $statement->fetchColumn() !== false;
}
