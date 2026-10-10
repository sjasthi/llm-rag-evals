
"""Integration test for V2 document-element persistence."""

import sys
import unittest
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "rag"))

from database import (
    ChunkRecord,
    ElementRecord,
    database_connection,
    upsert_document_and_chunks,
)
from settings import load_settings


class V2ElementPersistenceTests(unittest.TestCase):

    def test_element_to_chunk_relationship(self):
        settings = load_settings()
        test_id = uuid4().hex
        source_path = f"test/v2-element-persistence-{test_id}.pdf"
        document_id = None

        with database_connection(settings) as connection:
            try:
                document_id, chunk_ids = upsert_document_and_chunks(
                    connection,
                    title="V2 Element Persistence Test",
                    category="test",
                    source_path=source_path,
                    source_type="pdf",
                    original_filename="test.pdf",
                    source_hash=test_id,
                    chunk_size=800,
                    chunk_overlap=100,
                    elements=[
                        ElementRecord(
                            element_index=1,
                            page_number=2,
                            content_type="table",
                            normalized_content=(
                                "Program | GPA | Credits\n"
                                "Data Science | 3.2 | 33\n"
                                "Software Engineering | 2.9 | 39"
                            ),
                            extraction_method="pymupdf_table",
                        ),
                    ],
                    chunks=[
                        ChunkRecord(
                            chunk_index=0,
                            chunk_text="Program | GPA | Credits",
                            chroma_id=f"test-{test_id}-chunk-0",
                            element_index=1,
                        ),
                        ChunkRecord(
                            chunk_index=1,
                            chunk_text="Data Science | 3.2 | 33",
                            chroma_id=f"test-{test_id}-chunk-1",
                            element_index=1,
                        ),
                    ],
                )

                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            e.element_id,
                            e.page_number,
                            e.content_type,
                            e.normalized_content,
                            c.chunk_id,
                            c.element_id
                        FROM document_elements AS e
                        JOIN document_chunks AS c
                            ON c.element_id = e.element_id
                        WHERE e.document_id = %s
                        ORDER BY c.chunk_index
                        """,
                        (document_id,),
                    )
                    rows = cursor.fetchall()

                self.assertEqual(len(rows), 2)
                self.assertEqual(len(chunk_ids), 2)
                self.assertEqual(rows[0][0], rows[1][0])
                self.assertEqual(rows[0][0], rows[0][5])
                self.assertEqual(rows[1][0], rows[1][5])
                self.assertEqual(rows[0][1], 2)
                self.assertEqual(rows[0][2], "table")
                self.assertIn("Software Engineering", rows[0][3])

                print("\nV2 persistence verified:")
                print("  Complete elements stored: 1")
                print("  Linked retrieval chunks: 2")
                print("  Both chunks reference the same element_id.")

            finally:
                if document_id is not None:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "DELETE FROM documents WHERE document_id = %s",
                            (document_id,),
                        )
                    connection.commit()


if __name__ == "__main__":
    unittest.main()
