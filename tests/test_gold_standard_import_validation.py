import copy
import sys
from pathlib import Path

import pytest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "rag"))

import evaluation
from evaluation import validate_existing_question


@pytest.fixture
def existing_question():
    return {
        "expected_answer": "8,400 gallons",
        "expected_source": "TC02_Campus_Water_Savings_Embedded_Image_v3.pdf",
        "expected_evidence": "Total water savings: 8,400 gallons.",
        "accepted_answers": '["8400 gallons"]',
        "required_facts": '["8400 gallons", "8000 gallon goal"]',
        "category": "pdf_chart",
        "difficulty": "medium",
        "is_answerable": 1,
        "reviewer_notes": "Verified against the PDF chart.",
        "review_status": "reviewed",
    }


@pytest.fixture
def incoming_question(existing_question):
    question = copy.deepcopy(existing_question)
    question["question"] = "What were the total water savings?"
    question["accepted_answers"] = ["8400 gallons"]
    question["required_facts"] = [
        "8400 gallons",
        "8000 gallon goal",
    ]
    return question


def test_identical_question_is_accepted(existing_question, incoming_question):
    validate_existing_question(existing_question, incoming_question)


def test_conflicting_answer_is_rejected(existing_question, incoming_question):
    incoming_question["expected_answer"] = "9,000 gallons"

    with pytest.raises(ValueError, match="expected_answer"):
        validate_existing_question(existing_question, incoming_question)


def test_conflicting_source_is_rejected(existing_question, incoming_question):
    incoming_question["expected_source"] = "different_document.pdf"

    with pytest.raises(ValueError, match="expected_source"):
        validate_existing_question(existing_question, incoming_question)


def test_conflicting_required_facts_are_rejected(
    existing_question,
    incoming_question,
):
    incoming_question["required_facts"] = ["9000 gallons"]

    with pytest.raises(ValueError, match="required_facts"):
        validate_existing_question(existing_question, incoming_question)


def test_conflicting_review_status_is_rejected(
    existing_question,
    incoming_question,
):
    incoming_question["review_status"] = "draft"

    with pytest.raises(ValueError, match="review_status"):
        validate_existing_question(existing_question, incoming_question)

def test_missing_review_status_uses_importer_default(
    existing_question,
    incoming_question,
):
    incoming_question.pop("review_status")

    validate_existing_question(existing_question, incoming_question)

def test_conflicting_question_rolls_back_transaction(
    existing_question,
    incoming_question,
):
    seed = {
        "dataset_name": "Metro State Multimodal",
        "version": "v1",
        "status": "draft",
        "questions": [incoming_question],
    }

    conflicting_question = existing_question.copy()
    conflicting_question["expected_answer"] = "9,000 gallons"

    columns = list(conflicting_question.keys())
    row = tuple(conflicting_question.values())

    cursor = MagicMock()
    cursor.lastrowid = 123
    cursor.fetchone.return_value = row
    cursor.description = [(column,) for column in columns]

    connection = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor

    with (
        patch.object(evaluation, "load_seed", return_value=seed),
        patch.object(evaluation, "load_settings"),
        patch.object(evaluation, "database_connection") as mock_database,
    ):
        mock_database.return_value.__enter__.return_value = connection

        with pytest.raises(ValueError, match="expected_answer"):
            evaluation.seed_dataset()

    connection.start_transaction.assert_called_once()
    connection.rollback.assert_called_once()
    connection.commit.assert_not_called()

def test_new_question_import_commits_transaction(incoming_question):
    seed = {
        "dataset_name": "Metro State Multimodal",
        "version": "v1",
        "status": "draft",
        "questions": [incoming_question],
    }

    cursor = MagicMock()
    cursor.lastrowid = 123
    cursor.fetchone.return_value = None

    connection = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor

    with (
        patch.object(evaluation, "load_seed", return_value=seed),
        patch.object(evaluation, "load_settings"),
        patch.object(evaluation, "database_connection") as mock_database,
    ):
        mock_database.return_value.__enter__.return_value = connection

        result = evaluation.seed_dataset()

    connection.start_transaction.assert_called_once()
    connection.commit.assert_called_once()
    connection.rollback.assert_not_called()

    assert result["dataset_id"] == 123
    assert result["questions"] == 1

    executed_queries = [
        call.args[0]
        for call in cursor.execute.call_args_list
    ]

    assert any(
        "INSERT INTO evaluation_questions" in query
        for query in executed_queries
    )

    assert any(
        "INSERT INTO evaluation_question_memberships" in query
        for query in executed_queries
    )