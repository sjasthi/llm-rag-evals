"""Persistence helpers for canonical evaluator results and immutable attempts."""

from __future__ import annotations

import json
from typing import Any


def active_evaluator(connection: Any, evaluator_key: str) -> dict[str, Any]:
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(
            """SELECT evaluator_id, evaluator_key, version, configuration_json
               FROM evaluator_definitions
               WHERE evaluator_key=%s AND is_active=TRUE
               ORDER BY evaluator_id DESC LIMIT 1""",
            (evaluator_key,),
        )
        row = cursor.fetchone()
    if not row:
        raise ValueError(f"Evaluator definition {evaluator_key!r} is not seeded.")
    return row


def reusable_result_exists(connection: Any, response_id: int, evaluator_key: str) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT 1
               FROM evaluator_results result
               JOIN evaluator_definitions definition
                 ON definition.evaluator_id=result.evaluator_id
               WHERE result.response_id=%s AND definition.evaluator_key=%s
                 AND definition.is_active=TRUE
                 AND result.status IN ('completed', 'skipped')
               LIMIT 1""",
            (response_id, evaluator_key),
        )
        return cursor.fetchone() is not None


def next_attempt_number(connection: Any, response_id: int, evaluator_id: int) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT COALESCE(MAX(attempt_number), 0) + 1
               FROM evaluator_result_attempts
               WHERE response_id=%s AND evaluator_id=%s""",
            (response_id, evaluator_id),
        )
        row = cursor.fetchone()
    return int(row[0]) if row else 1


def _json_object(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def persist_result(
    connection: Any,
    *,
    response_id: int,
    result: Any,
    raw_provider_output: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
) -> int:
    """Append one immutable attempt and update the latest canonical display row."""
    evaluator = active_evaluator(connection, str(result.evaluator_key))
    evaluator_id = int(evaluator["evaluator_id"])
    attempt_number = next_attempt_number(connection, response_id, evaluator_id)
    definition_configuration = _json_object(evaluator.get("configuration_json"))
    result_configuration = getattr(result, "configuration", None) or {}
    configuration = {
        **definition_configuration,
        **result_configuration,
        "evaluator_version": evaluator["version"],
        "canonical_policy": "latest_attempt",
    }
    details = dict(getattr(result, "details", {}) or {})
    details["attempt_number"] = attempt_number
    details["canonical_policy"] = "latest_attempt"
    estimated_cost = getattr(result, "estimated_cost", None)

    with connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO evaluator_result_attempts
               (response_id, evaluator_id, attempt_number, status, raw_score,
                normalized_score, passed, explanation, details_json,
                configuration_json, raw_provider_output, input_tokens,
                output_tokens, total_tokens, runtime_ms, estimated_cost,
                error_message)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                response_id,
                evaluator_id,
                attempt_number,
                result.status,
                result.raw_score,
                result.normalized_score,
                result.passed,
                result.explanation,
                json.dumps(details),
                json.dumps(configuration),
                raw_provider_output,
                input_tokens,
                output_tokens,
                total_tokens,
                result.runtime_ms,
                estimated_cost,
                result.error_message,
            ),
        )
        cursor.execute(
            """INSERT INTO evaluator_results
               (response_id, evaluator_id, status, raw_score, normalized_score,
                passed, explanation, details_json, runtime_ms, estimated_cost,
                error_message)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON DUPLICATE KEY UPDATE
                 status=VALUES(status), raw_score=VALUES(raw_score),
                 normalized_score=VALUES(normalized_score), passed=VALUES(passed),
                 explanation=VALUES(explanation), details_json=VALUES(details_json),
                 runtime_ms=VALUES(runtime_ms), estimated_cost=VALUES(estimated_cost),
                 error_message=VALUES(error_message)""",
            (
                response_id,
                evaluator_id,
                result.status,
                result.raw_score,
                result.normalized_score,
                result.passed,
                result.explanation,
                json.dumps(details),
                result.runtime_ms,
                estimated_cost,
                result.error_message,
            ),
        )
    return attempt_number
