# Metro State Source Documents

These documents are the initial source dataset for the RAG evaluation project.

Source:

`https://github.com/sjasthi/student-compass/tree/main/documents`

The folder structure from the source repository is preserved so document
categories remain clear during ingestion and evaluation.

Current intended use:

- seed the local document set,
- ingest documents into ChromaDB,
- store document metadata in MySQL,
- create evaluation questions and expected source mappings,
- compare MySQL-based retrieval and ChromaDB vector retrieval.

Generated files such as ChromaDB indexes, logs, uploads, and evaluation outputs
should not be stored in this folder.
