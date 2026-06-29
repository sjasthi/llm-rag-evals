"""Environment-backed settings shared by the FP5 RAG helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"


def _project_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def _positive_int(name: str, default: int) -> int:
    raw_value = _env_value(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer, received {raw_value!r}") from error

    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")

    return value


def _env_value(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else default


def _float_between_zero_and_one(name: str, default: float) -> float:
    raw_value = _env_value(name, str(default))
    try:
        value = float(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} must be a number, received {raw_value!r}") from error
    if value < 0.0 or value > 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0")
    return value


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    chroma_path: Path
    chroma_collection: str
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    llm_provider: str
    llm_api_key: str
    llm_chat_model: str
    llm_temperature: float
    llm_top_p: float
    retrieval_top_k: int


def load_settings() -> Settings:
    load_dotenv(ENV_PATH, override=False)

    chunk_size = _positive_int("CHUNK_SIZE", 800)
    chunk_overlap = int(_env_value("CHUNK_OVERLAP", "100"))
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("CHUNK_OVERLAP must be zero or less than CHUNK_SIZE")

    return Settings(
        db_host=_env_value("DB_HOST", "127.0.0.1"),
        db_port=_positive_int("DB_PORT", 3306),
        db_name=_env_value("DB_NAME", "llm_rag_evals"),
        db_user=_env_value("DB_USER", "root"),
        db_password=_env_value("DB_PASSWORD"),
        chroma_path=_project_path(_env_value("CHROMA_PATH", "rag/chroma")),
        chroma_collection=_env_value("CHROMA_COLLECTION", "metrostate_documents"),
        embedding_model=_env_value("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        llm_provider=_env_value("LLM_PROVIDER", "gemini").lower(),
        llm_api_key=_env_value("GEMINI_API_KEY", _env_value("LLM_API_KEY")),
        llm_chat_model=_env_value("LLM_CHAT_MODEL", "gemini-2.5-flash"),
        llm_temperature=_float_between_zero_and_one("LLM_TEMPERATURE", 0.0),
        llm_top_p=_float_between_zero_and_one("LLM_TOP_P", 0.9),
        retrieval_top_k=_positive_int("RETRIEVAL_TOP_K", 3),
    )
