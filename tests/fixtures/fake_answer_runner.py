"""Run rag/answer.py with retrieval and Gemini replaced by deterministic fakes.

Used by tests/test_user_accounts_http.py so the real PHP endpoints, sessions,
database and conversation code can be exercised without the embedding model or
a paid model call. Usage: fake_answer_runner.py rag/answer.py <answer.py args>
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "rag"))

import answer  # noqa: E402
from llm import HISTORY_PROMPT_HEADER  # noqa: E402
from query import SearchResult  # noqa: E402


def fake_search(**kwargs):
    return [
        SearchResult(
            rank=rank,
            source_path="admissions/first_year_admissions_overview.txt",
            category="admissions",
            chunk_index=rank - 1,
            text="First-year applicants need a minimum high school GPA of 2.0.",
            distance=0.4,
            keyword_score=8,
            document_id=None,
            chunk_id=None,
        )
        for rank in range(1, int(kwargs.get("top_k", 1)) + 1)
    ]


def fake_generator(prompt: str, _settings: object) -> str:
    question = prompt.split("Question:\n", 1)[1].split("\n", 1)[0]
    used_history = "yes" if HISTORY_PROMPT_HEADER in prompt else "no"
    return f"Fake answer to: {question} [history:{used_history}]"


_real_answer_question = answer.answer_question


def answer_question_with_fake_generator(*args, **kwargs):
    kwargs["generator"] = fake_generator
    return _real_answer_question(*args, **kwargs)


answer.search_with_optional_reranking = fake_search
answer.answer_question = answer_question_with_fake_generator

if __name__ == "__main__":
    sys.argv = sys.argv[1:]
    answer.main()
