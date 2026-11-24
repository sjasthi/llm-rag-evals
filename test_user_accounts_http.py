"""End-to-end tests for Chat accounts through the real PHP endpoints.

Starts PHP's built-in server against the configured MySQL database. Retrieval
and Gemini are replaced by tests/fixtures/fake_answer_runner.py, so no
embedding model or paid call is needed. Skips when PHP with pdo_mysql or the
database is unavailable.
"""

from __future__ import annotations

import http.cookiejar
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "rag"))

from database import database_connection  # noqa: E402
from settings import load_settings  # noqa: E402

PHP = shutil.which("php")
PASSWORD = "correct horse battery"


def php_has_pdo_mysql() -> bool:
    if PHP is None:
        return False
    result = subprocess.run([PHP, "-m"], capture_output=True, text=True, check=False)
    return "pdo_mysql" in result.stdout


def database_available() -> bool:
    try:
        with database_connection(load_settings()) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM users LIMIT 1")
                cursor.fetchall()
        return True
    except Exception:
        return False


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class Browser:
    """One visitor with their own cookies (session) and CSRF token."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )
        self.csrf = ""

    def call(self, path, payload=None, *, method=None, csrf=True):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/{path}",
            data=data,
            method=method or ("GET" if payload is None else "POST"),
        )
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if csrf and self.csrf:
            request.add_header("X-CSRF-Token", self.csrf)
        try:
            with self.opener.open(request, timeout=60) as response:
                status, body = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, body = error.code, error.read()
        parsed = json.loads(body.decode("utf-8"))
        if isinstance(parsed, dict) and parsed.get("csrf_token"):
            self.csrf = parsed["csrf_token"]
        return status, parsed

    def start(self):
        return self.call("api/auth.php")

    def register(self, username, password=PASSWORD, display_name=""):
        return self.call(
            "api/auth.php",
            {"action": "register", "username": username, "password": password, "display_name": display_name},
        )

    def login(self, username, password=PASSWORD):
        return self.call("api/auth.php", {"action": "login", "username": username, "password": password})

    def ask(self, question, conversation_id=None, action="answer"):
        return self.call(
            "api/ask.php",
            {
                "action": action,
                "question": question,
                "retrieval_method": "chroma_vector",
                "top_k": 1,
                "temperature": 0.0,
                "top_p": 0.9,
                "conversation_id": conversation_id,
            },
        )

    def chats(self):
        return self.call("api/conversations.php")

    def messages(self, conversation_id):
        return self.call(f"api/conversations.php?conversation_id={conversation_id}")


PHP_READY = php_has_pdo_mysql()
DATABASE_READY = database_available()
if os.environ.get("REQUIRE_ACCOUNT_HTTP_TESTS") == "1" and not (PHP_READY and DATABASE_READY):
    # CI sets this so a missing PHP extension or database fails loudly instead of skipping.
    raise RuntimeError(
        f"Account HTTP tests cannot run: php+pdo_mysql={PHP_READY}, database={DATABASE_READY}"
    )


@unittest.skipUnless(PHP_READY, "PHP with pdo_mysql is required")
@unittest.skipUnless(DATABASE_READY, "MySQL with the current schema is required")
class UserAccountHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="rag-accounts-"))
        runner = PROJECT_ROOT / "tests" / "fixtures" / "fake_answer_runner.py"

        if os.name == "nt":
            wrapper = cls.temp_dir / "python.cmd"
            wrapper.write_text(
                f'@echo off\r\n"{sys.executable}" "{runner}" %*\r\n',
                encoding="utf-8",
            )
        else:
            wrapper = cls.temp_dir / "python"
            wrapper.write_text(
                f'#!/bin/sh\nexec "{sys.executable}" "{runner}" "$@"\n',
                encoding="utf-8",
            )
            wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        settings = load_settings()
        env = os.environ.copy()
        env.update(
            {
                "DB_HOST": settings.db_host,
                "DB_PORT": str(settings.db_port),
                "DB_NAME": settings.db_name,
                "DB_USER": settings.db_user,
                "DB_PASSWORD": settings.db_password,
                "PYTHON_BIN": str(wrapper),
                "ALLOW_PAID_GENERATION": "1",
                "ALLOW_UNKNOWN_GENERATION_COST": "1",
                "ALLOW_ACCOUNT_REGISTRATION": "1",
            }
        )
        port = free_port()
        cls.server = subprocess.Popen(
            [PHP, "-S", f"127.0.0.1:{port}", "-t", str(PROJECT_ROOT)],
            cwd=PROJECT_ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        cls.base_url = f"http://127.0.0.1:{port}"
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                    break
            except OSError:
                time.sleep(0.1)
        cls.marker = uuid4().hex[:10]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.terminate()
        cls.server.wait(timeout=10)
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
        with database_connection(load_settings()) as connection:
            with connection.cursor() as cursor:
                pattern = f"%{cls.marker}"
                cursor.execute(
                    "DELETE FROM rag_responses WHERE response_id IN ("
                    "SELECT m.response_id FROM conversation_messages m "
                    "JOIN conversations c ON c.conversation_id = m.conversation_id "
                    "JOIN users u ON u.user_id = c.user_id "
                    "WHERE u.username LIKE %s AND m.response_id IS NOT NULL)",
                    (pattern,),
                )
                cursor.execute("DELETE FROM users WHERE username LIKE %s", (pattern,))
            connection.commit()

    def name(self, base: str) -> str:
        return f"{base}_{self.marker}"

    def signed_in(self, base: str, display_name: str = "") -> Browser:
        browser = Browser(self.base_url)
        browser.start()
        status, body = browser.register(self.name(base), display_name=display_name)
        self.assertEqual(201, status, body)
        return browser

    def test_state_changes_require_the_session_csrf_token(self) -> None:
        browser = Browser(self.base_url)
        status, body = browser.start()
        self.assertEqual(200, status)
        self.assertIsNone(body["user"])
        status, _ = browser.call(
            "api/auth.php",
            {"action": "register", "username": self.name("nocsrf"), "password": PASSWORD},
            csrf=False,
        )
        self.assertEqual(403, status)

    def test_registration_and_sign_in_rules(self) -> None:
        browser = Browser(self.base_url)
        browser.start()
        self.assertEqual(422, browser.register(self.name("weak"), password="short")[0])
        self.assertEqual(422, browser.register("x")[0])
        status, body = browser.register(self.name("andrew"), display_name="Andrew")
        self.assertEqual(201, status)
        self.assertEqual("Andrew", body["user"]["display_name"])
        self.assertNotIn("password_hash", json.dumps(body))

        other = Browser(self.base_url)
        other.start()
        self.assertEqual(409, other.register(self.name("andrew"))[0])
        self.assertEqual(401, other.login(self.name("andrew"), "wrong password")[0])
        self.assertEqual(401, other.login(self.name("nobody"))[0])
        status, body = other.login(self.name("andrew"))
        self.assertEqual(200, status)
        self.assertEqual(self.name("andrew"), body["user"]["username"])

        status, body = other.call("api/auth.php", {"action": "logout"})
        self.assertEqual(200, status)
        self.assertIsNone(body["user"])
        self.assertEqual(401, other.chats()[0])

    def test_signed_out_visitors_can_preview_but_not_ask(self) -> None:
        browser = Browser(self.base_url)
        browser.start()
        status, body = browser.ask("When does registration begin?")
        self.assertEqual(401, status)
        self.assertTrue(body["sign_in_required"])
        status, body = browser.ask("When does registration begin?", action="preview")
        self.assertEqual(200, status, body)
        self.assertEqual(1, len(body["data"]["sources"]))

    def test_multiturn_chat_is_saved_to_the_signed_in_user_and_can_be_resumed(self) -> None:
        chris = self.signed_in("chris", "Chris")
        status, first = chris.ask("What are the first-year admission requirements?")
        self.assertEqual(200, status, first)
        conversation_id = first["data"]["conversation_id"]
        self.assertIn("[history:no]", first["data"]["answer"])

        status, second = chris.ask("What GPA do they need?", conversation_id)
        self.assertEqual(200, status, second)
        self.assertEqual(conversation_id, second["data"]["conversation_id"])
        self.assertEqual(2, second["data"]["history_messages_used"])
        self.assertIn("[history:yes]", second["data"]["answer"])
        self.assertIn("first-year admission requirements", second["data"]["retrieval_query"])

        status, listing = chris.chats()
        self.assertEqual(200, status)
        chats = listing["data"]["conversations"]
        self.assertEqual([conversation_id], [chat["conversation_id"] for chat in chats])
        self.assertEqual(2, chats[0]["question_count"])
        self.assertEqual("What are the first-year admission requirements?", chats[0]["title"])

        # Sign in again from a new browser and continue where Chris left off.
        later = Browser(self.base_url)
        later.start()
        self.assertEqual(200, later.login(self.name("chris"))[0])
        status, thread = later.messages(conversation_id)
        self.assertEqual(200, status)
        self.assertEqual(
            ["user", "assistant", "user", "assistant"],
            [message["role"] for message in thread["data"]["messages"]],
        )
        status, third = later.ask("And for transfer students?", conversation_id)
        self.assertEqual(200, status, third)
        self.assertEqual(4, third["data"]["history_messages_used"])
        self.assertEqual(3, later.chats()[1]["data"]["conversations"][0]["question_count"])

        # Improvement 4: "it" in a question about another school is not treated
        # as a follow-up to the Metro State admissions topic.
        other_school = "What does it cost to attend the University of Minnesota?"
        status, fourth = later.ask(other_school, conversation_id)
        self.assertEqual(200, status, fourth)
        self.assertEqual(other_school, fourth["data"]["retrieval_query"])
        self.assertEqual("unchanged", fourth["data"]["query_rewrite_status"])
        self.assertEqual("rewritten", second["data"]["query_rewrite_status"])

    def test_users_only_see_and_continue_their_own_chats(self) -> None:
        chris = self.signed_in("chris2", "Chris")
        neha = self.signed_in("neha", "Neha")
        _, chris_chat = chris.ask("What are the first-year admission requirements?")
        chris_id = chris_chat["data"]["conversation_id"]
        _, neha_chat = neha.ask("When is the tuition payment deadline?")
        neha_id = neha_chat["data"]["conversation_id"]

        self.assertEqual([neha_id], [c["conversation_id"] for c in neha.chats()[1]["data"]["conversations"]])
        self.assertEqual([chris_id], [c["conversation_id"] for c in chris.chats()[1]["data"]["conversations"]])

        # Neha cannot read, continue, preview inside or remove Chris's chat.
        self.assertEqual(404, neha.messages(chris_id)[0])
        status, body = neha.ask("What GPA do they need?", chris_id)
        self.assertEqual(404, status)
        self.assertTrue(body["conversation_reset"])
        self.assertEqual(404, neha.ask("What GPA do they need?", chris_id, action="preview")[0])
        self.assertEqual(
            404, neha.call("api/conversations.php", {"action": "archive", "conversation_id": chris_id})[0]
        )
        status, thread = chris.messages(chris_id)
        self.assertEqual(2, len(thread["data"]["messages"]), "Chris's chat must be unchanged")

        # A signed-out visitor cannot reach it either.
        stranger = Browser(self.base_url)
        stranger.start()
        self.assertEqual(401, stranger.messages(chris_id)[0])
        self.assertEqual(401, stranger.ask("What GPA do they need?", chris_id)[0])

    def test_an_answer_that_could_not_be_saved_is_shown_but_not_marked_saved(self) -> None:
        """Improvement 2: generated and saved are reported separately."""
        dana = self.signed_in("dana")
        status, body = dana.ask("What are the admission requirements? [simulate-save-failure]")
        self.assertEqual(200, status, body)
        data = body["data"]
        self.assertIn("Fake answer to:", data["answer"], "the generated answer is still returned")
        self.assertFalse(data["saved"])
        self.assertIn("could not be saved", data["save_warning"])
        self.assertIsNone(data["response_id"])
        self.assertIsNone(data["conversation_id"])
        self.assertNotIn("persistence_error", data, "database errors stay in the server log")
        self.assertEqual([], dana.chats()[1]["data"]["conversations"], "nothing appears in Recent chats")

        # A failure inside an existing chat leaves that chat's history unchanged.
        status, first = dana.ask("When does registration begin?")
        self.assertTrue(first["data"]["saved"])
        self.assertIsNone(first["data"]["save_warning"])
        chat_id = first["data"]["conversation_id"]
        status, body = dana.ask("Is it online? [simulate-save-failure]", chat_id)
        self.assertEqual(200, status, body)
        self.assertFalse(body["data"]["saved"])
        self.assertEqual(chat_id, body["data"]["conversation_id"])
        _, thread = dana.messages(chat_id)
        self.assertEqual(2, len(thread["data"]["messages"]))

    def test_long_chat_reopens_at_its_newest_messages_and_pages_back(self) -> None:
        """Improvement 3: a 250-message chat shows messages 51-250, then 1-50."""
        from conversation import append_exchange, create_conversation  # noqa: PLC0415

        erin = self.signed_in("erin")
        with database_connection(load_settings()) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id FROM users WHERE username=%s", (self.name("erin"),))
                user_id = int(cursor.fetchone()[0])
            chat_id = create_conversation(connection, "Long chat", user_id=user_id)
            for turn in range(1, 126):
                append_exchange(
                    connection, chat_id, question=f"question {turn}", answer=f"answer {turn}",
                    response_id=None, user_id=user_id,
                )

        status, body = erin.messages(chat_id)
        self.assertEqual(200, status, body)
        data = body["data"]
        sequences = [m["sequence_number"] for m in data["messages"]]
        self.assertEqual(list(range(51, 251)), sequences, "newest 200, oldest first")
        self.assertEqual("question 26", data["messages"][0]["content"])
        self.assertEqual("answer 125", data["messages"][-1]["content"], "newest message is last")
        self.assertEqual(250, data["total_messages"])
        self.assertTrue(data["has_earlier"])
        self.assertEqual(51, data["earliest_sequence"])

        status, body = erin.call(f"api/conversations.php?conversation_id={chat_id}&before_sequence=51")
        self.assertEqual(200, status, body)
        earlier = body["data"]
        self.assertEqual(list(range(1, 51)), [m["sequence_number"] for m in earlier["messages"]])
        self.assertFalse(earlier["has_earlier"])
        self.assertEqual(422, erin.call(f"api/conversations.php?conversation_id={chat_id}&before_sequence=x")[0])

        # Paging is still limited to the owner.
        other = self.signed_in("erin_other")
        self.assertEqual(
            404, other.call(f"api/conversations.php?conversation_id={chat_id}&before_sequence=51")[0]
        )
        with database_connection(load_settings()) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM conversation_messages WHERE conversation_id=%s", (chat_id,)
                )
                self.assertEqual(250, int(cursor.fetchone()[0]), "every message stays stored")

    # --- Documents and Gold Standard (Improvement 5) ---------------------------

    def user_id(self, base: str) -> int:
        with database_connection(load_settings()) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id FROM users WHERE username=%s", (self.name(base),))
                return int(cursor.fetchone()[0])

    def make_admin(self, base: str) -> None:
        with database_connection(load_settings()) as connection:
            with connection.cursor() as cursor:
                cursor.execute("UPDATE users SET is_admin=TRUE WHERE username=%s", (self.name(base),))
            connection.commit()

    def indexed_document(self, label: str, owner: int | None) -> int:
        path = f"test/{label}-{self.marker}-{uuid4().hex[:6]}.txt"
        with database_connection(load_settings()) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO documents (title, category, source_path, user_id, status) "
                    "VALUES (%s, 'testing', %s, %s, 'ingested')",
                    (f"{label} {self.marker}", path, owner),
                )
                document_id = int(cursor.lastrowid)
            connection.commit()
        self.addCleanup(self.delete_document_row, document_id)
        return document_id

    @staticmethod
    def delete_document_row(document_id: int) -> None:
        with database_connection(load_settings()) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM documents WHERE document_id=%s", (document_id,))
            connection.commit()

    @staticmethod
    def document_exists(document_id: int) -> bool:
        with database_connection(load_settings()) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM documents WHERE document_id=%s", (document_id,))
                return cursor.fetchone() is not None

    def listed(self, browser: Browser) -> dict[int, dict]:
        status, body = browser.call("api/documents.php")
        self.assertEqual(200, status, body)
        return {int(d["document_id"]): d for d in body["data"]}

    def test_documents_are_private_to_their_uploader_and_the_library_is_shared(self) -> None:
        fran = self.signed_in("docfran")
        gus = self.signed_in("docgus")
        shared = self.indexed_document("shared", None)
        frans = self.indexed_document("fran", self.user_id("docfran"))
        frans_second = self.indexed_document("fran2", self.user_id("docfran"))
        guss = self.indexed_document("gus", self.user_id("docgus"))

        fran_view = self.listed(fran)
        self.assertIn(shared, fran_view)
        self.assertIn(frans, fran_view)
        self.assertNotIn(guss, fran_view, "another user's upload is not listed")
        self.assertEqual((True, False), (fran_view[shared]["shared"], fran_view[shared]["can_manage"]))
        self.assertEqual((False, True), (fran_view[frans]["shared"], fran_view[frans]["can_manage"]))
        self.assertNotIn(frans, self.listed(gus))

        def delete(browser, document_id):
            return browser.call("api/documents.php", {"document_id": document_id}, method="DELETE")

        self.assertEqual(404, delete(fran, guss)[0], "another user's upload looks missing")
        self.assertEqual(403, delete(fran, shared)[0], "only an administrator manages the library")
        status, body = fran.call(
            "api/documents.php", {"action": "restore_bundled", "confirmation": "RESTORE"}
        )
        self.assertEqual(403, status, body)
        self.assertTrue(self.document_exists(guss) and self.document_exists(shared))

        status, body = delete(fran, frans)
        self.assertEqual(200, status, body)
        self.assertFalse(self.document_exists(frans))

        # "Delete all" clears only Fran's own uploads.
        status, body = fran.call(
            "api/documents.php", {"action": "delete_all", "confirmation": "DELETE ALL"}, method="DELETE"
        )
        self.assertEqual(200, status, body)
        self.assertFalse(self.document_exists(frans_second))
        self.assertTrue(self.document_exists(guss), "other users' uploads are untouched")
        self.assertTrue(self.document_exists(shared), "the shared library is untouched")

    def test_administrators_manage_the_shared_library_and_gold_standard(self) -> None:
        hana = self.signed_in("dochana")
        ivan = self.signed_in("docivan")
        self.make_admin("dochana")
        hana.login(self.name("dochana"))  # a fresh sign-in carries the role to the page
        status, session = hana.start()
        self.assertTrue(session["user"]["is_admin"])
        self.assertFalse(ivan.start()[1]["user"]["is_admin"])

        shared = self.indexed_document("shared-admin", None)
        ivans = self.indexed_document("ivan", self.user_id("docivan"))
        hana_view = self.listed(hana)
        self.assertTrue(hana_view[shared]["can_manage"])
        self.assertNotIn(ivans, hana_view, "administrators do not see private uploads either")
        self.assertEqual(
            404, hana.call("api/documents.php", {"document_id": ivans}, method="DELETE")[0]
        )

        # Gold Standard review status: shared data, administrator only.
        change = {"question_id": 2**31, "review_status": "reviewed"}
        status, body = ivan.call("api/evaluations.php", change, method="PATCH")
        self.assertEqual(403, status, body)
        status, body = hana.call("api/evaluations.php", change, method="PATCH")
        self.assertEqual(404, status, body)  # allowed through; that question does not exist

        status, body = hana.call("api/documents.php", {"document_id": shared}, method="DELETE")
        self.assertEqual(200, status, body)
        self.assertFalse(self.document_exists(shared))

    def test_removing_a_chat_hides_it_from_recent_chats(self) -> None:
        andrew = self.signed_in("andrew2")
        _, chat = andrew.ask("When does Fall 2026 registration begin?")
        chat_id = chat["data"]["conversation_id"]
        status, _ = andrew.call("api/conversations.php", {"action": "archive", "conversation_id": chat_id})
        self.assertEqual(200, status)
        self.assertEqual([], andrew.chats()[1]["data"]["conversations"])
        self.assertEqual(404, andrew.ask("Is it online?", chat_id)[0])

    # --- Evaluation data is isolated by account (Improvement 1) ---------------

    def saved_response_id(self, browser: Browser, question: str) -> int:
        """Ask in Chat and return the rag_responses id saved for the answer."""
        status, body = browser.ask(question)
        self.assertEqual(200, status, body)
        conversation_id = body["data"]["conversation_id"]
        _, thread = browser.messages(conversation_id)
        response_ids = [m["response_id"] for m in thread["data"]["messages"] if m["response_id"]]
        self.assertEqual(1, len(response_ids), thread)
        return int(response_ids[0])

    def owned_run(self, browser_username: str, setting_from_response: int) -> tuple[int, int]:
        """Store a completed test run with one saved answer for an account."""
        with database_connection(load_settings()) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id FROM users WHERE username=%s", (browser_username,))
                user_id = int(cursor.fetchone()[0])
                cursor.execute(
                    "SELECT setting_id FROM rag_responses WHERE response_id=%s",
                    (setting_from_response,),
                )
                setting_id = int(cursor.fetchone()[0])
                cursor.execute(
                    "INSERT INTO evaluation_runs (setting_id, user_id, run_name, status, started_at, completed_at) "
                    "VALUES (%s, %s, %s, 'completed', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                    (setting_id, user_id, f"isolation run {self.marker}"),
                )
                run_id = int(cursor.lastrowid)
                cursor.execute(
                    "INSERT INTO rag_responses (run_id, user_id, setting_id, question_text, answer_text, retrieval_method) "
                    "VALUES (%s, %s, %s, 'Run question?', 'Run answer.', 'chroma_vector')",
                    (run_id, user_id, setting_id),
                )
                response_id = int(cursor.lastrowid)
            connection.commit()
        self.addCleanup(self.delete_run, run_id)
        return run_id, response_id

    @staticmethod
    def delete_run(run_id: int) -> None:
        with database_connection(load_settings()) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM rag_responses WHERE run_id=%s", (run_id,))
                cursor.execute("DELETE FROM evaluation_runs WHERE run_id=%s", (run_id,))
            connection.commit()

    def review(self, browser: Browser, response_id: int):
        return browser.call(
            "api/evaluations.php",
            {
                "action": "human_review",
                "response_id": response_id,
                "reviewer_alias": "tester",
                "overall_decision": "acceptable",
            },
        )

    def test_evaluation_lists_only_show_the_signed_in_users_data(self) -> None:
        chris = self.signed_in("evalchris", "Chris")
        neha = self.signed_in("evalneha", "Neha")
        chris_answer = self.saved_response_id(chris, "What are the first-year admission requirements?")
        neha_answer = self.saved_response_id(neha, "When is the tuition payment deadline?")
        chris_run, chris_run_answer = self.owned_run(self.name("evalchris"), chris_answer)
        self.assertEqual(201, self.review(chris, chris_answer)[0])

        status, chris_view = chris.call("api/evaluations.php")
        self.assertEqual(200, status, chris_view)
        data = chris_view["data"]
        self.assertIn(chris_answer, [int(r["response_id"]) for r in data["standaloneResponses"]])
        self.assertNotIn(neha_answer, [int(r["response_id"]) for r in data["standaloneResponses"]])
        self.assertIn(chris_run, [int(r["run_id"]) for r in data["runs"]])
        self.assertIn(chris_run_answer, [int(r["response_id"]) for r in data["responses"]])
        self.assertEqual(1, data["findings"]["human_review_count"])

        status, neha_view = neha.call("api/evaluations.php")
        self.assertEqual(200, status, neha_view)
        data = neha_view["data"]
        self.assertEqual([neha_answer], [int(r["response_id"]) for r in data["standaloneResponses"]])
        self.assertEqual([], data["runs"])
        self.assertEqual([], data["responses"])
        self.assertEqual([], data["findings"]["run_metric_summaries"])
        self.assertEqual(0, data["findings"]["human_review_count"])
        listing = json.dumps(neha_view)
        self.assertNotIn("first-year admission requirements", listing)
        self.assertNotIn(f"isolation run {self.marker}", listing)

    def test_users_cannot_open_score_review_or_export_another_users_records(self) -> None:
        chris = self.signed_in("evalchris2", "Chris")
        neha = self.signed_in("evalneha2", "Neha")
        chris_answer = self.saved_response_id(chris, "What are the first-year admission requirements?")
        neha_answer = self.saved_response_id(neha, "When is the tuition payment deadline?")
        chris_run, chris_run_answer = self.owned_run(self.name("evalchris2"), chris_answer)

        # Each user can open their own saved answers.
        self.assertEqual(200, chris.call(f"api/evaluations.php?response_id={chris_answer}")[0])
        self.assertEqual(200, chris.call(f"api/evaluations.php?response_id={chris_run_answer}")[0])
        self.assertEqual(200, neha.call(f"api/evaluations.php?response_id={neha_answer}")[0])

        # Changing an ID in the request never reaches another user's data, and
        # the answer is the same 404 as for an ID that does not exist.
        missing = neha.call("api/evaluations.php?response_id=999999999")
        for response_id in (chris_answer, chris_run_answer):
            status, body = neha.call(f"api/evaluations.php?response_id={response_id}")
            self.assertEqual((404, missing[1]), (status, body))
            self.assertEqual(404, self.review(neha, response_id)[0])
            status, body = neha.call(
                "api/evaluate_standalone.php", {"action": "preflight", "response_id": response_id}
            )
            self.assertEqual(404, status, body)
        self.assertEqual(404, neha.call(f"api/exports.php?run_id={chris_run}&format=json")[0])
        self.assertEqual(404, neha.call(f"api/exports.php?run_id={chris_run}&format=csv")[0])
        status, body = neha.call(
            "api/run_evaluation.php", {"action": "preflight", "run_id": chris_run, "limit": 1}
        )
        self.assertEqual(404, status, body)
        status, body = neha.call(
            "api/run_evaluation.php",
            {"action": "evaluate", "run_id": chris_run, "response_id": chris_run_answer, "limit": 1},
        )
        self.assertEqual(404, status, body)
        status, body = neha.call(
            "api/test_runs.php",
            {
                "action": "preflight",
                "dataset_id": 1,
                "name": "Borrowed baseline",
                "question_ids": [1],
                "retrieval_method": "chroma_vector",
                "top_k": 3,
                "temperature": 0.0,
                "top_p": 0.9,
                "model": "gemini-2.5-flash",
                "experiment_mode": "comparison",
                "experiment_key": "borrowed",
                "baseline_run_id": chris_run,
                "controlled_variable": "top_k",
                "change_from_baseline": "top_k 3 instead of 5",
            },
        )
        self.assertEqual(404, status, body)

        # A response ID that belongs to a different run is rejected too.
        status, body = chris.call(
            "api/run_evaluation.php",
            {"action": "preflight", "run_id": chris_run, "response_id": chris_answer, "limit": 1},
        )
        self.assertEqual(404, status, body)

        # Nothing was written to Chris's records.
        with database_connection(load_settings()) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM human_reviews WHERE response_id IN (%s, %s)",
                    (chris_answer, chris_run_answer),
                )
                self.assertEqual(0, int(cursor.fetchone()[0]))

        # The owner can still export their own run.
        status, export = chris.call(f"api/exports.php?run_id={chris_run}&format=json")
        self.assertEqual(200, status, export)
        self.assertEqual([chris_run_answer], [int(r["response_id"]) for r in export["responses"]])


@unittest.skipUnless(DATABASE_READY, "MySQL with the current schema is required")
class EvaluationOwnershipMigrationTests(unittest.TestCase):
    """Migration 011 and rag/claim_evaluations.py keep history without deleting it."""

    def setUp(self) -> None:
        self.marker = uuid4().hex[:10]
        self.settings = load_settings()

    def tearDown(self) -> None:
        with database_connection(self.settings) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM rag_responses WHERE question_text LIKE %s", (f"%{self.marker}",)
                )
                cursor.execute("DELETE FROM evaluation_runs WHERE run_name LIKE %s", (f"%{self.marker}",))
                cursor.execute("DELETE FROM users WHERE username LIKE %s", (f"%{self.marker}",))
            connection.commit()

    def test_migration_assigns_provable_owners_and_claim_keeps_the_rest(self) -> None:
        sys.path.insert(0, str(PROJECT_ROOT / "rag"))
        from claim_evaluations import claim_unowned_evaluations  # noqa: PLC0415
        from database import _execute_sql_script  # noqa: PLC0415

        with database_connection(self.settings) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (username, display_name, password_hash) VALUES (%s, 'Owner', 'x')",
                    (f"owner_{self.marker}",),
                )
                owner = int(cursor.lastrowid)
                cursor.execute(
                    "INSERT INTO conversations (user_id, title) VALUES (%s, %s)", (owner, self.marker)
                )
                conversation = int(cursor.lastrowid)
                cursor.execute("SELECT setting_id FROM model_settings LIMIT 1")
                row = cursor.fetchone()
                if row is None:
                    self.skipTest("model_settings has no rows")
                setting = int(row[0])

                def legacy_answer(label: str, run_id: int | None = None) -> int:
                    cursor.execute(
                        "INSERT INTO rag_responses (run_id, setting_id, question_text, answer_text, retrieval_method) "
                        "VALUES (%s, %s, %s, 'answer', 'chroma_vector')",
                        (run_id, setting, f"{label} {self.marker}"),
                    )
                    return int(cursor.lastrowid)

                chat_answer = legacy_answer("chat")
                cursor.execute(
                    "INSERT INTO conversation_messages (conversation_id, role, content, sequence_number, response_id) "
                    "VALUES (%s, 'assistant', 'answer', 1, %s)",
                    (conversation, chat_answer),
                )
                cursor.execute(
                    "INSERT INTO evaluation_runs (setting_id, user_id, run_name) VALUES (%s, %s, %s)",
                    (setting, owner, f"owned {self.marker}"),
                )
                owned_run_answer = legacy_answer("owned run", int(cursor.lastrowid))
                cursor.execute(
                    "INSERT INTO evaluation_runs (setting_id, run_name) VALUES (%s, %s)",
                    (setting, f"legacy {self.marker}"),
                )
                legacy_run = int(cursor.lastrowid)
                legacy_run_answer = legacy_answer("legacy run", legacy_run)
                orphan_answer = legacy_answer("cli")
            connection.commit()

            migration = PROJECT_ROOT / "database" / "migrations" / "011_evaluation_ownership.sql"
            _execute_sql_script(connection, migration.read_text(encoding="utf-8"))
            connection.commit()

            def owners() -> dict[int, int | None]:
                with connection.cursor() as cursor:
                    ids = (chat_answer, owned_run_answer, legacy_run_answer, orphan_answer)
                    cursor.execute(
                        "SELECT response_id, user_id FROM rag_responses WHERE response_id IN (%s,%s,%s,%s)",
                        ids,
                    )
                    return {int(r[0]): (None if r[1] is None else int(r[1])) for r in cursor.fetchall()}

            self.assertEqual(
                {chat_answer: owner, owned_run_answer: owner, legacy_run_answer: None, orphan_answer: None},
                owners(),
            )

            claimed = claim_unowned_evaluations(connection, owner)
            self.assertGreaterEqual(claimed["runs"], 1)
            self.assertGreaterEqual(claimed["responses"], 2)
            self.assertEqual(
                {chat_answer: owner, owned_run_answer: owner, legacy_run_answer: owner, orphan_answer: owner},
                owners(),
            )
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id FROM evaluation_runs WHERE run_id=%s", (legacy_run,))
                self.assertEqual(owner, int(cursor.fetchone()[0]))


if __name__ == "__main__":
    unittest.main()
