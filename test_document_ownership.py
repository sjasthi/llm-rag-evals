"""Improvement 5: retrieval only uses the shared library plus the user's uploads.

Runs against the configured MySQL database (CI provides one). ChromaDB is
replaced by a fake collection that records the filter it receives, so no
embedding model is needed.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "rag"))

from database import database_connection  # noqa: E402
from query import (  # noqa: E402
    ALL_DOCUMENTS,
    DocumentScope,
    allowed_source_paths,
    mysql_keyword_search,
    semantic_search,
)
from settings import load_settings  # noqa: E402


def database_available() -> bool:
    try:
        with database_connection(load_settings()) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id FROM documents LIMIT 1")
                cursor.fetchall()
        return True
    except Exception:
        return False


class FakeCollection:
    def __init__(self) -> None:
        self.where = "not called"

    def count(self) -> int:
        return 100

    def query(self, **kwargs):
        self.where = kwargs.get("where")
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}


@unittest.skipUnless(database_available(), "MySQL with the current schema is required")
class DocumentScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = load_settings()
        self.marker = uuid4().hex[:12]
        self.word = f"zebrafact{self.marker}"
        with database_connection(self.settings) as connection:
            with connection.cursor() as cursor:
                self.users = []
                for name in ("alex", "blair"):
                    cursor.execute(
                        "INSERT INTO users (username, display_name, password_hash) VALUES (%s, %s, 'x')",
                        (f"{name}_{self.marker}", name),
                    )
                    self.users.append(int(cursor.lastrowid))
                self.alex, self.blair = self.users
                self.paths = {}
                for label, owner in (("shared", None), ("alex", self.alex), ("blair", self.blair)):
                    path = f"test/{label}-{self.marker}.txt"
                    cursor.execute(
                        "INSERT INTO documents (title, category, source_path, user_id, status) "
                        "VALUES (%s, 'testing', %s, %s, 'ingested')",
                        (label, path, owner),
                    )
                    document_id = int(cursor.lastrowid)
                    cursor.execute(
                        "INSERT INTO document_chunks (document_id, chunk_index, chunk_text) VALUES (%s, 0, %s)",
                        (document_id, f"{label} document mentions {self.word} for retrieval"),
                    )
                    self.paths[label] = path
            connection.commit()

    def tearDown(self) -> None:
        with database_connection(self.settings) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM documents WHERE source_path LIKE %s", (f"%{self.marker}%",))
                cursor.execute("DELETE FROM users WHERE username LIKE %s", (f"%{self.marker}",))
            connection.commit()

    def found_paths(self, scope: DocumentScope) -> set[str]:
        results = mysql_keyword_search(self.word, 10, ["testing"], scope)
        return {result.source_path for result in results}

    def test_keyword_search_uses_shared_library_and_own_uploads_only(self) -> None:
        self.assertEqual(
            {self.paths["shared"], self.paths["alex"]}, self.found_paths(DocumentScope(user_id=self.alex))
        )
        self.assertEqual(
            {self.paths["shared"], self.paths["blair"]}, self.found_paths(DocumentScope(user_id=self.blair))
        )
        self.assertEqual({self.paths["shared"]}, self.found_paths(DocumentScope(shared_only=True)))
        self.assertEqual(set(self.paths.values()), self.found_paths(ALL_DOCUMENTS))

    def test_vector_search_filters_chroma_with_an_allow_list_from_mysql(self) -> None:
        allowed = allowed_source_paths(DocumentScope(user_id=self.alex))
        self.assertIn(self.paths["shared"], allowed)
        self.assertIn(self.paths["alex"], allowed)
        self.assertNotIn(self.paths["blair"], allowed)
        self.assertIsNone(allowed_source_paths(ALL_DOCUMENTS))

        collection = FakeCollection()
        with patch("vector_store.get_collection", return_value=collection):
            semantic_search("question", 3, ["testing"], DocumentScope(user_id=self.alex))
        category_filter, path_filter = collection.where["$and"]
        self.assertEqual({"category": "testing"}, category_filter)
        self.assertIn(self.paths["alex"], path_filter["source_path"]["$in"])
        self.assertNotIn(self.paths["blair"], path_filter["source_path"]["$in"])

        collection = FakeCollection()
        with patch("vector_store.get_collection", return_value=collection):
            semantic_search("question", 3, None, ALL_DOCUMENTS)
        self.assertIsNone(collection.where, "trusted CLI search is unchanged")


if __name__ == "__main__":
    unittest.main()
