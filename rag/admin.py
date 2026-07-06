"""CLI bridge used by PHP document administration."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from database import database_connection, delete_uploaded_document
from ingest import ingest_document
from settings import load_settings
from vector_store import get_collection


def main() -> None:
    settings = load_settings()
    parser = argparse.ArgumentParser(description="Administer one uploaded document.")
    parser.add_argument("file", type=Path, nargs="?")
    parser.add_argument("--source-path", required=True)
    parser.add_argument("--category")
    parser.add_argument("--title")
    parser.add_argument("--original-filename")
    parser.add_argument("--delete", action="store_true")
    parser.add_argument("--init-schema", action="store_true")
    args = parser.parse_args()

    try:
        if args.delete:
            if not args.source_path.startswith("storage/uploads/"):
                raise ValueError("Only browser-uploaded documents can be deleted.")
            collection = get_collection(settings)
            collection.delete(where={"source_path": args.source_path})
            with database_connection(settings) as connection:
                delete_uploaded_document(connection, args.source_path)
            print(json.dumps({"deleted": True, "source_path": args.source_path}))
            return

        if args.file is None or not args.category or not args.title or not args.original_filename:
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
