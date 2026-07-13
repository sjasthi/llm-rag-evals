"""FP7 local evaluators applied to one already-saved RAG response."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import unicodedata
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from database import database_connection
from llm import REFUSAL_MESSAGE
from settings import PROJECT_ROOT, load_settings


DATASET_PATH = PROJECT_ROOT / "data" / "evaluation" / "metrostate_v1.json"
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class EvaluationInput:
    response_id: int
    question: str
    expected_answer: str
    actual_answer: str
    expected_source: str | None
    retrieved_sources: list[str]
    accepted_answers: list[str]
    required_facts: list[str]
    is_answerable: bool


@dataclass(frozen=True)
class EvaluationResult:
    evaluator_key: str
    raw_score: float | None
    normalized_score: float | None
    passed: bool | None
    explanation: str
    details: dict[str, Any]
    runtime_ms: int
    status: str = "completed"
    error_message: str | None = None


Evaluator = Callable[[EvaluationInput], tuple[float | None, bool | None, str, dict[str, Any]]]


EVALUATOR_DEFINITIONS = (
    ("exact_contains", "Exact or accepted-answer match", "lexical", "generation", "1.0", "Checks normalized equality or containment against reviewed accepted answers."),
    ("required_fact_coverage", "Required fact coverage", "lexical", "generation", "1.0", "Measures how many manually reviewed required facts appear in the response."),
    ("token_f1", "Token overlap F1", "lexical", "generation", "1.0", "Measures unigram precision and recall against the expected answer."),
    ("rouge_l", "ROUGE-L F1", "lexical", "generation", "1.0", "Measures longest-common-subsequence precision, recall, and F1 against the expected answer."),
    ("semantic_similarity", "Embedding semantic similarity", "semantic", "generation", "all-MiniLM-L6-v2", "Measures cosine similarity between expected and actual answer embeddings."),
    ("bertscore", "BERTScore F1", "semantic", "generation", "distilbert-base-uncased", "Measures contextual token similarity between the expected and actual answer."),
    ("expected_source_accuracy", "Expected source accuracy", "retrieval", "retrieval", "1.0", "Checks whether the reviewed source appears in the ranked retrieved contexts."),
    ("refusal_correctness", "Refusal correctness", "supporting", "generation", "1.0", "Checks fixed refusal behavior using the reviewed answerability label."),
)


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower()
    return " ".join(TOKEN_PATTERN.findall(value))


def exact_contains(item: EvaluationInput) -> tuple[float, bool, str, dict[str, Any]]:
    actual = normalize_text(item.actual_answer)
    candidates = [item.expected_answer, *item.accepted_answers]
    normalized = [normalize_text(candidate) for candidate in candidates if candidate.strip()]
    exact = any(actual == candidate for candidate in normalized)
    contains = any(candidate in actual or actual in candidate for candidate in normalized if candidate)
    score = 1.0 if exact else 0.75 if contains else 0.0
    return score, contains, "Exact match." if exact else "Accepted answer is contained." if contains else "No accepted lexical match.", {"exact": exact, "contains": contains, "candidate_count": len(normalized)}


def required_fact_coverage(item: EvaluationInput) -> tuple[float | None, bool | None, str, dict[str, Any]]:
    if not item.required_facts:
        return None, None, "No required facts apply to this question.", {"matched": [], "missing": []}
    actual = normalize_text(item.actual_answer)
    matched = [fact for fact in item.required_facts if normalize_text(fact) in actual]
    missing = [fact for fact in item.required_facts if fact not in matched]
    score = len(matched) / len(item.required_facts)
    return score, score == 1.0, f"Matched {len(matched)} of {len(item.required_facts)} required facts.", {"matched": matched, "missing": missing}


def token_f1(item: EvaluationInput) -> tuple[float, bool, str, dict[str, Any]]:
    expected = TOKEN_PATTERN.findall(normalize_text(item.expected_answer))
    actual = TOKEN_PATTERN.findall(normalize_text(item.actual_answer))
    expected_counts = {token: expected.count(token) for token in set(expected)}
    actual_counts = {token: actual.count(token) for token in set(actual)}
    overlap = sum(min(count, actual_counts.get(token, 0)) for token, count in expected_counts.items())
    precision = overlap / len(actual) if actual else 0.0
    recall = overlap / len(expected) if expected else 0.0
    score = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return score, score >= 0.7, f"Token F1 is {score:.3f} (descriptive threshold 0.70).", {"precision": precision, "recall": recall, "overlap_tokens": overlap}


def _lcs_length(left: list[str], right: list[str]) -> int:
    previous = [0] * (len(right) + 1)
    for left_token in left:
        current = [0]
        for index, right_token in enumerate(right, start=1):
            current.append(previous[index - 1] + 1 if left_token == right_token else max(previous[index], current[-1]))
        previous = current
    return previous[-1]


def rouge_l(item: EvaluationInput) -> tuple[float, bool, str, dict[str, Any]]:
    expected = TOKEN_PATTERN.findall(normalize_text(item.expected_answer))
    actual = TOKEN_PATTERN.findall(normalize_text(item.actual_answer))
    lcs = _lcs_length(expected, actual)
    precision = lcs / len(actual) if actual else 0.0
    recall = lcs / len(expected) if expected else 0.0
    score = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return score, score >= 0.7, f"ROUGE-L F1 is {score:.3f} (descriptive threshold 0.70).", {"precision": precision, "recall": recall, "lcs_tokens": lcs}


def semantic_similarity(item: EvaluationInput) -> tuple[float, bool, str, dict[str, Any]]:
    from sentence_transformers import util

    model = _semantic_model()
    embeddings = model.encode([item.expected_answer, item.actual_answer], convert_to_tensor=True)
    score = float(util.cos_sim(embeddings[0], embeddings[1]).item())
    return score, score >= 0.75, f"Embedding cosine similarity is {score:.3f} (descriptive threshold 0.75).", {"model": "all-MiniLM-L6-v2"}


@lru_cache(maxsize=1)
def _semantic_model() -> Any:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("all-MiniLM-L6-v2")


def bertscore(item: EvaluationInput) -> tuple[float, bool, str, dict[str, Any]]:
    precision, recall, f1 = _bert_scorer().score([item.actual_answer], [item.expected_answer])
    precision_value = float(precision[0].item())
    recall_value = float(recall[0].item())
    score = float(f1[0].item())
    return score, score >= 0.8, f"BERTScore F1 is {score:.3f} (descriptive threshold 0.80).", {"precision": precision_value, "recall": recall_value, "model": "distilbert-base-uncased"}


@lru_cache(maxsize=1)
def _bert_scorer() -> Any:
    from bert_score import BERTScorer

    return BERTScorer(model_type="distilbert-base-uncased", lang="en")


def expected_source_accuracy(item: EvaluationInput) -> tuple[float | None, bool | None, str, dict[str, Any]]:
    if not item.is_answerable or not item.expected_source:
        return None, None, "Expected-source scoring does not apply to this unanswerable question.", {"expected_source": item.expected_source}
    normalized_expected = item.expected_source.replace("\\", "/").lower()
    sources = [source.replace("\\", "/").lower() for source in item.retrieved_sources]
    rank = next((index for index, source in enumerate(sources, start=1) if source == normalized_expected), None)
    score = 1.0 if rank is not None else 0.0
    return score, rank is not None, f"Expected source was retrieved at rank {rank}." if rank else "Expected source was not retrieved.", {"expected_source": item.expected_source, "retrieved_rank": rank, "retrieved_sources": item.retrieved_sources}


def refusal_correctness(item: EvaluationInput) -> tuple[float, bool, str, dict[str, Any]]:
    refused = normalize_text(item.actual_answer) == normalize_text(REFUSAL_MESSAGE)
    correct = refused if not item.is_answerable else not refused
    return float(correct), correct, "Refusal behavior matches the answerability label." if correct else "Refusal behavior conflicts with the answerability label.", {"is_answerable": item.is_answerable, "returned_fixed_refusal": refused}


LOCAL_EVALUATORS: dict[str, Evaluator] = {
    "exact_contains": exact_contains,
    "required_fact_coverage": required_fact_coverage,
    "token_f1": token_f1,
    "rouge_l": rouge_l,
    "semantic_similarity": semantic_similarity,
    "bertscore": bertscore,
    "expected_source_accuracy": expected_source_accuracy,
    "refusal_correctness": refusal_correctness,
}


def run_evaluator(key: str, item: EvaluationInput) -> EvaluationResult:
    started = time.perf_counter()
    try:
        score, passed, explanation, details = LOCAL_EVALUATORS[key](item)
        runtime_ms = round((time.perf_counter() - started) * 1000)
        normalized = None if score is None else max(0.0, min(1.0, score))
        return EvaluationResult(key, score, normalized, passed, explanation, details, runtime_ms)
    except Exception as error:
        runtime_ms = round((time.perf_counter() - started) * 1000)
        return EvaluationResult(key, None, None, None, "Evaluator failed; inspect the stored error.", {}, runtime_ms, "failed", str(error))


def load_seed(path: Path = DATASET_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def seed_dataset() -> dict[str, int]:
    seed = load_seed()
    settings = load_settings()
    with database_connection(settings) as connection:
        connection.start_transaction()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO evaluation_datasets (dataset_name, version, description, status, reviewed_at)
                       VALUES (%s, %s, %s, %s, CASE WHEN %s='reviewed' THEN CURRENT_TIMESTAMP ELSE NULL END)
                       ON DUPLICATE KEY UPDATE dataset_id=LAST_INSERT_ID(dataset_id), description=VALUES(description),
                         status=VALUES(status), reviewed_at=VALUES(reviewed_at)""",
                    (seed["dataset_name"], seed["version"], seed.get("description"), seed.get("status", "draft"), seed.get("status", "draft")),
                )
                dataset_id = int(cursor.lastrowid)
                for order, question in enumerate(seed["questions"], start=1):
                    question_key = hashlib.sha256(question["question"].strip().encode("utf-8")).hexdigest()
                    cursor.execute(
                        """INSERT INTO evaluation_questions
                           (question_key, question_text, expected_answer, expected_source, expected_evidence, accepted_answers,
                            required_facts, category, difficulty, is_answerable, reviewer_notes, review_status, is_active)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE)
                           ON DUPLICATE KEY UPDATE question_id=LAST_INSERT_ID(question_id),
                             question_text=VALUES(question_text), expected_answer=VALUES(expected_answer),
                             expected_source=VALUES(expected_source), expected_evidence=VALUES(expected_evidence),
                             accepted_answers=VALUES(accepted_answers), required_facts=VALUES(required_facts),
                             category=VALUES(category), difficulty=VALUES(difficulty),
                             is_answerable=VALUES(is_answerable), reviewer_notes=VALUES(reviewer_notes),
                             review_status=VALUES(review_status)""",
                        (question_key, question["question"], question["expected_answer"], question.get("expected_source"), question.get("expected_evidence"), json.dumps(question.get("accepted_answers", [])), json.dumps(question.get("required_facts", [])), question["category"], question["difficulty"], question["is_answerable"], question.get("reviewer_notes"), question.get("review_status", "reviewed")),
                    )
                    question_id = int(cursor.lastrowid)
                    cursor.execute(
                        """INSERT INTO evaluation_question_memberships (dataset_id, question_id, display_order)
                           VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE display_order=VALUES(display_order)""",
                        (dataset_id, question_id, order),
                    )
                for key, name, family, dimension, version, description in EVALUATOR_DEFINITIONS:
                    cursor.execute(
                        """INSERT INTO evaluator_definitions
                           (evaluator_key, display_name, family, dimension, version, description, configuration_json, is_local, is_deterministic)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,TRUE,TRUE)
                           ON DUPLICATE KEY UPDATE display_name=VALUES(display_name), description=VALUES(description), configuration_json=VALUES(configuration_json)""",
                        (key, name, family, dimension, version, description, json.dumps({"implementation": "rag/evaluation.py"})),
                    )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return {"dataset_id": dataset_id, "questions": len(seed["questions"]), "evaluators": len(EVALUATOR_DEFINITIONS)}


def _json_list(value: Any) -> list[str]:
    if value is None:
        return []
    parsed = json.loads(value) if isinstance(value, str) else value
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def load_evaluation_input(connection: Any, response_id: int) -> EvaluationInput:
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(
            """SELECT r.response_id, r.question_text, r.answer_text,
                      q.expected_answer, q.expected_source, q.accepted_answers,
                      q.required_facts, q.is_answerable
               FROM rag_responses r
               JOIN evaluation_questions q ON q.question_id = r.question_id
               WHERE r.response_id = %s""",
            (response_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("Saved response is missing or is not linked to an evaluation question.")
        cursor.execute(
            """SELECT d.source_path
               FROM retrieved_contexts c
               LEFT JOIN documents d ON d.document_id = c.document_id
               WHERE c.response_id = %s ORDER BY c.rank_position""",
            (response_id,),
        )
        sources = [str(item["source_path"]) for item in cursor.fetchall() if item["source_path"]]
    return EvaluationInput(
        response_id=int(row["response_id"]),
        question=str(row["question_text"]),
        expected_answer=str(row["expected_answer"]),
        actual_answer=str(row["answer_text"]),
        expected_source=row["expected_source"],
        retrieved_sources=sources,
        accepted_answers=_json_list(row["accepted_answers"]),
        required_facts=_json_list(row["required_facts"]),
        is_answerable=bool(row["is_answerable"]),
    )


def score_saved_response(response_id: int, evaluator_keys: list[str]) -> list[EvaluationResult]:
    unknown = sorted(set(evaluator_keys) - LOCAL_EVALUATORS.keys())
    if unknown:
        raise ValueError(f"Unknown evaluators: {', '.join(unknown)}")
    settings = load_settings()
    with database_connection(settings) as connection:
        item = load_evaluation_input(connection, response_id)
        results = [run_evaluator(key, item) for key in evaluator_keys]
        try:
            connection.commit()
            connection.start_transaction()
            with connection.cursor() as cursor:
                for result in results:
                    cursor.execute(
                        "SELECT evaluator_id FROM evaluator_definitions WHERE evaluator_key=%s AND is_active=TRUE ORDER BY evaluator_id DESC LIMIT 1",
                        (result.evaluator_key,),
                    )
                    evaluator = cursor.fetchone()
                    if not evaluator:
                        raise ValueError(f"Evaluator definition {result.evaluator_key!r} is not seeded.")
                    cursor.execute(
                        """INSERT INTO evaluator_results
                           (response_id, evaluator_id, status, raw_score, normalized_score, passed,
                            explanation, details_json, runtime_ms, estimated_cost, error_message)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,0,%s)
                           ON DUPLICATE KEY UPDATE status=VALUES(status), raw_score=VALUES(raw_score),
                             normalized_score=VALUES(normalized_score), passed=VALUES(passed),
                             explanation=VALUES(explanation), details_json=VALUES(details_json),
                             runtime_ms=VALUES(runtime_ms), estimated_cost=0, error_message=VALUES(error_message)""",
                        (response_id, int(evaluator[0]), result.status, result.raw_score, result.normalized_score,
                         result.passed, result.explanation, json.dumps(result.details), result.runtime_ms, result.error_message),
                    )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed and run FP7 local RAG evaluators.")
    parser.add_argument("--seed", action="store_true", help="Import the versioned draft question dataset and evaluator definitions.")
    parser.add_argument("--response-id", type=int, help="Score one response already linked to an evaluation question.")
    parser.add_argument("--evaluators", default="exact_contains,required_fact_coverage,token_f1,expected_source_accuracy,refusal_correctness")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.seed:
        result = seed_dataset()
        print(json.dumps(result, indent=2) if args.json else f"Seeded dataset {result['dataset_id']} with {result['questions']} questions and {result['evaluators']} local evaluators.")
        return
    if args.response_id:
        results = score_saved_response(args.response_id, [key.strip() for key in args.evaluators.split(",") if key.strip()])
        print(json.dumps([asdict(result) for result in results], indent=2) if args.json else "\n".join(f"{result.evaluator_key}: {result.normalized_score} - {result.explanation}" for result in results))
        return
    parser.error("choose --seed or --response-id")


if __name__ == "__main__":
    main()
