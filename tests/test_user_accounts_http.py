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

    def test_removing_a_chat_hides_it_from_recent_chats(self) -> None:
        andrew = self.signed_in("andrew2")
        _, chat = andrew.ask("When does Fall 2026 registration begin?")
        chat_id = chat["data"]["conversation_id"]
        status, _ = andrew.call("api/conversations.php", {"action": "archive", "conversation_id": chat_id})
        self.assertEqual(200, status)
        self.assertEqual([], andrew.chats()[1]["data"]["conversations"])
        self.assertEqual(404, andrew.ask("Is it online?", chat_id)[0])


if __name__ == "__main__":
    unittest.main()
