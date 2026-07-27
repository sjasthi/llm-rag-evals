"""CLI bridge used by PHP document administration."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from database import (
    database_connection,
    delete_all_indexed_documents,
    delete_indexed_document,
)
from ingest import ingest_document
from settings import load_settings
from vector_store import delete_all_chunks, delete_source_chunks, get_collection


def main() -> None:
    settings = load_settings()
    parser = argparse.ArgumentParser(description="Administer the active document index.")
    parser.add_argument("file", type=Path, nargs="?")
    parser.add_argument("--source-path")
    parser.add_argument("--category")
    parser.add_argument("--title")
    parser.add_argument("--original-filename")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--delete", action="store_true")
    action.add_argument("--delete-all", action="store_true")
    parser.add_argument("--init-schema", action="store_true")
    args = parser.parse_args()

    try:
        if args.delete_all:
            collection = get_collection(settings)
            with database_connection(settings) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT source_path FROM documents ORDER BY document_id")
                    source_paths = [str(row[0]) for row in cursor.fetchall()]
                connection.commit()
                deleted_chunk_count = delete_all_chunks(collection)
                deleted_count = delete_all_indexed_documents(connection)
            print(json.dumps({
                "deleted": True,
                "deleted_count": deleted_count,
                "deleted_chunk_count": deleted_chunk_count,
                "source_paths": source_paths,
            }))
            return

        if args.delete:
            if not args.source_path:
                parser.error("--delete requires --source-path")
            collection = get_collection(settings)
            with database_connection(settings) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT 1 FROM documents WHERE source_path=%s",
                        (args.source_path,),
                    )
                    if cursor.fetchone() is None:
                        raise ValueError("Indexed document was not found.")
                connection.commit()
                deleted_chunk_count = delete_source_chunks(collection, args.source_path)
                delete_indexed_document(connection, args.source_path)
            print(json.dumps({
                "deleted": True,
                "source_path": args.source_path,
                "deleted_chunk_count": deleted_chunk_count,
            }))
            return

        if (
            args.file is None
            or not args.source_path
            or not args.category
            or not args.title
            or not args.original_filename
        ):
            parser.error("ingestion requires file, category, title, and original filename")
        document_id, chunk_count = ingest_document(
            args.file,
            source_path=args.source_path,
            category=args.category,
            title=args.title,
            original_filename=args.original_filename,
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap,
            init_schema=args.init_schema,
        )
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error

    print(json.dumps({"document_id": document_id, "chunk_count": chunk_count}))


if __name__ == "__main__":
    main()
