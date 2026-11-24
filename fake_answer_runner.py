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
from llm import HISTORY_PROMPT_HEADER, rewrite_follow_up_query  # noqa: E402
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


def fake_rewrite_model(prompt: str, _settings: object, *, system_instruction: str):
    """Stand-in for the chat model's follow-up rewrite (Improvement 4).

    Resolves a follow-up against the latest earlier student question, but
    leaves a question about another school unchanged, like the real model is
    instructed to.
    """
    latest = prompt.split("Latest question:\n", 1)[1].split("\n", 1)[0]
    if "University of" in latest:
        return latest
    earlier = [
        line[len("Student: "):]
        for line in prompt.split("Latest question:", 1)[0].splitlines()
        if line.startswith("Student: ")
    ]
    return f"{earlier[-1]} {latest}" if earlier else latest


def fake_query_rewriter(question, history, settings):
    return rewrite_follow_up_query(question, history, settings, generator=fake_rewrite_model)


_real_answer_question = answer.answer_question


def answer_question_with_fake_generator(*args, **kwargs):
    kwargs["generator"] = fake_generator
    kwargs.setdefault("query_rewriter", fake_query_rewriter)
    return _real_answer_question(*args, **kwargs)


answer.search_with_optional_reranking = fake_search
answer.answer_question = answer_question_with_fake_generator

SIMULATE_SAVE_FAILURE = "[simulate-save-failure]"
"""A question containing this marker makes the conversation save fail, so the
HTTP tests can check that a generated-but-unsaved answer is reported."""


def failing_append_exchange(*_args, **_kwargs):
    raise RuntimeError("simulated MySQL failure while saving the conversation")


if any(SIMULATE_SAVE_FAILURE in argument for argument in sys.argv):
    answer.append_exchange = failing_append_exchange

if __name__ == "__main__":
    sys.argv = sys.argv[1:]
    if Path(sys.argv[0]).name == "answer.py":
        answer.main()
    else:
        # Other endpoints (for example rag/admin.py for document deletion)
        # run their real script unchanged.
        import runpy  # noqa: PLC0415

        runpy.run_path(sys.argv[0], run_name="__main__")
