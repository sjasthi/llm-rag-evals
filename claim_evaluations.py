"""Assign evaluation data saved before accounts existed to one account.

Migration 011 gives every saved answer and test run an owner where ownership
can be proven. Runs and answers from before accounts stay unowned, so the
Evaluation page hides them from everyone. Run this once to give that history
to the account that should keep it:

    python rag/claim_evaluations.py --username neha --dry-run
    python rag/claim_evaluations.py --username neha

Nothing is deleted, and rows that already have an owner are never changed.
"""

from __future__ import annotations

import argparse
import json
import sys

from database import database_connection
from settings import load_settings


def unowned_counts(connection) -> dict[str, int]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM evaluation_runs WHERE user_id IS NULL")
        runs = int(cursor.fetchone()[0])
        cursor.execute("SELECT COUNT(*) FROM rag_responses WHERE user_id IS NULL")
        responses = int(cursor.fetchone()[0])
    return {"runs": runs, "responses": responses}


def claim_unowned_evaluations(connection, user_id: int) -> dict[str, int]:
    """Give every unowned run, and every unowned saved answer, to ``user_id``."""
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE evaluation_runs SET user_id=%s WHERE user_id IS NULL", (user_id,)
        )
        runs = int(cursor.rowcount)
        cursor.execute(
            "UPDATE rag_responses SET user_id=%s WHERE user_id IS NULL", (user_id,)
        )
        responses = int(cursor.rowcount)
    connection.commit()
    return {"runs": runs, "responses": responses}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--username", required=True, help="Account that receives the history.")
    parser.add_argument("--dry-run", action="store_true", help="Only count unowned rows.")
    args = parser.parse_args()

    with database_connection(load_settings()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT user_id FROM users WHERE username=%s", (args.username,))
            row = cursor.fetchone()
        if row is None:
            parser.error(f"No account is named {args.username!r}.")
        user_id = int(row[0])
        if args.dry_run:
            result = {"dry_run": True, "unowned": unowned_counts(connection)}
        else:
            result = {"dry_run": False, "claimed": claim_unowned_evaluations(connection, user_id)}
    result["username"] = args.username
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
