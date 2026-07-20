"""MySQL persistence for document and chunk ingestion."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import re
from typing import Any, Iterator, Sequence

import mysql.connector
from mysql.connector import MySQLConnection
from mysql.connector.errors import DatabaseError, ProgrammingError

from settings import PROJECT_ROOT, Settings


SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"
MIGRATIONS_PATH = PROJECT_ROOT / "database" / "migrations"
DATABASE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _schema_sql_for_database(sql: str, database_name: str) -> str:
    if not DATABASE_NAME_PATTERN.fullmatch(database_name):
        raise ValueError("DB_NAME may contain only letters, numbers, and underscores.")
    return sql.replace("llm_rag_evals", database_name)


def _execute_sql_script(connection: MySQLConnection, sql: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(sql)
        while cursor.nextset():
            pass


def _connection_arguments(settings: Settings, include_database: bool = True) -> dict[str, object]:
    arguments: dict[str, object] = {
        "host": settings.db_host,
        "port": settings.db_port,
        "user": settings.db_user,
        "password": settings.db_password,
        "charset": "utf8mb4",
        "use_unicode": True,
    }
    if include_database:
        arguments["database"] = settings.db_name
    return arguments


def initialize_schema(settings: Settings, schema_path: Path = SCHEMA_PATH) -> None:
    """Create the project database and tables from the versioned schema."""
    sql = _schema_sql_for_database(
        schema_path.read_text(encoding="utf-8"), settings.db_name
    )
    connection = mysql.connector.connect(**_connection_arguments(settings, include_database=False))
    try:
        _execute_sql_script(connection, sql)
        connection.commit()
    finally:
        connection.close()

    connection = mysql.connector.connect(**_connection_arguments(settings))
    try:
        # Migration 003 backfills these columns. Existing FP7 databases do not
        # gain columns from CREATE TABLE IF NOT EXISTS, so ensure the migration
        # prerequisites before ordered migration scripts execute.
        with connection.cursor() as cursor:
            fp8_run_columns = (
                ("dataset_id", "BIGINT UNSIGNED NULL AFTER setting_id"),
                ("baseline_run_id", "BIGINT UNSIGNED NULL AFTER dataset_id"),
                ("experiment_key", "VARCHAR(120) NULL AFTER run_name"),
                ("corpus_variant_key", "VARCHAR(120) NOT NULL DEFAULT 'full_current' AFTER experiment_key"),
                ("run_configuration_json", "JSON NULL AFTER corpus_variant_key"),
            )
            for column_name, definition in fp8_run_columns:
                cursor.execute(
                    """SELECT COUNT(*) FROM information_schema.columns
                       WHERE table_schema=%s AND table_name='evaluation_runs' AND column_name=%s""",
                    (settings.db_name, column_name),
                )
                row = cursor.fetchone()
                if not row or int(row[0]) == 0:
                    cursor.execute(
                        f"ALTER TABLE evaluation_runs ADD COLUMN {column_name} {definition}"
                    )
        connection.commit()

        if MIGRATIONS_PATH.is_dir():
            for migration_path in sorted(MIGRATIONS_PATH.glob("*.sql")):
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT 1 FROM schema_migrations WHERE migration_name = %s",
                        (migration_path.name,),
                    )
                    if cursor.fetchone():
                        continue
                migration_sql = _schema_sql_for_database(
                    migration_path.read_text(encoding="utf-8"), settings.db_name
                )
                _execute_sql_script(connection, migration_sql)
                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO schema_migrations (migration_name) VALUES (%s)",
                        (migration_path.name,),
                    )
                connection.commit()
        with connection.cursor() as cursor:
            fp5_columns = (
                ("chunk_size", "INT UNSIGNED NULL AFTER source_hash"),
                ("chunk_overlap", "INT UNSIGNED NULL AFTER chunk_size"),
                ("ingestion_error", "TEXT NULL AFTER chunk_overlap"),
            )
            for column_name, definition in fp5_columns:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND table_name = 'documents'
                      AND column_name = %s
                    """,
                    (settings.db_name, column_name),
                )
                row = cursor.fetchone()
                if not row or int(row[0]) == 0:
                    cursor.execute(
                        f"ALTER TABLE documents ADD COLUMN {column_name} {definition}"
                    )
            fp7_columns = (
                ("question_key", "CHAR(64) NULL AFTER question_id"),
                ("expected_evidence", "TEXT NULL AFTER expected_source"),
                ("accepted_answers", "JSON NULL AFTER expected_evidence"),
                ("required_facts", "JSON NULL AFTER accepted_answers"),
                ("difficulty", "ENUM('easy', 'medium', 'hard') NOT NULL DEFAULT 'medium' AFTER category"),
                ("is_answerable", "BOOLEAN NOT NULL DEFAULT TRUE AFTER difficulty"),
                ("reviewer_notes", "TEXT NULL AFTER is_answerable"),
                ("review_status", "ENUM('draft', 'reviewed', 'needs_revision') NOT NULL DEFAULT 'draft' AFTER reviewer_notes"),
            )
            for column_name, definition in fp7_columns:
                cursor.execute(
                    """SELECT COUNT(*) FROM information_schema.columns
                       WHERE table_schema=%s AND table_name='evaluation_questions' AND column_name=%s""",
                    (settings.db_name, column_name),
                )
                row = cursor.fetchone()
                if not row or int(row[0]) == 0:
                    cursor.execute(f"ALTER TABLE evaluation_questions ADD COLUMN {column_name} {definition}")
            cursor.execute(
                """SELECT COUNT(*) FROM information_schema.columns
                   WHERE table_schema=%s AND table_name='evaluator_results'
                     AND column_name='updated_at'""",
                (settings.db_name,),
            )
            row = cursor.fetchone()
            if not row or int(row[0]) == 0:
                cursor.execute(
                    "ALTER TABLE evaluator_results ADD COLUMN updated_at TIMESTAMP NOT NULL "
                    "DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at"
                )
            cursor.execute(
                """SELECT COUNT(*) FROM information_schema.statistics
                   WHERE table_schema=%s AND table_name='evaluation_questions'
                     AND index_name='uq_evaluation_questions_key'""",
                (settings.db_name,),
            )
            row = cursor.fetchone()
            if not row or int(row[0]) == 0:
                cursor.execute(
                    "ALTER TABLE evaluation_questions ADD UNIQUE KEY uq_evaluation_questions_key (question_key)"
                )
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = 'documents'
                  AND column_name = 'original_filename'
                """,
                (settings.db_name,),
            )
            row = cursor.fetchone()
            if not row or int(row[0]) == 0:
                cursor.execute(
                    "ALTER TABLE documents ADD COLUMN original_filename VARCHAR(255) NULL "
                    "AFTER source_type"
                )
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.statistics
                WHERE table_schema = %s
                  AND table_name = 'document_chunks'
                  AND index_name = 'uq_document_chunks_chroma_id'
                """,
                (settings.db_name,),
            )
            row = cursor.fetchone()
            if not row or int(row[0]) == 0:
                cursor.execute(
                    "ALTER TABLE document_chunks "
                    "ADD UNIQUE KEY uq_document_chunks_chroma_id (chroma_id)"
                )
            cursor.execute(
                """SELECT COUNT(*) FROM information_schema.statistics
                   WHERE table_schema=%s AND table_name='document_chunks'
                     AND index_name='ft_document_chunks_text'""",
                (settings.db_name,),
            )
            row = cursor.fetchone()
            if not row or int(row[0]) == 0:
                cursor.execute(
                    "ALTER TABLE document_chunks ADD FULLTEXT KEY ft_document_chunks_text (chunk_text)"
                )

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = 'rag_responses'
                  AND column_name = 'setting_id'
                """,
                (settings.db_name,),
            )
            row = cursor.fetchone()
            if not row or int(row[0]) == 0:
                cursor.execute(
                    "ALTER TABLE rag_responses ADD COLUMN setting_id BIGINT UNSIGNED NULL "
                    "AFTER run_id"
                )

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.table_constraints
                WHERE constraint_schema = %s
                  AND table_name = 'rag_responses'
                  AND constraint_name = 'fk_rag_responses_setting'
                """,
                (settings.db_name,),
            )
            row = cursor.fetchone()
            if not row or int(row[0]) == 0:
                cursor.execute(
                    """
                    ALTER TABLE rag_responses
                    ADD CONSTRAINT fk_rag_responses_setting
                    FOREIGN KEY (setting_id) REFERENCES model_settings (setting_id)
                    ON DELETE SET NULL
                    """
                )

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = 'model_settings'
                  AND column_name = 'top_p'
                """,
                (settings.db_name,),
            )
            row = cursor.fetchone()
            if not row or int(row[0]) == 0:
                cursor.execute(
                    "ALTER TABLE model_settings "
                    "ADD COLUMN top_p DECIMAL(3,2) NOT NULL DEFAULT 1.00 AFTER temperature"
                )

            fp8_constraints = (
                (
                    "fk_evaluation_runs_dataset",
                    "ALTER TABLE evaluation_runs ADD CONSTRAINT fk_evaluation_runs_dataset "
                    "FOREIGN KEY (dataset_id) REFERENCES evaluation_datasets (dataset_id) ON DELETE SET NULL",
                ),
                (
                    "fk_evaluation_runs_baseline",
                    "ALTER TABLE evaluation_runs ADD CONSTRAINT fk_evaluation_runs_baseline "
                    "FOREIGN KEY (baseline_run_id) REFERENCES evaluation_runs (run_id) ON DELETE SET NULL",
                ),
            )
            for constraint_name, statement in fp8_constraints:
                cursor.execute(
                    """SELECT COUNT(*) FROM information_schema.table_constraints
                       WHERE constraint_schema=%s AND table_name='evaluation_runs'
                         AND constraint_name=%s""",
                    (settings.db_name, constraint_name),
                )
                row = cursor.fetchone()
                if not row or int(row[0]) == 0:
                    cursor.execute(statement)
        connection.commit()
    finally:
        connection.close()


@contextmanager
def database_connection(settings: Settings) -> Iterator[MySQLConnection]:
    try:
        connection = mysql.connector.connect(**_connection_arguments(settings))
    except ProgrammingError as error:
        if error.errno == 1049:
            raise RuntimeError(
                f"Database {settings.db_name!r} does not exist. Run ingest.py with --init-schema."
            ) from error
        raise
    except DatabaseError as error:
        raise RuntimeError(
            f"Could not connect to MySQL at {settings.db_host}:{settings.db_port}: {error}"
        ) from error

    try:
        yield connection
    finally:
        connection.close()


def upsert_document_and_chunks(
    connection: MySQLConnection,
    *,
    title: str,
    category: str,
    source_path: str,
    source_type: str,
    original_filename: str,
    source_hash: str,
    chunk_size: int,
    chunk_overlap: int,
    chunks: Sequence[tuple[int, str, str]],
) -> tuple[int, list[int]]:
    """Replace one document's chunk rows in a single MySQL transaction."""
    try:
        connection.start_transaction()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO documents (
                    title, category, source_path, source_type, original_filename, status, source_hash,
                    chunk_size, chunk_overlap, ingestion_error
                )
                VALUES (%s, %s, %s, %s, %s, 'pending', %s, %s, %s, NULL)
                ON DUPLICATE KEY UPDATE
                    document_id = LAST_INSERT_ID(document_id),
                    title = VALUES(title),
                    category = VALUES(category),
                    source_type = VALUES(source_type),
                    original_filename = VALUES(original_filename),
                    status = 'pending',
                    source_hash = VALUES(source_hash),
                    chunk_size = VALUES(chunk_size),
                    chunk_overlap = VALUES(chunk_overlap),
                    ingestion_error = NULL
                """,
                (
                    title, category, source_path, source_type, original_filename,
                    source_hash, chunk_size, chunk_overlap,
                ),
            )
            document_id = int(cursor.lastrowid)

            cursor.execute("DELETE FROM document_chunks WHERE document_id = %s", (document_id,))

            chunk_ids: list[int] = []
            for chunk_index, chunk_text, chroma_id in chunks:
                cursor.execute(
                    """
                    INSERT INTO document_chunks (
                        document_id, chunk_index, chunk_text, token_estimate, chroma_id
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        document_id,
                        chunk_index,
                        chunk_text,
                        max(1, (len(chunk_text) + 3) // 4),
                        chroma_id,
                    ),
                )
                chunk_ids.append(int(cursor.lastrowid))

        connection.commit()
        return document_id, chunk_ids
    except Exception:
        connection.rollback()
        raise


def mark_document_ingested(connection: MySQLConnection, document_id: int) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE documents
            SET status = 'ingested', imported_at = CURRENT_TIMESTAMP, ingestion_error = NULL
            WHERE document_id = %s
            """,
            (document_id,),
        )
    connection.commit()


def mark_document_failed(connection: MySQLConnection, document_id: int, error: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE documents
            SET status = 'failed', ingestion_error = %s
            WHERE document_id = %s
            """,
            (error[:65535], document_id),
        )
    connection.commit()


def record_document_failure(
    connection: MySQLConnection,
    *,
    title: str,
    category: str,
    source_path: str,
    source_type: str,
    original_filename: str,
    source_hash: str,
    error: str,
) -> None:
    """Record a parser failure without discarding chunks from an earlier good version."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO documents (
                title, category, source_path, source_type, original_filename,
                status, source_hash, ingestion_error
            ) VALUES (%s, %s, %s, %s, %s, 'failed', %s, %s)
            ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                category = VALUES(category),
                source_type = VALUES(source_type),
                original_filename = VALUES(original_filename),
                status = 'failed',
                source_hash = VALUES(source_hash),
                ingestion_error = VALUES(ingestion_error)
            """,
            (
                title,
                category,
                source_path,
                source_type,
                original_filename,
                source_hash,
                error[:65535],
            ),
        )
    connection.commit()


def database_counts(connection: MySQLConnection) -> dict[str, int]:
    counts: dict[str, int] = {}
    with connection.cursor() as cursor:
        for table in ("documents", "document_chunks"):
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row = cursor.fetchone()
            counts[table] = int(row[0]) if row else 0
    return counts


def delete_uploaded_document(connection: MySQLConnection, source_path: str) -> int:
    """Delete one browser-managed document and its cascading chunk rows."""
    if not source_path.startswith("storage/uploads/"):
        raise ValueError("Only browser-uploaded documents can be deleted.")

    try:
        connection.start_transaction()
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM documents WHERE source_path = %s",
                (source_path,),
            )
            deleted = int(cursor.rowcount)
        if deleted != 1:
            raise ValueError("Uploaded document was not found.")
        connection.commit()
        return deleted
    except Exception:
        connection.rollback()
        raise


def get_or_create_model_setting(
    connection: MySQLConnection,
    *,
    provider: str,
    chat_model: str,
    embedding_model: str,
    chunk_size: int,
    chunk_overlap: int,
    top_k: int,
    temperature: float,
    top_p: float,
    retrieval_method: str = "chroma_vector",
) -> int:
    if retrieval_method not in {"chroma_vector", "mysql_keyword"}:
        raise ValueError(f"Unsupported retrieval method {retrieval_method!r}")
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT setting_id
            FROM model_settings
            WHERE retrieval_method = %s
              AND llm_provider = %s
              AND chat_model = %s
              AND embedding_model = %s
              AND chunk_size = %s
              AND chunk_overlap = %s
              AND top_k = %s
              AND temperature = %s
              AND top_p = %s
            ORDER BY setting_id
            LIMIT 1
            """,
            (
                retrieval_method,
                provider,
                chat_model,
                embedding_model,
                chunk_size,
                chunk_overlap,
                top_k,
                temperature,
                top_p,
            ),
        )
        row = cursor.fetchone()
        if row:
            setting_id = int(row[0])
            connection.commit()
            return setting_id

        cursor.execute(
            """
            INSERT INTO model_settings (
                setting_name, retrieval_method, llm_provider, chat_model,
                embedding_model, chunk_size, chunk_overlap, top_k, temperature, top_p
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                f"{provider} {chat_model} grounded CLI",
                retrieval_method,
                provider,
                chat_model,
                embedding_model,
                chunk_size,
                chunk_overlap,
                top_k,
                temperature,
                top_p,
            ),
        )
        setting_id = int(cursor.lastrowid)
    connection.commit()
    return setting_id


def save_grounded_response(
    connection: MySQLConnection,
    *,
    setting_id: int,
    question: str,
    answer: str,
    latency_ms: int,
    contexts: Sequence[Any],
    question_id: int | None = None,
    run_id: int | None = None,
    retrieval_method: str = "chroma_vector",
) -> int:
    """Store one CLI answer and the exact retrieved contexts used to produce it."""
    try:
        connection.start_transaction()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO rag_responses (
                    run_id, setting_id, question_id, question_text, answer_text, retrieval_method, latency_ms
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (run_id, setting_id, question_id, question, answer, retrieval_method, latency_ms),
            )
            response_id = int(cursor.lastrowid)

            for context in contexts:
                distance = context.distance
                similarity = None if distance is None else 1.0 / (1.0 + max(0.0, distance))
                cursor.execute(
                    """
                    INSERT INTO retrieved_contexts (
                        response_id, document_id, chunk_id, rank_position,
                        similarity_score, context_excerpt
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        response_id,
                        context.document_id,
                        context.chunk_id,
                        context.rank,
                        similarity,
                        context.text,
                    ),
                )
        connection.commit()
        return response_id
    except Exception:
        connection.rollback()
        raise
