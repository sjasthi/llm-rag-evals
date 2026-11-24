"""Grant or revoke the administrator role.

Administrators manage the shared document library (the bundled Metro State
corpus) and change Gold Standard question review status. Every other account
only manages its own uploads, chats and evaluations.

    python rag/manage_admins.py --list
    python rag/manage_admins.py --grant neha
    python rag/manage_admins.py --revoke neha
"""

from __future__ import annotations

import argparse
import json
import sys

from database import database_connection
from settings import load_settings


def set_admin(connection, username: str, is_admin: bool) -> bool:
    """Return True when the account exists (and now has the requested role)."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT user_id FROM users WHERE username=%s", (username,))
        if cursor.fetchone() is None:
            return False
        cursor.execute("UPDATE users SET is_admin=%s WHERE username=%s", (is_admin, username))
    connection.commit()
    return True


def list_admins(connection) -> list[str]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT username FROM users WHERE is_admin=TRUE ORDER BY username")
        return [str(row[0]) for row in cursor.fetchall()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Grant or revoke the administrator role.")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--grant", metavar="USERNAME")
    action.add_argument("--revoke", metavar="USERNAME")
    action.add_argument("--list", action="store_true")
    args = parser.parse_args()

    with database_connection(load_settings()) as connection:
        if args.list:
            result = {"admins": list_admins(connection)}
        else:
            username = args.grant or args.revoke
            if not set_admin(connection, username, bool(args.grant)):
                parser.error(f"No account is named {username!r}.")
            result = {"username": username, "is_admin": bool(args.grant)}
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
