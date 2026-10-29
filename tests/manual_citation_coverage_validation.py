
"""Manual live validation of partial Citation Coverage.

Runs one Gemini evaluation without modifying saved responses
or persisting evaluation results to MySQL.
"""

import json
import sys
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "rag"))

from advanced_evaluation import run_citation_coverage
from evaluation import EvaluationInput
from settings import load_settings


def main() -> None:
    settings = load_settings()

    item = EvaluationInput(
        response_id=0,
        question="How long does Registration Review take?",
        expected_answer="",
        actual_answer=(
            "Registration Review takes 2 business days [1]. "
            "Advising appointments are available online."
        ),
        expected_source=None,
        retrieved_sources=[],
        accepted_answers=[],
        required_facts=[],
        is_answerable=True,
        retrieved_evidence_by_rank={
            1: "Registration Review takes 2 business days."
        },
    )

    execution = run_citation_coverage(item, settings)

    print(json.dumps(
        {
            "result": asdict(execution.result),
            "usage": {
                "input_tokens": execution.input_tokens,
                "output_tokens": execution.output_tokens,
                "total_tokens": execution.total_tokens,
                "thinking_tokens": execution.thinking_tokens,
            },
        },
        indent=2,
        default=str,
    ))


if __name__ == "__main__":
    main()
