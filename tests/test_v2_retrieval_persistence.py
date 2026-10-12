
"""Integration test for V2 retrieved-context provenance persistence."""

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
    get_or_create_model_setting,
    save_grounded_response,
    upsert_document_and_chunks,
)
from query import mysql_keyword_search
from settings import load_settings


class V2RetrievalPersistenceTests(unittest.TestCase):

    def test_retrieved_table_provenance_is_saved(self):
        settings = load_settings()
        test_id = uuid4().hex
        source_path = f"test/v2-retrieval-{test_id}.pdf"
        unique_term = f"provenance {test_id}"
        table_text = (
            f"Program | Credits | Identifier\n"
            f"Cybersecurity | 34 | {unique_term}"
        )

        document_id = None
        response_id = None
        setting_id = None

        with database_connection(settings) as connection:
            try:
                # Create a temporary document, table element, and chunk.
                document_id, chunk_ids = upsert_document_and_chunks(
                    connection,
                    title="V2 Retrieval Persistence Test",
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
                            normalized_content=table_text,
                            extraction_method="pymupdf_table",
                        ),
                    ],
                    chunks=[
                        ChunkRecord(
                            chunk_index=0,
                            chunk_text=table_text,
                            chroma_id=f"test-{test_id}-chunk-0",
                            element_index=1,
                        ),
                    ],
                )

                self.assertEqual(len(chunk_ids), 1)

                # Ensure the temporary document is eligible for retrieval.
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE documents
                        SET status = 'ingested'
                        WHERE document_id = %s
                        """,
                        (document_id,),
                    )
                connection.commit()

                # Retrieve the temporary table using the actual MySQL
                # keyword retrieval implementation.
                results = mysql_keyword_search(
                    unique_term,
                    top_k=10,
                )

                matching = [
                    result
                    for result in results
                    if result.source_path == source_path
                    and result.content_type == "table"
                    and result.element_id is not None
                ]

                self.assertTrue(
                    matching,
                    "Temporary V2 table was not found in retrieval results.",
                )

                context = matching[0]

                # Create a dedicated test model setting.
                # No Gemini API call is made.
                setting_id = get_or_create_model_setting(
                    connection,
                    provider="gemini",
                    chat_model=f"v2-test-{test_id}",
                    embedding_model="test-embedding-model",
                    chunk_size=800,
                    chunk_overlap=100,
                    top_k=10,
                    temperature=0.0,
                    top_p=0.9,
                    retrieval_method="mysql_keyword",
                )

                response_id = save_grounded_response(
                    connection,
                    setting_id=setting_id,
                    question=f"V2 provenance test {test_id}",
                    answer="The Cybersecurity program requires 34 credits.",
                    latency_ms=0,
                    contexts=[context],
                    retrieval_method="mysql_keyword",
                )

                # Verify the retrieved evidence was persisted correctly.
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute(
                        """
                        SELECT
                            response_id,
                            document_id,
                            chunk_id,
                            element_id,
                            page_number_snapshot,
                            content_type_snapshot,
                            extraction_method_snapshot,
                            context_excerpt
                        FROM retrieved_contexts
                        WHERE response_id = %s
                        """,
                        (response_id,),
                    )
                    saved = cursor.fetchone()

                self.assertIsNotNone(saved)
                self.assertEqual(saved["document_id"], document_id)
                self.assertEqual(saved["chunk_id"], chunk_ids[0])
                self.assertEqual(saved["element_id"], context.element_id)
                self.assertEqual(saved["page_number_snapshot"], 2)
                self.assertEqual(saved["content_type_snapshot"], "table")
                self.assertEqual(
                    saved["extraction_method_snapshot"],
                    "pymupdf_table",
                )
                self.assertEqual(saved["context_excerpt"], table_text)

                print("\nV2 retrieval provenance persistence verified:")
                print(f"  Document ID: {saved['document_id']}")
                print(f"  Chunk ID: {saved['chunk_id']}")
                print(f"  Element ID: {saved['element_id']}")
                print(f"  Page number: {saved['page_number_snapshot']}")
                print(f"  Content type: {saved['content_type_snapshot']}")
                print(
                    f"  Extraction method: "
                    f"{saved['extraction_method_snapshot']}"
                )

            finally:
                # Delete only records created by this test.
                # Foreign-key cascades remove related retrieved contexts
                # when the response is deleted.
                if response_id is not None:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "DELETE FROM rag_responses WHERE response_id = %s",
                            (response_id,),
                        )
                    connection.commit()

                if document_id is not None:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "DELETE FROM documents WHERE document_id = %s",
                            (document_id,),
                        )
                    connection.commit()

                # Remove the temporary model setting.
                if setting_id is not None:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "DELETE FROM model_settings WHERE setting_id = %s",
                            (setting_id,),
                        )
                    connection.commit()


if __name__ == "__main__":
    unittest.main()
