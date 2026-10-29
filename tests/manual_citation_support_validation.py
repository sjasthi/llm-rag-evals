
"""Manual live validation of Citation Support with synthetic cases.

This script makes paid Gemini API calls when executed.
It does not modify the database.
"""

import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag"))

from advanced_evaluation import run_citation_support
from evaluation import EvaluationInput
from settings import load_settings


CASES = [
    {
        "name": "contradicted",
        "answer": "Registration Review takes 5 business days [1].",
        "evidence": "Registration Review takes 2 business days.",
        "expected_score": 0.0,
        "expected_verdict": "contradicted",
    },
    {
        "name": "insufficient_evidence",
        "answer": "Registration Review takes 5 business days [1].",
        "evidence": "Contact the Advising office for assistance.",
        "expected_score": 0.0,
        "expected_verdict": "insufficient_evidence",
    },
    {
        "name": "partially_supported",
        "answer": (
            "Registration Review takes 2 business days, "
            "and the Registrar is responsible [1]."
        ),
        "evidence": (
            "Registration Review takes 2 business days. "
            "Responsible office: Advising."
        ),
        "expected_score": 0.5,
        "expected_verdict": "mixed",
    },
]

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Manually validate Citation Support with synthetic cases."
    )
    parser.add_argument(
        "--case",
        choices=[case["name"] for case in CASES],
        required=True,
        help="Select exactly one validation scenario.",
    )
    parser.add_argument(
        "--allow-paid",
        action="store_true",
        help="Explicitly authorize one Gemini evaluation.",
    )
    parser.add_argument(
        "--max-estimated-cost",
        type=float,
        default=0.01,
        help="Maximum permitted preflight estimate in USD.",
    )

    args = parser.parse_args()

    case = next(case for case in CASES if case["name"] == args.case)
    settings = load_settings()

    # Conservative planning estimate for one Citation Support call.
    estimated_input_tokens = 2000
    estimated_output_tokens = 1000

    if (
        settings.evaluator_input_cost_per_million <= 0
        or settings.evaluator_output_cost_per_million <= 0
    ):
        raise SystemExit(
            "Evaluator pricing is missing. Configure pricing before execution."
        )

    estimated_cost = (
        estimated_input_tokens * settings.evaluator_input_cost_per_million
        + estimated_output_tokens * settings.evaluator_output_cost_per_million
    ) / 1_000_000

    if estimated_cost > args.max_estimated_cost:
        raise SystemExit(
            f"Estimated cost ${estimated_cost:.6f} exceeds "
            f"limit ${args.max_estimated_cost:.6f}."
        )

    print(f"Selected case: {case['name']}")
    print(f"Estimated cost: ${estimated_cost:.6f}")
    print(f"Maximum permitted estimate: ${args.max_estimated_cost:.6f}")

    if not args.allow_paid:
        raise SystemExit(
            "No Gemini call made. "
            "Pass --allow-paid to authorize this single case."
        )

    item = EvaluationInput(
        response_id=-1,
        question="How long does Registration Review take, and who handles it?",
        expected_answer="",
        actual_answer=case["answer"],
        expected_source=None,
        retrieved_sources=["synthetic_registration_table.txt"],
        accepted_answers=[],
        required_facts=[],
        is_answerable=True,
        retrieved_contexts=[case["evidence"]],
        retrieved_source_ranks=[1],
        retrieved_evidence_by_rank={1: case["evidence"]},
    )

    execution = run_citation_support(item, settings)
    result = execution.result

    print(json.dumps({
        "case": case["name"],
        "expected_score": case["expected_score"],
        "actual_score": result.normalized_score,
        "expected_verdict": case["expected_verdict"],
        "claims": result.details.get("claims", []),
        "status": result.status,
        "estimated_cost": result.estimated_cost,
        "input_tokens": execution.input_tokens,
        "output_tokens": execution.output_tokens,
    }, indent=2))


if __name__ == "__main__":
    main()
