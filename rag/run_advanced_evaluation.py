"""Cost-bounded FP8 runner for advanced evaluators on saved responses."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import Any

from advanced_evaluation import (
    ADVANCED_EVALUATOR_KEYS,
    AdvancedEvaluatorEngine,
    applicability_reason,
    estimated_application_cost,
)
from database import database_connection
from evaluation import load_evaluation_input
from evaluation_store import completed_result_exists, persist_result
from settings import Settings, load_settings


def selected_response_ids(
    connection: Any,
    *,
    response_id: int | None,
    run_id: int | None,
    limit: int | None,
) -> list[int]:
    with connection.cursor() as cursor:
        if response_id is not None:
            cursor.execute(
                "SELECT response_id FROM rag_responses WHERE response_id=%s",
                (response_id,),
            )
        else:
            cursor.execute(
                "SELECT response_id FROM rag_responses WHERE run_id=%s ORDER BY response_id",
                (run_id,),
            )
        rows = cursor.fetchall()
    values = [int(row[0]) for row in rows]
    return values[:limit] if limit is not None else values


def build_preflight(
    settings: Settings,
    connection: Any,
    response_ids: list[int],
    evaluator_keys: list[str],
    *,
    attempts: int,
    force: bool,
) -> dict[str, Any]:
    applications: list[dict[str, Any]] = []
    reuse_count = 0
    estimated_cost = 0.0
    for response_id in response_ids:
        item = load_evaluation_input(connection, response_id)
        for evaluator_key in evaluator_keys:
            existing = completed_result_exists(connection, response_id, evaluator_key)
            if existing and not force:
                reuse_count += 1
                applications.append({
                    "response_id": response_id,
                    "evaluator": evaluator_key,
                    "action": "reuse",
                    "reason": "A completed active-version result already exists.",
                })
                continue
            reason = applicability_reason(evaluator_key, item)
            action = "skip" if reason else "run"
            repeat_count = 1 if reason else attempts
            if action == "run":
                estimated_cost += estimated_application_cost(settings, evaluator_key) * repeat_count
            applications.append({
                "response_id": response_id,
                "evaluator": evaluator_key,
                "action": action,
                "attempts": repeat_count,
                "reason": reason,
            })
    run_applications = sum(
        int(application.get("attempts", 1))
        for application in applications
        if application["action"] in {"run", "skip"}
    )
    paid_applications = sum(
        int(application.get("attempts", 1))
        for application in applications
        if application["action"] == "run"
    )
    return {
        "responses": len(response_ids),
        "evaluators": evaluator_keys,
        "applications": applications,
        "application_count": run_applications,
        "paid_application_count": paid_applications,
        "reused_count": reuse_count,
        "estimated_cost": round(estimated_cost, 8),
        "cost_note": (
            "Estimate uses configured per-million token rates and conservative token/call assumptions."
            if settings.evaluator_input_cost_per_million or settings.evaluator_output_cost_per_million
            else "Provider pricing is not configured, so estimated cost is unavailable (shown as 0)."
        ),
    }


def execute_plan(
    settings: Settings,
    preflight: dict[str, Any],
    *,
    allow_paid: bool,
) -> list[dict[str, Any]]:
    if preflight["paid_application_count"] and not allow_paid:
        raise ValueError("Advanced model-backed execution requires --allow-paid.")

    outcomes: list[dict[str, Any]] = []
    with AdvancedEvaluatorEngine(settings) as engine:
        for application in preflight["applications"]:
            if application["action"] == "reuse":
                outcomes.append(dict(application))
                continue
            response_id = int(application["response_id"])
            evaluator_key = str(application["evaluator"])
            repeat_count = int(application.get("attempts", 1))
            for _ in range(repeat_count):
                with database_connection(settings) as connection:
                    item = load_evaluation_input(connection, response_id)
                execution = engine.run(evaluator_key, item)
                with database_connection(settings) as connection:
                    try:
                        connection.start_transaction()
                        attempt_number = persist_result(
                            connection,
                            response_id=response_id,
                            result=execution.result,
                            raw_provider_output=execution.raw_provider_output,
                            input_tokens=execution.input_tokens,
                            output_tokens=execution.output_tokens,
                            total_tokens=execution.total_tokens,
                        )
                        connection.commit()
                    except Exception:
                        connection.rollback()
                        raise
                outcomes.append({
                    "response_id": response_id,
                    "evaluator": evaluator_key,
                    "attempt_number": attempt_number,
                    "result": asdict(execution.result),
                    "usage": {
                        "input_tokens": execution.input_tokens,
                        "output_tokens": execution.output_tokens,
                        "total_tokens": execution.total_tokens,
                    },
                })
    return outcomes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply FP8 advanced evaluators to already-saved responses."
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--response-id", type=int)
    target.add_argument("--run-id", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--evaluators",
        default=",".join(ADVANCED_EVALUATOR_KEYS),
        help="Comma-separated advanced evaluator keys.",
    )
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--max-applications", type=int, default=5)
    parser.add_argument("--max-estimated-cost", type=float, default=1.0)
    parser.add_argument("--allow-paid", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be greater than zero")
    if args.attempts <= 0 or args.attempts > 10:
        parser.error("--attempts must be between 1 and 10")
    if args.max_applications <= 0:
        parser.error("--max-applications must be greater than zero")
    if args.max_estimated_cost < 0:
        parser.error("--max-estimated-cost cannot be negative")
    evaluator_keys = [key.strip() for key in args.evaluators.split(",") if key.strip()]
    unknown = sorted(set(evaluator_keys) - set(ADVANCED_EVALUATOR_KEYS))
    if unknown:
        parser.error(f"Unknown advanced evaluators: {', '.join(unknown)}")

    settings = load_settings()
    with database_connection(settings) as connection:
        response_ids = selected_response_ids(
            connection,
            response_id=args.response_id,
            run_id=args.run_id,
            limit=args.limit,
        )
        if not response_ids:
            parser.error("No saved responses matched the selected target.")
        preflight = build_preflight(
            settings,
            connection,
            response_ids,
            evaluator_keys,
            attempts=args.attempts,
            force=args.force,
        )

    if preflight["application_count"] > args.max_applications:
        parser.error(
            f"Plan has {preflight['application_count']} applications; "
            f"raise --max-applications deliberately to continue."
        )
    if preflight["estimated_cost"] > args.max_estimated_cost:
        parser.error(
            f"Estimated cost {preflight['estimated_cost']:.6f} exceeds "
            f"--max-estimated-cost {args.max_estimated_cost:.6f}."
        )

    payload: dict[str, Any] = {"preflight": preflight, "dry_run": args.dry_run}
    if not args.dry_run:
        payload["outcomes"] = execute_plan(
            settings, preflight, allow_paid=args.allow_paid
        )
    print(json.dumps(payload, indent=2) if args.json else json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
