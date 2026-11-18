"""Provider-free smoke checks for a seeded MySQL/Chroma/PHP stack.

The script intentionally exercises only read paths plus Chat source preview.
It never requests answer generation or model-backed evaluation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
import time
from typing import Any
from urllib.error import HTTPError, URLError
from http.cookiejar import CookieJar
from urllib.request import (
    HTTPCookieProcessor,
    Request,
    build_opener,
    urlopen,
)
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from rag.evaluator_catalog import ALL_DEFINITIONS

def request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 30.0,
    opener: Any = None,
    csrf_token: str | None = None,
) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    if csrf_token:
        headers["X-CSRF-Token"] = csrf_token

    request = Request(
        f"{base_url.rstrip('/')}/{path.lstrip('/')}",
        data=body,
        headers=headers,
        method=method,
    )

    if opener is None:
        response = urlopen(request, timeout=timeout)
    else:
        response = opener.open(request, timeout=timeout)

    with response:
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

    # Authentication is required for protected application APIs.
    # First verify that anonymous document access is rejected.
    try:
        request_json(base_url, "api/documents.php")
    except HTTPError as error:
        if error.code != 401:
            raise AssertionError(
                f"Anonymous documents request returned {error.code}, expected 401"
            ) from error
        error.close()
    else:
        raise AssertionError(
            "Anonymous documents request succeeded unexpectedly"
        )

    # Use a cookie-preserving browser session for the remaining checks.
    browser = build_opener(HTTPCookieProcessor(CookieJar()))

    session = request_json(
        base_url,
        "api/auth.php",
        opener=browser,
    )
    csrf_token = session.get("csrf_token")
    if not session.get("ok") or not isinstance(csrf_token, str) or not csrf_token:
        raise AssertionError("Authentication session did not return a CSRF token")

    # Unique CI-only account; the GitHub Actions fixture is disposable.
    username = "ci_smoke_" + uuid4().hex[:16]
    password = "Smoke-Test-" + uuid4().hex + "9a!"

    registration = request_json(
        base_url,
        "api/auth.php",
        method="POST",
        payload={
            "action": "register",
            "username": username,
            "password": password,
            "display_name": "CI Smoke Test",
        },
        opener=browser,
        csrf_token=csrf_token,
    )

    if not registration.get("ok"):
        raise AssertionError("Smoke-test account registration failed")

    user = registration.get("user")
    if not isinstance(user, dict) or user.get("username") != username:
        raise AssertionError("Smoke-test account was not authenticated")

    # Session regeneration during registration may rotate the CSRF token.
    csrf_token = registration.get("csrf_token")
    if not isinstance(csrf_token, str) or not csrf_token:
        raise AssertionError("Authenticated session did not return a CSRF token")

    documents_payload = request_json(
        base_url,
        "api/documents.php",
        opener=browser,
    )
    documents = documents_payload.get("data")
    if not documents_payload.get("ok") or not isinstance(documents, list):
        raise AssertionError("Documents endpoint did not return the indexed library")
    chunk_count = sum(int(document.get("chunk_count") or 0) for document in documents)
    if len(documents) != 27 or chunk_count != 77:
        raise AssertionError(
            f"Expected the bundled 27-document/77-chunk corpus, got "
            f"{len(documents)} documents/{chunk_count} chunks"
        )

    evaluation_payload = request_json(
        base_url,
        "api/evaluations.php",
        opener=browser,
    )
    evaluation_data = evaluation_payload.get("data")
    if not evaluation_payload.get("ok") or not isinstance(evaluation_data, dict):
        raise AssertionError("Evaluation endpoint did not return seeded data")
    questions = evaluation_data.get("questions")
    evaluators = evaluation_data.get("evaluators")
    if not isinstance(questions, list) or len(questions) != 50:
        raise AssertionError("Expected 50 reviewed Gold Standard questions")

    if not isinstance(evaluators, list):
        raise AssertionError("Expected a list of active evaluator definitions")

    expected_keys = {definition["key"] for definition in ALL_DEFINITIONS}
    actual_keys = {evaluator["evaluator_key"] for evaluator in evaluators}

    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        unexpected = sorted(actual_keys - expected_keys)

        raise AssertionError(
            f"Evaluator definitions mismatch: "
            f"missing={missing}, unexpected={unexpected}"
        )

    preview_payload = request_json(
        base_url,
        "api/ask.php",
        method="POST",
        opener=browser,
        csrf_token=csrf_token,
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
