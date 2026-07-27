"""Capture reproducibility metadata for controlled RAG runs."""

from __future__ import annotations

import hashlib
from importlib import metadata
import platform
import subprocess
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRACKED_DISTRIBUTIONS = (
    "chromadb",
    "google-genai",
    "mysql-connector-python",
    "sentence-transformers",
    "bert-score",
    "ragas",
    "langchain-community",
)


def _source_files() -> list[Path]:
    files = sorted((PROJECT_ROOT / "rag").glob("*.py"))
    files.append(PROJECT_ROOT / "database" / "schema.sql")
    files.extend(sorted((PROJECT_ROOT / "database" / "migrations").glob("*.sql")))
    return [path for path in files if path.is_file()]


def source_tree_hash() -> str:
    """Hash executable RAG and schema sources, including uncommitted edits."""
    digest = hashlib.sha256()
    for path in _source_files():
        digest.update(path.relative_to(PROJECT_ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _git_output(*args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=PROJECT_ROOT,
            capture_output=True,
            check=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = completed.stdout.strip()
    return value or None


def code_provenance() -> dict[str, Any]:
    """Return a Git label and content hash for the exact code used by a run."""
    commit = _git_output("rev-parse", "HEAD")
    status = _git_output("status", "--porcelain", "--untracked-files=normal")
    tree_hash = source_tree_hash()
    dependencies: dict[str, str | None] = {}
    for distribution in TRACKED_DISTRIBUTIONS:
        try:
            dependencies[distribution] = metadata.version(distribution)
        except metadata.PackageNotFoundError:
            dependencies[distribution] = None
    return {
        "git_commit": commit,
        "git_dirty": bool(status) if status is not None else None,
        "source_tree_sha256": tree_hash,
        "version_label": f"{commit or 'git-unavailable'}+source-{tree_hash[:12]}",
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": dependencies,
    }
