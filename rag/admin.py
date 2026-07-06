"""CLI bridge used by PHP document administration."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ingest import ingest_document
from settings import load_settings


def main() -> None:
    settings = load_settings()
    parser = argparse.ArgumentParser(description="Ingest one uploaded document.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--source-path", required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--original-filename", required=True)
    parser.add_argument("--init-schema", action="store_true")
    args = parser.parse_args()

    try:
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
