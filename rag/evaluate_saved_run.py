"""Browser-facing orchestration for reapplying evaluators to a saved run."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import Any

from database import database_connection
from evaluation import LOCAL_EVALUATORS, score_saved_response
from evaluation_store import completed_result_exists
from run_advanced_evaluation import (
    build_preflight as build_advanced_preflight,
    execute_plan as execute_advanced_plan,
    selected_response_ids,
)
from settings import Settings, load_settings


LOCAL_EVALUATOR_KEYS = tuple(LOCAL_EVALUATORS)


def build_local_preflight(
    connection: Any,
    response_ids: list[int],
    *,
    force: bool,
) -> dict[str, Any]:
    applications: list[dict[str, Any]] = []
    for response_id in response_ids:
        for evaluator_key in LOCAL_EVALUATOR_KEYS:
            reuse = completed_result_exists(connection, response_id, evaluator_key) and not force
            applications.append({
                "response_id": response_id,
                "evaluator": evaluator_key,
                "action": "reuse" if reuse else "run",
                "reason": (
                    "A completed active-version result already exists."
                    if reuse
                    else "The local evaluator will be applied to the saved response."
                ),
            })
    return {
        "evaluators": list(LOCAL_EVALUATOR_KEYS),
        "applications": applications,
        "application_count": sum(item["action"] == "run" for item in applications),
        "reused_count": sum(item["action"] == "reuse" for item in applications),
        "paid_application_count": 0,
        "estimated_cost": 0.0,
        "cost_status": "provider_free",
    }


def build_run_preflight(
    settings: Settings,
    connection: Any,
    response_ids: list[int],
    *,
    include_advanced: bool,
    force: bool,
) -> dict[str, Any]:
    local = build_local_preflight(connection, response_ids, force=force)
    advanced = None
    if include_advanced:
        advanced = build_advanced_preflight(
            settings,
            connection,
            response_ids,
            [
                "llm_judge",
                "ragas_faithfulness",
                "ragas_response_relevancy",
                "ragas_context_precision",
                "ragas_context_recall",
            ],
            attempts=1,
            force=force,
        )
    return {
        "responses": len(response_ids),
        "response_ids": response_ids,
        "requested_metric_count": 13 if include_advanced else 8,
        "local": local,
        "advanced": advanced,
        "application_count": local["application_count"] + (
            int(advanced["application_count"]) if advanced else 0
        ),
        "reused_count": local["reused_count"] + (
            int(advanced["reused_count"]) if advanced else 0
        ),
        "paid_application_count": (
            int(advanced["paid_application_count"]) if advanced else 0
        ),
        "estimated_cost": advanced["estimated_cost"] if advanced else 0.0,
        "cost_status": advanced["cost_status"] if advanced else "provider_free",
    }


def execute_local_plan(preflight: dict[str, Any]) -> list[dict[str, Any]]:
    outcomes: list[dict[str, Any]] = []
    by_response: dict[int, list[str]] = {}
    for application in preflight["applications"]:
        if application["action"] == "reuse":
            outcomes.append(dict(application))
            continue
        by_response.setdefault(int(application["response_id"]), []).append(
            str(application["evaluator"])
        )
    for response_id, evaluator_keys in by_response.items():
        for result in score_saved_response(response_id, evaluator_keys):
            outcomes.append({
                "response_id": response_id,
                "evaluator": result.evaluator_key,
                "action": "run",
                "result": asdict(result),
            })
    return outcomes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reapply local or all 13 evaluators to an existing saved run."
    )
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument(
        "--response-id",
        type=int,
        help="Evaluate one exact saved answer from the selected run.",
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument("--include-advanced", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--allow-paid", action="store_true")
    parser.add_argument("--allow-unknown-cost", action="store_true")
    parser.add_argument("--max-advanced-applications", type=int, default=5)
    parser.add_argument("--max-estimated-cost", type=float, default=1.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.run_id <= 0:
        parser.error("--run-id must be greater than zero")
    if args.response_id is not None and args.response_id <= 0:
        parser.error("--response-id must be greater than zero")
    if args.limit is not None and not 1 <= args.limit <= 100:
        parser.error("--limit must be between 1 and 100")
    if args.max_advanced_applications <= 0:
        parser.error("--max-advanced-applications must be greater than zero")
    if args.max_estimated_cost < 0:
        parser.error("--max-estimated-cost cannot be negative")

    settings = load_settings()
    with database_connection(settings) as connection:
        if args.response_id is not None:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT run_id FROM rag_responses WHERE response_id=%s",
                    (args.response_id,),
                )
                selected = cursor.fetchone()
            if not selected:
                parser.error("The selected saved answer does not exist.")
            if int(selected[0] or 0) != args.run_id:
                parser.error("The selected saved answer does not belong to this run.")
        response_ids = selected_response_ids(
            connection,
            response_id=args.response_id,
            run_id=args.run_id,
            limit=args.limit,
        )
        if not response_ids:
            parser.error("The selected run has no saved responses to evaluate.")
        preflight = build_run_preflight(
            settings,
            connection,
            response_ids,
            include_advanced=args.include_advanced,
            force=args.force,
        )

    advanced = preflight["advanced"]
    if advanced and int(advanced["application_count"]) > args.max_advanced_applications:
        parser.error(
            f"Plan has {advanced['application_count']} advanced applications; "
            "evaluate fewer responses or raise the configured application cap."
        )
    if (
        advanced
        and advanced["estimated_cost"] is not None
        and float(advanced["estimated_cost"]) > args.max_estimated_cost
    ):
        parser.error(
            f"Estimated cost {advanced['estimated_cost']:.6f} exceeds the configured "
            f"maximum {args.max_estimated_cost:.6f}."
        )

    payload: dict[str, Any] = {"preflight": preflight, "dry_run": args.dry_run}
    if not args.dry_run:
        outcomes = {"local": execute_local_plan(preflight["local"]), "advanced": []}
        if advanced:
            outcomes["advanced"] = execute_advanced_plan(
                settings,
                advanced,
                allow_paid=args.allow_paid,
                allow_unknown_cost=args.allow_unknown_cost,
            )
        payload["outcomes"] = outcomes
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
