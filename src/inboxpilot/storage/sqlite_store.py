"""Summary: SQLite storage implementation for InboxPilot.

Importance: Provides a local-first persistence layer for the MVP.
Alternatives: Use an ORM or an external database immediately.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

from inboxpilot.models import AiRequest, AiResponse, Category, Meeting, Message, Note


@dataclass(frozen=True)
class StoredMessage:
    """Summary: Message record with database identifier.

    Importance: Links messages to categories and notes in storage.
    Alternatives: Use provider_message_id as the only identifier.
    """

    id: int
    provider_message_id: str
    subject: str
    sender: str
    recipients: str
    timestamp: str
    snippet: str
    body: str


@dataclass(frozen=True)
class StoredCategory:
    """Summary: Category record with database identifier.

    Importance: Allows referencing categories from assignments.
    Alternatives: Use category names as natural keys.
    """

    id: int
    name: str
    description: str | None


@dataclass(frozen=True)
class StoredMeeting:
    """Summary: Meeting record with database identifier.

    Importance: Enables listing and referencing meetings in notes and chat.
    Alternatives: Store meetings only as raw provider IDs.
    """

    id: int
    provider_event_id: str
    title: str
    participants: str
    start_time: str
    end_time: str
    transcript_ref: str | None


class SqliteStore:
    """Summary: SQLite-backed storage for InboxPilot.

    Importance: Enables local-first persistence with minimal dependencies.
    Alternatives: Use Postgres and SQLAlchemy from day one.
    """

    def __init__(self, db_path: str) -> None:
        """Summary: Initialize the storage with a database path.

        Importance: Allows configurable database location per environment.
        Alternatives: Hardcode a default path in the class.
        """

        self._db_path = Path(db_path)

    def initialize(self) -> None:
        """Summary: Create tables if they do not exist.

        Importance: Ensures the database is ready for ingestion and queries.
        Alternatives: Run migrations using a dedicated migration tool.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider_message_id TEXT NOT NULL UNIQUE,
                    subject TEXT,
                    sender TEXT,
                    recipients TEXT,
                    timestamp TEXT,
                    snippet TEXT,
                    body TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS category_assignments (
                    message_id INTEGER NOT NULL,
                    category_id INTEGER NOT NULL,
                    PRIMARY KEY (message_id, category_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_type TEXT NOT NULL,
                    parent_id INTEGER NOT NULL,
                    content TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS meetings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider_event_id TEXT NOT NULL UNIQUE,
                    title TEXT,
                    participants TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    transcript_ref TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id INTEGER NOT NULL,
                    response_text TEXT NOT NULL,
                    latency_ms INTEGER NOT NULL,
                    token_estimate INTEGER NOT NULL
                )
                """
            )
            connection.commit()

    def save_messages(self, messages: list[Message]) -> list[int]:
        """Summary: Persist messages and return their database IDs.

        Importance: Enables later lookup for category assignment and chat context.
        Alternatives: Insert messages lazily on first query.
        """

        ids: list[int] = []
        with self._connection() as connection:
            cursor = connection.cursor()
            for message in messages:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO messages (
                        provider_message_id, subject, sender, recipients, timestamp, snippet, body
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message.provider_message_id,
                        message.subject,
                        message.sender,
                        message.recipients,
                        message.timestamp.isoformat(),
                        message.snippet,
                        message.body,
                    ),
                )
                if cursor.lastrowid:
                    ids.append(cursor.lastrowid)
                else:
                    cursor.execute(
                        "SELECT id FROM messages WHERE provider_message_id = ?",
                        (message.provider_message_id,),
                    )
                    row = cursor.fetchone()
                    if row:
                        ids.append(int(row[0]))
            connection.commit()
        return ids

    def list_messages(self, limit: int) -> list[StoredMessage]:
        """Summary: Retrieve recent messages from storage.

        Importance: Supplies chat context and CLI listing.
        Alternatives: Stream messages from the provider directly.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT id, provider_message_id, subject, sender, recipients, timestamp, snippet, body
                FROM messages
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
        return [StoredMessage(*row) for row in rows]

    def search_messages(self, query: str, limit: int) -> list[StoredMessage]:
        """Summary: Search messages by subject or body.

        Importance: Supports chat and quick filtering.
        Alternatives: Implement full-text search using SQLite FTS.
        """

        pattern = f"%{query}%"
        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT id, provider_message_id, subject, sender, recipients, timestamp, snippet, body
                FROM messages
                WHERE subject LIKE ? OR body LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (pattern, pattern, limit),
            )
            rows = cursor.fetchall()
        return [StoredMessage(*row) for row in rows]

    def create_category(self, category: Category) -> int:
        """Summary: Create a category and return its ID.

        Importance: Enables user-defined organization and templates.
        Alternatives: Store categories in a JSON config file.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO categories (name, description) VALUES (?, ?)",
                (category.name, category.description),
            )
            if cursor.lastrowid:
                category_id = cursor.lastrowid
            else:
                cursor.execute("SELECT id FROM categories WHERE name = ?", (category.name,))
                row = cursor.fetchone()
                category_id = int(row[0]) if row else 0
            connection.commit()
        return category_id

    def list_categories(self) -> list[StoredCategory]:
        """Summary: Retrieve all categories.

        Importance: Powers category management and assignment flows.
        Alternatives: Filter categories by active flags or templates.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT id, name, description FROM categories ORDER BY name")
            rows = cursor.fetchall()
        return [StoredCategory(*row) for row in rows]

    def save_meetings(self, meetings: list[Meeting]) -> list[int]:
        """Summary: Persist meetings and return their database IDs.

        Importance: Enables future meeting queries and note linking.
        Alternatives: Store meetings only in memory for the session.
        """

        ids: list[int] = []
        with self._connection() as connection:
            cursor = connection.cursor()
            for meeting in meetings:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO meetings (
                        provider_event_id, title, participants, start_time, end_time, transcript_ref
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        meeting.provider_event_id,
                        meeting.title,
                        meeting.participants,
                        meeting.start_time.isoformat(),
                        meeting.end_time.isoformat(),
                        meeting.transcript_ref,
                    ),
                )
                if cursor.lastrowid:
                    ids.append(cursor.lastrowid)
                else:
                    cursor.execute(
                        "SELECT id FROM meetings WHERE provider_event_id = ?",
                        (meeting.provider_event_id,),
                    )
                    row = cursor.fetchone()
                    if row:
                        ids.append(int(row[0]))
            connection.commit()
        return ids

    def list_meetings(self, limit: int) -> list[StoredMeeting]:
        """Summary: Retrieve recent meetings from storage.

        Importance: Supplies CLI listing and meeting context.
        Alternatives: Load meetings directly from providers on demand.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT id, provider_event_id, title, participants, start_time, end_time, transcript_ref
                FROM meetings
                ORDER BY start_time DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
        return [StoredMeeting(*row) for row in rows]

    def assign_category(self, message_id: int, category_id: int) -> None:
        """Summary: Assign a category to a message.

        Importance: Links messages to user-defined categories.
        Alternatives: Store category IDs directly on the message record.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO category_assignments (message_id, category_id)
                VALUES (?, ?)
                """,
                (message_id, category_id),
            )
            connection.commit()

    def list_message_categories(self, message_id: int) -> list[StoredCategory]:
        """Summary: List categories assigned to a message.

        Importance: Provides context for chat and review workflows.
        Alternatives: Denormalize categories onto the message record.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT c.id, c.name, c.description
                FROM categories c
                JOIN category_assignments ca ON ca.category_id = c.id
                WHERE ca.message_id = ?
                ORDER BY c.name
                """,
                (message_id,),
            )
            rows = cursor.fetchall()
        return [StoredCategory(*row) for row in rows]

    def add_note(self, note: Note) -> int:
        """Summary: Persist a note linked to a message or meeting.

        Importance: Captures user context and action items.
        Alternatives: Use a separate notes service.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO notes (parent_type, parent_id, content) VALUES (?, ?, ?)",
                (note.parent_type, note.parent_id, note.content),
            )
            note_id = cursor.lastrowid
            connection.commit()
        return int(note_id)

    def list_notes(self, parent_type: str, parent_id: int) -> list[Note]:
        """Summary: Retrieve notes for a message or meeting.

        Importance: Supports reviewing stored context for follow-ups.
        Alternatives: Store notes as part of the message body.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT parent_type, parent_id, content FROM notes WHERE parent_type = ? AND parent_id = ?",
                (parent_type, parent_id),
            )
            rows = cursor.fetchall()
        return [Note(*row) for row in rows]

    def log_ai_request(self, request: AiRequest) -> int:
        """Summary: Persist an AI request for auditing.

        Importance: Tracks prompts and providers used by the system.
        Alternatives: Use structured logs instead of database storage.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO ai_requests (provider, model, prompt, purpose, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    request.provider,
                    request.model,
                    request.prompt,
                    request.purpose,
                    request.timestamp.isoformat(),
                ),
            )
            request_id = cursor.lastrowid
            connection.commit()
        return int(request_id)

    def log_ai_response(self, response: AiResponse) -> int:
        """Summary: Persist an AI response for auditing.

        Importance: Enables traceability of AI outputs and latency.
        Alternatives: Store responses in a flat log file.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO ai_responses (request_id, response_text, latency_ms, token_estimate)
                VALUES (?, ?, ?, ?)
                """,
                (
                    response.request_id,
                    response.response_text,
                    response.latency_ms,
                    response.token_estimate,
                ),
            )
            response_id = cursor.lastrowid
            connection.commit()
        return int(response_id)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Summary: Context manager for SQLite connections.

        Importance: Ensures connections are closed cleanly after use.
        Alternatives: Keep a single long-lived connection.
        """

        connection = sqlite3.connect(self._db_path)
        try:
            yield connection
        finally:
            connection.close()


def default_store_path() -> str:
    """Summary: Provide the default database path.

    Importance: Centralizes the default storage location.
    Alternatives: Compute the path based on OS user directories.
    """

    return "inboxpilot.db"
