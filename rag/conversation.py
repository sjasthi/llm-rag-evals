"""Conversation memory for multi-turn RAG chat (Version 2.0).

The memory is deliberately scoped to one active conversation thread, as
planned in docs/V2 docs/FP3_RAG_Evals_V2_Architecture_Plan.md section 5:

1. Every user question and assistant answer is persisted in order in the
   ``conversations`` / ``conversation_messages`` tables. Assistant messages
   link to the existing ``rag_responses`` row, so answer provenance and
   retrieved contexts are not duplicated.
2. Before answering a follow-up, a bounded window of recent messages is
   loaded (``bounded_history``) rather than the unlimited transcript.
3. The window is used twice:
   - ``contextual_retrieval_query`` turns a referential follow-up such as
     "What GPA do they need?" into a self-contained search query by joining
     it with the previous user question, so retrieval finds the right
     documents. This step is deterministic and provider-free.
   - ``llm.build_grounded_prompt`` shows the window to the model so it can
     interpret the follow-up. History is never treated as a source of
     facts; answers stay grounded in the retrieved excerpts.

Single-turn callers (evaluation runs, the Gold Standard study) pass no
conversation and therefore produce byte-identical prompts to Version 1.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


DEFAULT_HISTORY_MESSAGES = 6
"""Most recent messages (three user/assistant exchanges) supplied as memory."""

DEFAULT_HISTORY_CHARACTERS = 4000
"""Upper bound on history text so prompt cost stays predictable."""

TITLE_MAX_CHARACTERS = 120

UNKNOWN_CONVERSATION_EXIT_CODE = 3
"""answer.py exit status when a conversation id does not exist (read by api/ask.php)."""

_REFERENTIAL_WORDS = frozenset(
    {
        "it", "its", "it's", "they", "them", "their", "theirs", "they're",
        "that", "this", "those", "these", "there", "he", "she", "his", "her",
        "same", "also", "too", "else", "former", "latter", "one", "ones",
    }
)
_FOLLOW_UP_OPENERS = (
    "and ", "what about", "how about", "what if", "but ", "also ",
    "then ", "so ", "same ", "is that", "does that", "do they", "can they",
)
_WORD_PATTERN = re.compile(r"[a-z']+")


class UnknownConversationError(LookupError):
    """Raised when a caller references a conversation that does not exist."""


@dataclass(frozen=True)
class ConversationMessage:
    role: str
    content: str
    sequence_number: int | None = None
    response_id: int | None = None

    def __post_init__(self) -> None:
        if self.role not in {"user", "assistant"}:
            raise ValueError(f"Unsupported conversation role {self.role!r}")


def bounded_history(
    messages: Sequence[ConversationMessage],
    *,
    max_messages: int = DEFAULT_HISTORY_MESSAGES,
    max_characters: int = DEFAULT_HISTORY_CHARACTERS,
) -> list[ConversationMessage]:
    """Keep the most recent messages that fit both the count and size budget.

    Messages are kept whole, newest first, so the immediately preceding
    exchange always survives. If even the newest message is longer than the
    budget it is truncated from the start, keeping its final characters.
    """
    if max_messages <= 0 or max_characters <= 0:
        return []

    kept: list[ConversationMessage] = []
    used = 0
    for message in reversed(list(messages)[-max_messages:]):
        length = len(message.content)
        if used + length > max_characters:
            if not kept:
                kept.append(
                    ConversationMessage(
                        role=message.role,
                        content="..." + message.content[-(max_characters - 3):],
                        sequence_number=message.sequence_number,
                        response_id=message.response_id,
                    )
                )
            break
        kept.append(message)
        used += length
    kept.reverse()
    return kept


def is_follow_up(question: str) -> bool:
    """Heuristically detect a question that depends on earlier turns."""
    text = question.strip().lower()
    if not text:
        return False
    if text.startswith(_FOLLOW_UP_OPENERS):
        return True
    words = _WORD_PATTERN.findall(text)
    return any(word in _REFERENTIAL_WORDS for word in words)


def contextual_retrieval_query(
    question: str,
    history: Sequence[ConversationMessage],
) -> str:
    """Return the text to search with for this turn.

    A standalone question is searched as-is. A follow-up is combined with the
    most recent earlier user question, which usually names the subject the
    follow-up refers to ("first-year admission" for "What GPA do they need?").
    """
    question = question.strip()
    if not history or not is_follow_up(question):
        return question
    for message in reversed(history):
        if message.role == "user" and message.content.strip():
            previous = message.content.strip()
            if previous.lower() == question.lower():
                return question
            return f"{previous} {question}"
    return question


def format_history_for_prompt(history: Sequence[ConversationMessage]) -> str:
    lines = []
    for message in history:
        speaker = "User" if message.role == "user" else "Assistant"
        lines.append(f"{speaker}: {message.content.strip()}")
    return "\n".join(lines)


def conversation_title(question: str) -> str:
    title = " ".join(question.split())
    if len(title) <= TITLE_MAX_CHARACTERS:
        return title
    return title[: TITLE_MAX_CHARACTERS - 3].rstrip() + "..."


# ---------------------------------------------------------------------------
# MySQL persistence (tables defined in database/schema.sql)
# ---------------------------------------------------------------------------


def _end_implicit_read(connection: Any, was_in_transaction: bool) -> None:
    """Close the read-only transaction a SELECT opened when autocommit is off.

    Without this, a later ``start_transaction`` on the same connection fails
    with "Transaction already in progress". A transaction the caller already
    had open is left alone.
    """
    if not was_in_transaction and getattr(connection, "in_transaction", False):
        connection.rollback()


def _owner_clause(user_id: int | None) -> tuple[str, tuple[Any, ...]]:
    """SQL filter that limits a conversation lookup to its owner.

    ``user_id=None`` means a trusted caller (CLI or tests) that is not acting
    for a signed-in user; the web app always passes the session's user id.
    """
    if user_id is None:
        return "", ()
    return " AND user_id = %s", (user_id,)


def create_conversation(
    connection: Any,
    title: str | None = None,
    *,
    user_id: int | None = None,
) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO conversations (user_id, title, status) VALUES (%s, %s, 'active')",
            (user_id, conversation_title(title) if title else None),
        )
        conversation_id = int(cursor.lastrowid)
    connection.commit()
    return conversation_id


def require_conversation(
    connection: Any,
    conversation_id: int,
    *,
    user_id: int | None = None,
) -> None:
    """Raise UnknownConversationError unless the conversation is active and owned.

    A conversation that belongs to someone else is reported exactly like a
    missing one, so ids cannot be probed to discover other users' chats.
    """
    owner_sql, owner_params = _owner_clause(user_id)
    was_in_transaction = bool(getattr(connection, "in_transaction", False))
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT conversation_id FROM conversations "
            "WHERE conversation_id = %s AND status = 'active'" + owner_sql,
            (conversation_id, *owner_params),
        )
        row = cursor.fetchone()
    _end_implicit_read(connection, was_in_transaction)
    if row is None:
        raise UnknownConversationError(f"Conversation {conversation_id} was not found.")


def load_recent_messages(
    connection: Any,
    conversation_id: int,
    *,
    limit: int = DEFAULT_HISTORY_MESSAGES,
) -> list[ConversationMessage]:
    """Load the newest ``limit`` messages, returned oldest first."""
    if limit <= 0:
        return []
    was_in_transaction = bool(getattr(connection, "in_transaction", False))
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT role, content, sequence_number, response_id
            FROM conversation_messages
            WHERE conversation_id = %s
            ORDER BY sequence_number DESC
            LIMIT %s
            """,
            (conversation_id, limit),
        )
        rows = cursor.fetchall()
    _end_implicit_read(connection, was_in_transaction)
    messages = [
        ConversationMessage(
            role=str(role),
            content=str(content),
            sequence_number=int(sequence_number),
            response_id=None if response_id is None else int(response_id),
        )
        for role, content, sequence_number, response_id in rows
    ]
    messages.reverse()
    return messages


def append_exchange(
    connection: Any,
    conversation_id: int,
    *,
    question: str,
    answer: str,
    response_id: int | None,
    user_id: int | None = None,
) -> tuple[int, int]:
    """Append one user question and its assistant answer atomically.

    The conversation row is locked so concurrent requests on the same thread
    cannot claim the same sequence numbers. Returns the two message ids.
    """
    owner_sql, owner_params = _owner_clause(user_id)
    try:
        connection.start_transaction()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT conversation_id FROM conversations "
                "WHERE conversation_id = %s AND status = 'active'" + owner_sql + " FOR UPDATE",
                (conversation_id, *owner_params),
            )
            if cursor.fetchone() is None:
                raise UnknownConversationError(
                    f"Conversation {conversation_id} was not found."
                )
            cursor.execute(
                "SELECT COALESCE(MAX(sequence_number), 0) "
                "FROM conversation_messages WHERE conversation_id = %s",
                (conversation_id,),
            )
            next_sequence = int(cursor.fetchone()[0]) + 1
            cursor.execute(
                """
                INSERT INTO conversation_messages
                    (conversation_id, role, content, sequence_number, response_id)
                VALUES (%s, 'user', %s, %s, NULL)
                """,
                (conversation_id, question, next_sequence),
            )
            user_message_id = int(cursor.lastrowid)
            cursor.execute(
                """
                INSERT INTO conversation_messages
                    (conversation_id, role, content, sequence_number, response_id)
                VALUES (%s, 'assistant', %s, %s, %s)
                """,
                (conversation_id, answer, next_sequence + 1, response_id),
            )
            assistant_message_id = int(cursor.lastrowid)
            cursor.execute(
                "UPDATE conversations "
                "SET updated_at = CURRENT_TIMESTAMP, title = COALESCE(title, %s) "
                "WHERE conversation_id = %s",
                (conversation_title(question), conversation_id),
            )
        connection.commit()
        return user_message_id, assistant_message_id
    except Exception:
        connection.rollback()
        raise
