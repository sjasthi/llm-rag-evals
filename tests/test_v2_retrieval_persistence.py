
"""Integration test for V2 retrieved-context provenance persistence."""

import sys
import unittest
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "rag"))

from database import database_connection, save_grounded_response
from query import mysql_keyword_search
from settings import load_settings


class V2RetrievalPersistenceTests(unittest.TestCase):

    def test_retrieved_table_provenance_is_saved(self):
        settings = load_settings()
        test_marker = f"V2 provenance test {uuid4().hex}"
        response_id = None

        # Retrieve the table using the actual application retrieval code.
        results = mysql_keyword_search(
            "How many credits are required for the Cybersecurity graduate program?",
            top_k=10,
        )

        # Select the V2-ingested table, not the older uploaded copy.
        matching = [
            result for result in results
            if result.source_path.endswith("V2_Table_Extraction_Test.pdf")
            and result.content_type == "table"
            and result.element_id is not None
        ]

        self.assertTrue(matching, "V2 table was not found in retrieval results.")
        context = matching[0]

        with database_connection(settings) as connection:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT setting_id FROM model_settings ORDER BY setting_id LIMIT 1"
                    )
                    setting_row = cursor.fetchone()

                self.assertIsNotNone(
                    setting_row,
                    "No existing model setting found."
                )

                setting_id = int(setting_row[0])

                # End the read transaction before save_grounded_response()
                # starts its own transaction.
                connection.commit()

                # Save a simulated answer without calling Gemini.
                response_id = save_grounded_response(
                    connection,
                    setting_id=setting_id,
                    question=test_marker,
                    answer="The Cybersecurity program requires 34 credits.",
                    latency_ms=0,
                    contexts=[context],
                    retrieval_method="mysql_keyword",
                )

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
                self.assertEqual(saved["document_id"], context.document_id)
                self.assertEqual(saved["chunk_id"], context.chunk_id)
                self.assertEqual(saved["element_id"], context.element_id)
                self.assertEqual(saved["page_number_snapshot"], context.page_number)
                self.assertEqual(saved["content_type_snapshot"], "table")
                self.assertEqual(
                    saved["extraction_method_snapshot"],
                    "pymupdf_table",
                )
                self.assertEqual(saved["context_excerpt"], context.text)

                print("\nV2 retrieval provenance persistence verified:")
                print(f"  Response ID: {response_id}")
                print(f"  Document ID: {saved['document_id']}")
                print(f"  Chunk ID: {saved['chunk_id']}")
                print(f"  Element ID: {saved['element_id']}")
                print(f"  Page number: {saved['page_number_snapshot']}")
                print(f"  Content type: {saved['content_type_snapshot']}")
                print(f"  Extraction method: {saved['extraction_method_snapshot']}")

            finally:
                if response_id is not None:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "DELETE FROM rag_responses WHERE response_id = %s",
                            (response_id,),
                        )
                    connection.commit()


if __name__ == "__main__":
    unittest.main()
