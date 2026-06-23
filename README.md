# LLM RAG Evaluation Project

An ICS 499 capstone web application for comparing Retrieval-Augmented
Generation (RAG) configurations and evaluation methods using Metro State
documents.

## Current Status

FP4 establishes the backend-ready project foundation. The frontend workspace
loads through PHP and now reflects the local Metro State document set. Shared
layout files, environment configuration, an initial MySQL schema, storage
folders, and Python RAG helper scripts have been added.

Full LLM calls, ChromaDB embedding persistence, evaluation runs, and dashboard
results are planned for later iterations.

## Technology Stack

- HTML, CSS, JavaScript, jQuery, and Bootstrap
- PHP
- MySQL
- Python helper scripts for RAG ingestion and retrieval preparation
- ChromaDB planned for vector storage
- Any approved LLM provider, such as OpenAI/ChatGPT, Gemini, or Claude

## Prerequisites

- PHP installed and available from the terminal
- Python 3 installed and available from the terminal
- MySQL installed for later database testing

The current frontend page does not require a database connection or API key to
open. Those are needed in later iterations when ingestion, retrieval, and LLM
calls are connected.

## Open the Frontend

From the project root, run:

```powershell
cd "C:\path\to\LLM RAG Evaluation Project"
php -S 127.0.0.1:8000
```

Then open this URL in a browser:

```text
http://127.0.0.1:8000/
```

Expected result:

- The RAG Evaluation Workspace page loads.
- The dashboard shows the current Metro State source document count.
- The dashboard shows the number of document categories.
- The page identifies the stack as PHP + MySQL + ChromaDB.

To stop the PHP server, return to the terminal and press `Ctrl+C`.

## FP4 Verification Commands

Run these from the project root.

Check PHP syntax:

```powershell
php -l index.php
php -l config\env.php
php -l config\database.php
```

Check the Python document chunking helper:

```powershell
python rag\ingest.py
```

Expected output:

```text
Prepared 77 chunks from 27 text documents.
Embedding generation and ChromaDB persistence will be added in FP5.
```

Check the temporary keyword retrieval helper:

```powershell
python rag\query.py "When does Fall 2026 registration begin?" --top-k 3
```

Expected result:

- The first result should come from
  `data/metrostate_documents/academic_calendar/fall_2026.txt`.
- The result should mention that Fall 2026 registration begins in eServices on
  Monday, March 23, 2026.

## Database Schema

The initial MySQL schema is stored in:

```text
database/schema.sql
```

It defines tables for:

- documents
- document chunks
- evaluation questions
- model settings
- evaluation runs
- RAG responses
- retrieved contexts
- evaluation scores

This schema is included for FP4 review. The current frontend can open without
importing the schema.

## Configuration

Copy `.env.example` to `.env` for local secrets when database or LLM work is
enabled in later iterations.

Do not commit `.env`.

Current safe example values are stored in:

```text
.env.example
```

## Planning Documents

- [Requirements](requirements.md)
- [Final project scope](docs/final-project-scope.md)
- [FP3-FP10 project plan](docs/fp3-project-plan.md)
- [UX design](docs/ux-design.md)
- [Code structure and conventions](docs/code-structure.md)
- [Recommended implementation approach](docs/implementation-approach.md)

## Source Documents

The initial Metro State document dataset is stored in
`data/metrostate_documents/`. These files were copied from the Student Compass
reference repository's `documents/` folder and will be used for ingestion,
retrieval, and evaluation work.

Current local source set:

- 27 text documents
- 8 document categories

## Security

Do not commit API keys, database passwords, private Metro State documents, or
uploaded user files. Use local environment configuration for secrets.
