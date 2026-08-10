"""Provider-free smoke checks for a seeded MySQL/Chroma/PHP stack.

The script intentionally exercises only read paths plus Chat source preview.
It never requests answer generation or model-backed evaluation.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        f"{base_url.rstrip('/')}/{path.lstrip('/')}",
        data=body,
        headers=headers,
        method=method,
    )
    with urlopen(request, timeout=timeout) as response:
        result = json.load(response)
    if not isinstance(result, dict):
        raise AssertionError(f"{path} did not return a JSON object")
    return result


def wait_until_ready(base_url: str, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            health = request_json(base_url, "api/health.php", timeout=2.0)
            if health.get("ok") and health.get("data", {}).get("status") == "ready":
                return health
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            last_error = error
        time.sleep(0.25)
    raise TimeoutError(f"Application did not become ready: {last_error}")


def verify_stack(base_url: str) -> dict[str, Any]:
    wait_until_ready(base_url, 30.0)

    documents_payload = request_json(base_url, "api/documents.php")
    documents = documents_payload.get("data")
    if not documents_payload.get("ok") or not isinstance(documents, list):
        raise AssertionError("Documents endpoint did not return the indexed library")
    chunk_count = sum(int(document.get("chunk_count") or 0) for document in documents)
    if len(documents) != 27 or chunk_count != 77:
        raise AssertionError(
            f"Expected the bundled 27-document/77-chunk corpus, got "
            f"{len(documents)} documents/{chunk_count} chunks"
        )

    evaluation_payload = request_json(base_url, "api/evaluations.php")
    evaluation_data = evaluation_payload.get("data")
    if not evaluation_payload.get("ok") or not isinstance(evaluation_data, dict):
        raise AssertionError("Evaluation endpoint did not return seeded data")
    questions = evaluation_data.get("questions")
    evaluators = evaluation_data.get("evaluators")
    if not isinstance(questions, list) or len(questions) != 50:
        raise AssertionError("Expected 50 reviewed Gold Standard questions")
    if not isinstance(evaluators, list) or len(evaluators) != 13:
        raise AssertionError("Expected 13 active evaluator definitions")

    preview_payload = request_json(
        base_url,
        "api/ask.php",
        method="POST",
        payload={
            "action": "preview",
            "question": "When does Fall 2026 registration begin?",
            "retrieval_method": "chroma_vector",
            "top_k": 3,
            "temperature": 0.0,
            "top_p": 0.9,
        },
        timeout=90.0,
    )
    preview_data = preview_payload.get("data")
    sources = preview_data.get("sources") if isinstance(preview_data, dict) else None
    if not preview_payload.get("ok") or not isinstance(sources, list) or len(sources) != 3:
        raise AssertionError("Provider-free Chat preview did not return three sources")
    first_source = str(sources[0].get("source_path") or sources[0].get("source") or "")
    if "fall_2026.txt" not in first_source:
        raise AssertionError(
            f"Expected the Fall 2026 calendar at rank one, got {first_source!r}"
        )

    return {
        "status": "ok",
        "documents": len(documents),
        "chunks": chunk_count,
        "questions": len(questions),
        "evaluators": len(evaluators),
        "preview_sources": len(sources),
        "rank_one_source": first_source,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    try:
        result = verify_stack(args.base_url)
    except Exception as error:  # noqa: BLE001 - CLI should report every failure clearly.
        print(f"Provider-free stack verification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
