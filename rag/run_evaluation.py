"""Generate one saved response per reviewed question and score that response once."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict
from dataclasses import replace

from answer import answer_question
from database import database_connection, get_or_create_model_setting
from evaluation import score_saved_response
from llm import estimated_generation_application_cost
from provenance import code_provenance
from query import retrieval_provenance
from settings import load_settings


DEFAULT_EVALUATORS = [
    "exact_contains",
    "required_fact_coverage",
    "token_f1",
    "rouge_l",
    "semantic_similarity",
    "bertscore",
    "expected_source_accuracy",
    "refusal_correctness",
]


def _json_list(value: object) -> list[object]:
    if value is None:
        return []
    parsed = json.loads(value) if isinstance(value, str) else value
    return list(parsed) if isinstance(parsed, list) else []


def select_questions(
    available_questions: list[dict[str, object]],
    *,
    limit: int | None,
    question_ids: list[int] | None,
) -> list[dict[str, object]]:
    """Select a stable reviewed subset while preserving requested order."""
    if not question_ids:
        return available_questions[:limit] if limit is not None else available_questions

    normalized_ids = [int(value) for value in question_ids]
    if len(normalized_ids) != len(set(normalized_ids)):
        raise ValueError("question_ids must not contain duplicates")
    if limit is not None and limit != len(normalized_ids):
        raise ValueError("limit must match the number of explicitly selected questions")

    questions_by_id = {
        int(question["question_id"]): question for question in available_questions
    }
    missing = [question_id for question_id in normalized_ids if question_id not in questions_by_id]
    if missing:
        raise ValueError(
            "Selected questions are not active reviewed members of this dataset: "
            + ", ".join(str(value) for value in missing)
        )
    return [questions_by_id[question_id] for question_id in normalized_ids]


def evaluation_snapshot(
    question: dict[str, object], dataset: dict[str, object]
) -> dict[str, object]:
    """Freeze the reviewed answer-key fields used by one generated response."""
    return {
        "snapshot_schema_version": 1,
        "dataset_id": dataset.get("dataset_id"),
        "dataset_name": dataset.get("dataset_name"),
        "dataset_version": dataset.get("version"),
        "question_id": int(question["question_id"]),
        "question_key": question.get("question_key"),
        "question_text": str(question["question_text"]),
        "expected_answer": str(question["expected_answer"]),
        "expected_source": question.get("expected_source"),
        "expected_evidence": question.get("expected_evidence"),
        "accepted_answers": _json_list(question.get("accepted_answers")),
        "required_facts": _json_list(question.get("required_facts")),
        "category": question.get("category"),
        "difficulty": question.get("difficulty"),
        "is_answerable": bool(question.get("is_answerable")),
        "review_status": question.get("review_status"),
        "question_updated_at": str(question.get("updated_at")),
    }


def create_run(
    dataset_id: int,
    name: str,
    limit: int | None,
    *,
    retrieval_method: str = "chroma_vector",
    top_k: int | None = None,
    model: str | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    experiment_key: str | None = None,
    baseline_run_id: int | None = None,
    change_from_baseline: str | None = None,
    corpus_variant_key: str = "full_current",
    categories: list[str] | None = None,
    question_ids: list[int] | None = None,
    dry_run: bool = False,
    allow_paid: bool = False,
    allow_unknown_cost: bool = False,
    max_responses: int = 5,
    max_estimated_cost: float = 1.0,
) -> dict[str, object]:
    if dataset_id <= 0:
        raise ValueError("dataset_id must be greater than zero")
    if not name.strip():
        raise ValueError("name cannot be empty")
    if len(name.strip()) > 120:
        raise ValueError("name must be 120 characters or fewer")
    if limit is not None and limit <= 0:
        raise ValueError("limit must be greater than zero")
    if question_ids is not None and any(int(value) <= 0 for value in question_ids):
        raise ValueError("question_ids must contain positive integers")
    if retrieval_method not in {"chroma_vector", "mysql_keyword"}:
        raise ValueError(f"Unsupported retrieval method {retrieval_method!r}")
    if top_k is not None and top_k <= 0:
        raise ValueError("top_k must be greater than zero")
    if model is not None and not model.strip():
        raise ValueError("model cannot be empty")
    if temperature is not None and not 0.0 <= temperature <= 1.0:
        raise ValueError("temperature must be between 0.0 and 1.0")
    if top_p is not None and not 0.0 <= top_p <= 1.0:
        raise ValueError("top_p must be between 0.0 and 1.0")
    if max_responses <= 0:
        raise ValueError("max_responses must be greater than zero")
    if max_estimated_cost < 0:
        raise ValueError("max_estimated_cost cannot be negative")
    if experiment_key is not None and len(experiment_key.strip()) > 120:
        raise ValueError("experiment_key must be 120 characters or fewer")
    if baseline_run_id is not None and baseline_run_id <= 0:
        raise ValueError("baseline_run_id must be greater than zero")
    if change_from_baseline is not None and len(change_from_baseline.strip()) > 500:
        raise ValueError("change_from_baseline must be 500 characters or fewer")
    if not corpus_variant_key.strip() or len(corpus_variant_key.strip()) > 120:
        raise ValueError("corpus_variant must be between 1 and 120 characters")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,119}", corpus_variant_key.strip()):
        raise ValueError("corpus_variant must use lowercase letters, numbers, underscores, or hyphens")
    for category in categories or []:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,49}", category.strip()):
            raise ValueError(f"Invalid source category {category!r}")
    base_settings = load_settings()
    settings = replace(
        base_settings,
        llm_chat_model=(model.strip() if model is not None else base_settings.llm_chat_model),
        llm_temperature=(
            float(temperature) if temperature is not None else base_settings.llm_temperature
        ),
        llm_top_p=float(top_p) if top_p is not None else base_settings.llm_top_p,
    )
    selected_top_k = top_k or settings.retrieval_top_k
    normalized_categories = sorted({value.strip() for value in (categories or []) if value.strip()})
    controlled_differences: list[str] = []
    with database_connection(settings) as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                """SELECT q.question_id, q.question_key, q.question_text,
                          q.expected_answer, q.expected_source, q.expected_evidence,
                          q.accepted_answers, q.required_facts, q.category, q.difficulty,
                          q.is_answerable, q.review_status, q.updated_at
                   FROM evaluation_question_memberships m
                   JOIN evaluation_questions q ON q.question_id=m.question_id
                   WHERE m.dataset_id=%s AND q.is_active=TRUE AND q.review_status='reviewed'
                   ORDER BY m.display_order""",
                (dataset_id,),
            )
            available_questions = cursor.fetchall()
        questions = select_questions(
            available_questions,
            limit=limit,
            question_ids=question_ids,
        )
        if not questions:
            raise ValueError("The selected dataset has no reviewed active questions.")
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT dataset_id, dataset_name, version FROM evaluation_datasets WHERE dataset_id=%s",
                (dataset_id,),
            )
            dataset = cursor.fetchone()
            if not dataset:
                raise ValueError("The selected evaluation dataset does not exist.")
            baseline = None
            baseline_configuration: dict[str, object] = {}
            if baseline_run_id is not None:
                cursor.execute(
                    """SELECT run.run_id, run.dataset_id, run.experiment_key, run.status,
                              run.run_configuration_json,
                              settings.retrieval_method, settings.chat_model, settings.top_k,
                              settings.temperature, settings.top_p,
                              (SELECT COUNT(*) FROM rag_responses response
                               WHERE response.run_id=run.run_id) AS response_count
                       FROM evaluation_runs run
                       JOIN model_settings settings ON settings.setting_id=run.setting_id
                       WHERE run.run_id=%s""",
                    (baseline_run_id,),
                )
                baseline = cursor.fetchone()
                if not baseline:
                    raise ValueError("The selected baseline run does not exist.")
                if baseline["status"] != "completed":
                    raise ValueError("A comparison baseline must be a completed run.")
                if int(baseline["dataset_id"] or 0) != dataset_id:
                    raise ValueError("A comparison baseline must use the same dataset.")
                if not (change_from_baseline or "").strip():
                    raise ValueError(
                        "A comparison run must document change_from_baseline."
                    )
                baseline_configuration_value = baseline.get("run_configuration_json")
                if isinstance(baseline_configuration_value, str):
                    baseline_configuration_value = json.loads(baseline_configuration_value)
                if isinstance(baseline_configuration_value, dict):
                    baseline_configuration = baseline_configuration_value
                if experiment_key is None:
                    experiment_key = str(
                        baseline["experiment_key"] or f"baseline-{baseline_run_id}"
                    )
                cursor.execute(
                    """SELECT question_id
                       FROM rag_responses
                       WHERE run_id=%s AND question_id IS NOT NULL
                       ORDER BY response_id""",
                    (baseline_run_id,),
                )
                baseline_question_ids = [int(row["question_id"]) for row in cursor.fetchall()]
            elif change_from_baseline:
                raise ValueError(
                    "change_from_baseline requires a declared baseline_run_id."
                )
            cursor.execute(
                """SELECT document_id, source_path, source_hash, category
                   FROM documents WHERE status='ingested'
                   ORDER BY document_id"""
            )
            documents = [
                row for row in cursor.fetchall()
                if not normalized_categories or str(row["category"]) in normalized_categories
            ]
        manifest = [
            {
                "document_id": int(document["document_id"]),
                "source_path": str(document["source_path"]),
                "source_hash": document["source_hash"],
                "category": str(document["category"]),
            }
            for document in documents
        ]
        if not manifest:
            raise ValueError(
                "The selected corpus/category variant contains no ingested documents."
            )
        manifest_hash = hashlib.sha256(
            json.dumps(manifest, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        if baseline is not None:
            selected_question_ids = [int(question["question_id"]) for question in questions]
            baseline_response_count = int(baseline.get("response_count") or 0)
            if baseline_response_count != len(questions):
                raise ValueError(
                    "A controlled comparison must use the same number of reviewed questions "
                    f"as its baseline ({baseline_response_count})."
                )
            if baseline_question_ids != selected_question_ids:
                raise ValueError(
                    "A controlled comparison must use the exact ordered reviewed-question "
                    "set saved by its baseline."
                )
            baseline_categories = sorted(
                str(value) for value in (baseline_configuration.get("categories") or [])
            )
            baseline_manifest_hash = str(
                baseline_configuration.get("corpus_manifest_hash") or ""
            )
            comparisons = {
                "retrieval method": (
                    str(baseline.get("retrieval_method") or ""),
                    retrieval_method,
                ),
                "source chunks (top-k)": (
                    int(baseline.get("top_k") or 0),
                    int(selected_top_k),
                ),
                "answer model": (
                    str(baseline.get("chat_model") or ""),
                    settings.llm_chat_model,
                ),
                "temperature": (
                    float(baseline.get("temperature") or 0.0),
                    float(settings.llm_temperature),
                ),
                "top-p": (
                    float(baseline.get("top_p") or 0.0),
                    float(settings.llm_top_p),
                ),
            }
            controlled_differences = [
                label for label, (before, after) in comparisons.items()
                if before != after
            ]
            corpus_changed = baseline_categories != normalized_categories
            if baseline_manifest_hash and baseline_manifest_hash != manifest_hash:
                corpus_changed = True
            if corpus_changed:
                controlled_differences.append("source category composition")
            if len(controlled_differences) != 1:
                observed = ", ".join(controlled_differences) if controlled_differences else "none"
                raise ValueError(
                    "A controlled comparison must change exactly one supported setting; "
                    f"observed changes: {observed}."
                )
        captured_code = code_provenance()
        per_response_cost = estimated_generation_application_cost(settings)
        estimated_cost = (
            None
            if per_response_cost is None
            else round(per_response_cost * len(questions), 8)
        )
        preflight: dict[str, object] = {
            "response_count": len(questions),
            "paid_call_count": len(questions),
            "estimated_cost_per_response": per_response_cost,
            "estimated_cost": estimated_cost,
            "cost_status": "unknown" if estimated_cost is None else "estimated",
            "cost_note": (
                "Provider pricing is not configured, so paid-call cost is unknown."
                if estimated_cost is None
                else "Estimate uses configured per-million token rates and conservative token assumptions."
            ),
            "max_responses": max_responses,
            "max_estimated_cost": max_estimated_cost,
            "controlled_differences": controlled_differences,
        }
        run_configuration = {
            "dataset": dataset,
            "retrieval_method": retrieval_method,
            "retrieval_algorithm": retrieval_provenance(retrieval_method),
            "top_k": selected_top_k,
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "embedding_model": settings.embedding_model,
            "answer_provider": settings.llm_provider,
            "answer_model": settings.llm_chat_model,
            "temperature": settings.llm_temperature,
            "top_p": settings.llm_top_p,
            "corpus_variant_key": corpus_variant_key,
            "baseline_run_id": baseline_run_id,
            "change_from_baseline": (
                change_from_baseline.strip() if change_from_baseline else None
            ),
            "categories": normalized_categories,
            "document_count": len(manifest),
            "corpus_manifest_hash": manifest_hash,
            "documents": manifest,
            "question_ids": [int(question["question_id"]) for question in questions],
            "question_keys": [question.get("question_key") for question in questions],
            "question_count": len(questions),
            "evaluators": DEFAULT_EVALUATORS,
            "code_provenance": captured_code,
            "preflight": preflight,
        }
        if len(questions) > max_responses:
            raise ValueError(
                f"Plan has {len(questions)} paid responses; raise max_responses deliberately to continue."
            )
        if not dry_run and not allow_paid:
            raise ValueError("Baseline model-backed execution requires allow_paid=True / --allow-paid.")
        if not dry_run and estimated_cost is None and not allow_unknown_cost:
            raise ValueError(
                "Baseline execution cost is unknown. Configure generation pricing or "
                "pass --allow-unknown-cost deliberately."
            )
        if (
            not dry_run
            and estimated_cost is not None
            and estimated_cost > max_estimated_cost
        ):
            raise ValueError(
                f"Estimated cost {estimated_cost:.6f} exceeds max_estimated_cost "
                f"{max_estimated_cost:.6f}."
            )
        if dry_run:
            return {
                "run_id": None,
                "status": "dry_run",
                "responses": [],
                "configuration": run_configuration,
                "preflight": preflight,
            }

        setting_id = get_or_create_model_setting(
            connection,
            provider=settings.llm_provider,
            chat_model=settings.llm_chat_model,
            embedding_model=settings.embedding_model,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            top_k=selected_top_k,
            temperature=settings.llm_temperature,
            top_p=settings.llm_top_p,
            retrieval_method=retrieval_method,
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO evaluation_runs
                   (setting_id, dataset_id, baseline_run_id, run_name, experiment_key,
                    corpus_variant_key, run_configuration_json, status, started_at, notes)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,'running',CURRENT_TIMESTAMP,%s)""",
                (
                    setting_id, dataset_id, baseline_run_id, name, experiment_key,
                    corpus_variant_key, json.dumps(run_configuration),
                    "Reviewed questions only; one saved answer/context set per question.",
                ),
            )
            run_id = int(cursor.lastrowid)
        connection.commit()

    outcomes: list[dict[str, object]] = []
    status = "failed"
    try:
        for question in questions:
            answer = answer_question(
                str(question["question_text"]),
                top_k=selected_top_k,
                question_id=int(question["question_id"]),
                run_id=run_id,
                retrieval_method=retrieval_method,
                categories=normalized_categories,
                evaluation_snapshot=evaluation_snapshot(question, dataset),
                run_code_provenance=captured_code,
                model=settings.llm_chat_model,
                temperature=settings.llm_temperature,
                top_p=settings.llm_top_p,
            )
            if answer.response_id is None:
                raise RuntimeError(answer.persistence_error or "Generated response was not saved.")
            scores = score_saved_response(answer.response_id, DEFAULT_EVALUATORS)
            outcomes.append({
                "question_id": int(question["question_id"]),
                "response_id": answer.response_id,
                "answer": answer.answer,
                "latency_ms": answer.latency_ms,
                "scores": [asdict(score) for score in scores],
            })
        status = "completed"
    except Exception:
        status = "failed"
        raise
    finally:
        with database_connection(settings) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE evaluation_runs SET status=%s, completed_at=CURRENT_TIMESTAMP WHERE run_id=%s",
                    (status, run_id),
                )
            connection.commit()
    return {
        "run_id": run_id,
        "status": status,
        "responses": outcomes,
        "configuration": run_configuration,
        "preflight": preflight,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run reviewed FP7 questions through the fixed RAG baseline.")
    parser.add_argument("--dataset-id", type=int, required=True)
    parser.add_argument("--name", default="FP7 local baseline")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--retrieval",
        choices=("chroma_vector", "mysql_keyword"),
        default="chroma_vector",
    )
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--model")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--top-p", type=float)
    parser.add_argument("--experiment-key")
    parser.add_argument("--baseline-run-id", type=int)
    parser.add_argument(
        "--change-from-baseline",
        help="Single controlled variable changed from the declared baseline run.",
    )
    parser.add_argument("--corpus-variant", default="full_current")
    parser.add_argument("--categories", help="Comma-separated category subset.")
    parser.add_argument(
        "--question-ids",
        help="Optional comma-separated exact reviewed question IDs in execution order.",
    )
    parser.add_argument("--max-responses", type=int, default=5)
    parser.add_argument("--max-estimated-cost", type=float, default=1.0)
    parser.add_argument("--allow-paid", action="store_true")
    parser.add_argument(
        "--allow-unknown-cost",
        action="store_true",
        help="Permit paid calls when generation pricing has not been configured.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the frozen configuration and cost preflight without saving a run or calling Gemini.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be greater than zero")
    if args.top_k is not None and args.top_k <= 0:
        parser.error("--top-k must be greater than zero")
    if args.temperature is not None and not 0.0 <= args.temperature <= 1.0:
        parser.error("--temperature must be between 0.0 and 1.0")
    if args.top_p is not None and not 0.0 <= args.top_p <= 1.0:
        parser.error("--top-p must be between 0.0 and 1.0")
    if args.max_responses <= 0:
        parser.error("--max-responses must be greater than zero")
    if args.max_estimated_cost < 0:
        parser.error("--max-estimated-cost cannot be negative")
    try:
        result = create_run(
            args.dataset_id,
            args.name,
            args.limit,
            retrieval_method=args.retrieval,
            top_k=args.top_k,
            model=args.model,
            temperature=args.temperature,
            top_p=args.top_p,
            experiment_key=args.experiment_key,
            baseline_run_id=args.baseline_run_id,
            change_from_baseline=args.change_from_baseline,
            corpus_variant_key=args.corpus_variant,
            categories=[value.strip() for value in (args.categories or "").split(",") if value.strip()],
            question_ids=[
                int(value.strip())
                for value in (args.question_ids or "").split(",")
                if value.strip()
            ] or None,
            dry_run=args.dry_run,
            allow_paid=args.allow_paid,
            allow_unknown_cost=args.allow_unknown_cost,
            max_responses=args.max_responses,
            max_estimated_cost=args.max_estimated_cost,
        )
    except ValueError as error:
        parser.error(str(error))
    if args.json or args.dry_run:
        print(json.dumps(result, indent=2))
    else:
        print(f"Run {result['run_id']} completed with {len(result['responses'])} responses.")


if __name__ == "__main__":
    main()
