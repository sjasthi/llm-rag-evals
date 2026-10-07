from __future__ import annotations

import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_SQL = (PROJECT_ROOT / "database" / "schema.sql").read_text(encoding="utf-8")
DATABASE_PY = (PROJECT_ROOT / "rag" / "database.py").read_text(encoding="utf-8")

# Columns that existing V1 databases gain through initialize_schema().
V2_UPGRADED_COLUMNS = {
    "document_chunks": ("element_id",),
    "retrieved_contexts": (
        "element_id",
        "page_number_snapshot",
        "content_type_snapshot",
        "extraction_method_snapshot",
    ),
    "model_settings": ("chunking_strategy", "chunking_configuration_json"),
}


def table_body(table_name: str) -> str:
    match = re.search(
        rf"CREATE TABLE IF NOT EXISTS {table_name} \((.*?)\n\);",
        SCHEMA_SQL,
        re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"schema.sql does not create {table_name}")
    return match.group(1)


class V2SchemaTests(unittest.TestCase):
    def test_new_v2_tables_are_declared(self) -> None:
        self.assertIn("element_index INT UNSIGNED NOT NULL", table_body("document_elements"))
        self.assertIn("status ENUM('active', 'archived')", table_body("conversations"))
        messages = table_body("conversation_messages")
        self.assertIn("role ENUM('user', 'assistant') NOT NULL", messages)
        self.assertIn("REFERENCES rag_responses (response_id)", messages)

    def test_referenced_tables_are_created_first(self) -> None:
        def position(table_name: str) -> int:
            return SCHEMA_SQL.index(f"CREATE TABLE IF NOT EXISTS {table_name} (")

        self.assertLess(position("documents"), position("document_elements"))
        self.assertLess(position("document_elements"), position("document_chunks"))
        self.assertLess(position("rag_responses"), position("conversation_messages"))
        self.assertLess(position("conversations"), position("conversation_messages"))

    def test_fresh_schema_and_upgrade_path_declare_the_same_columns(self) -> None:
        for table_name, columns in V2_UPGRADED_COLUMNS.items():
            body = table_body(table_name)
            for column_name in columns:
                with self.subTest(table=table_name, column=column_name):
                    self.assertRegex(body, rf"\n    {column_name} ")
                    self.assertIn(f'"{column_name}",', DATABASE_PY)

    def test_upgrade_path_adds_element_foreign_keys(self) -> None:
        for constraint_name in ("fk_document_chunks_element", "fk_retrieved_contexts_element"):
            with self.subTest(constraint=constraint_name):
                self.assertIn(f"CONSTRAINT {constraint_name}", SCHEMA_SQL)
                self.assertIn(f"ADD CONSTRAINT {constraint_name}", DATABASE_PY)


if __name__ == "__main__":
    unittest.main()
