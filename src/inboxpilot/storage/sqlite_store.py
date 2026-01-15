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

from inboxpilot.models import AiRequest, AiResponse, Category, Meeting, Message, Note, Task, User


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
class StoredUser:
    """Summary: User record with database identifier.

    Importance: Enables multi-user and future tenant boundaries.
    Alternatives: Keep only a single implicit user without records.
    """

    id: int
    display_name: str
    email: str


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


@dataclass(frozen=True)
class StoredTask:
    """Summary: Task record with database identifier.

    Importance: Allows tracking action items linked to messages or meetings.
    Alternatives: Store tasks as notes or free-form text only.
    """

    id: int
    parent_type: str
    parent_id: int
    description: str
    status: str
    due_date: str | None


@dataclass(frozen=True)
class StoredMeetingTranscript:
    """Summary: Meeting transcript record.

    Importance: Stores transcript text for summarization and task extraction.
    Alternatives: Store transcripts in external object storage only.
    """

    meeting_id: int
    content: str


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
                    user_id INTEGER,
                    name TEXT NOT NULL,
                    description TEXT,
                    UNIQUE(name, user_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
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
                    user_id INTEGER,
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
                    user_id INTEGER,
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
                    user_id INTEGER,
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
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    parent_type TEXT NOT NULL,
                    parent_id INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    due_date TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS meeting_transcripts (
                    meeting_id INTEGER PRIMARY KEY,
                    content TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    display_name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE
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
        self._ensure_column("categories", "user_id")
        self._ensure_column("messages", "user_id")
        self._ensure_column("notes", "user_id")
        self._ensure_column("meetings", "user_id")
        self._ensure_column("ai_requests", "user_id")
        self._ensure_column("tasks", "user_id")

    def ensure_user(self, user: User) -> int:
        """Summary: Ensure a user exists and return their ID.

        Importance: Provides a stable user record for data ownership.
        Alternatives: Omit user records in single-user mode.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO users (display_name, email) VALUES (?, ?)",
                (user.display_name, user.email),
            )
            if cursor.lastrowid:
                user_id = cursor.lastrowid
            else:
                cursor.execute("SELECT id FROM users WHERE email = ?", (user.email,))
                row = cursor.fetchone()
                user_id = int(row[0]) if row else 0
            connection.commit()
        return int(user_id)

    def save_messages(self, messages: list[Message], user_id: int | None = None) -> list[int]:
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
                        user_id, provider_message_id, subject, sender, recipients, timestamp, snippet, body
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
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

    def list_messages(self, limit: int, user_id: int | None = None) -> list[StoredMessage]:
        """Summary: Retrieve recent messages from storage.

        Importance: Supplies chat context and CLI listing.
        Alternatives: Stream messages from the provider directly.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            if user_id is None:
                cursor.execute(
                    """
                    SELECT id, provider_message_id, subject, sender, recipients, timestamp, snippet, body
                    FROM messages
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, provider_message_id, subject, sender, recipients, timestamp, snippet, body
                    FROM messages
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (user_id, limit),
                )
            rows = cursor.fetchall()
        return [StoredMessage(*row) for row in rows]

    def search_messages(
        self, query: str, limit: int, user_id: int | None = None
    ) -> list[StoredMessage]:
        """Summary: Search messages by subject or body.

        Importance: Supports chat and quick filtering.
        Alternatives: Implement full-text search using SQLite FTS.
        """

        pattern = f"%{query}%"
        with self._connection() as connection:
            cursor = connection.cursor()
            if user_id is None:
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
            else:
                cursor.execute(
                    """
                    SELECT id, provider_message_id, subject, sender, recipients, timestamp, snippet, body
                    FROM messages
                    WHERE user_id = ? AND (subject LIKE ? OR body LIKE ?)
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (user_id, pattern, pattern, limit),
                )
            rows = cursor.fetchall()
        return [StoredMessage(*row) for row in rows]

    def create_category(self, category: Category, user_id: int | None = None) -> int:
        """Summary: Create a category and return its ID.

        Importance: Enables user-defined organization and templates.
        Alternatives: Store categories in a JSON config file.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO categories (user_id, name, description) VALUES (?, ?, ?)",
                (user_id, category.name, category.description),
            )
            if cursor.lastrowid:
                category_id = cursor.lastrowid
            else:
                cursor.execute("SELECT id FROM categories WHERE name = ?", (category.name,))
                row = cursor.fetchone()
                category_id = int(row[0]) if row else 0
            connection.commit()
        return category_id

    def list_categories(self, user_id: int | None = None) -> list[StoredCategory]:
        """Summary: Retrieve all categories.

        Importance: Powers category management and assignment flows.
        Alternatives: Filter categories by active flags or templates.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            if user_id is None:
                cursor.execute("SELECT id, name, description FROM categories ORDER BY name")
            else:
                cursor.execute(
                    "SELECT id, name, description FROM categories WHERE user_id = ? ORDER BY name",
                    (user_id,),
                )
            rows = cursor.fetchall()
        return [StoredCategory(*row) for row in rows]

    def save_meetings(self, meetings: list[Meeting], user_id: int | None = None) -> list[int]:
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
                        user_id, provider_event_id, title, participants, start_time, end_time, transcript_ref
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
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

    def list_meetings(self, limit: int, user_id: int | None = None) -> list[StoredMeeting]:
        """Summary: Retrieve recent meetings from storage.

        Importance: Supplies CLI listing and meeting context.
        Alternatives: Load meetings directly from providers on demand.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            if user_id is None:
                cursor.execute(
                    """
                    SELECT id, provider_event_id, title, participants, start_time, end_time, transcript_ref
                    FROM meetings
                    ORDER BY start_time DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, provider_event_id, title, participants, start_time, end_time, transcript_ref
                    FROM meetings
                    WHERE user_id = ?
                    ORDER BY start_time DESC
                    LIMIT ?
                    """,
                    (user_id, limit),
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

    def add_note(self, note: Note, user_id: int | None = None) -> int:
        """Summary: Persist a note linked to a message or meeting.

        Importance: Captures user context and action items.
        Alternatives: Use a separate notes service.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO notes (user_id, parent_type, parent_id, content) VALUES (?, ?, ?, ?)",
                (user_id, note.parent_type, note.parent_id, note.content),
            )
            note_id = cursor.lastrowid
            connection.commit()
        return int(note_id)

    def list_notes(
        self, parent_type: str, parent_id: int, user_id: int | None = None
    ) -> list[Note]:
        """Summary: Retrieve notes for a message or meeting.

        Importance: Supports reviewing stored context for follow-ups.
        Alternatives: Store notes as part of the message body.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            if user_id is None:
                cursor.execute(
                    "SELECT parent_type, parent_id, content FROM notes WHERE parent_type = ? AND parent_id = ?",
                    (parent_type, parent_id),
                )
            else:
                cursor.execute(
                    """
                    SELECT parent_type, parent_id, content
                    FROM notes
                    WHERE parent_type = ? AND parent_id = ? AND user_id = ?
                    """,
                    (parent_type, parent_id, user_id),
                )
            rows = cursor.fetchall()
        return [Note(*row) for row in rows]

    def add_task(self, task: Task, user_id: int | None = None) -> int:
        """Summary: Persist a task linked to a message or meeting.

        Importance: Tracks action items for follow-up workflows.
        Alternatives: Store tasks in a separate task manager.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO tasks (user_id, parent_type, parent_id, description, status, due_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, task.parent_type, task.parent_id, task.description, task.status, task.due_date),
            )
            task_id = cursor.lastrowid
            connection.commit()
        return int(task_id)

    def list_tasks(
        self, parent_type: str, parent_id: int, user_id: int | None = None
    ) -> list[StoredTask]:
        """Summary: Retrieve tasks for a message or meeting.

        Importance: Supports reviewing action items derived from communications.
        Alternatives: Store tasks as notes without structured fields.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            if user_id is None:
                cursor.execute(
                    """
                    SELECT id, parent_type, parent_id, description, status, due_date
                    FROM tasks
                    WHERE parent_type = ? AND parent_id = ?
                    ORDER BY id ASC
                    """,
                    (parent_type, parent_id),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, parent_type, parent_id, description, status, due_date
                    FROM tasks
                    WHERE parent_type = ? AND parent_id = ? AND user_id = ?
                    ORDER BY id ASC
                    """,
                    (parent_type, parent_id, user_id),
                )
            rows = cursor.fetchall()
        return [StoredTask(*row) for row in rows]

    def save_meeting_transcript(self, meeting_id: int, content: str) -> None:
        """Summary: Save or update a meeting transcript.

        Importance: Enables AI summaries and task extraction from meetings.
        Alternatives: Store transcripts as notes only.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO meeting_transcripts (meeting_id, content)
                VALUES (?, ?)
                ON CONFLICT(meeting_id) DO UPDATE SET content = excluded.content
                """,
                (meeting_id, content),
            )
            connection.commit()

    def get_meeting_transcript(self, meeting_id: int) -> StoredMeetingTranscript | None:
        """Summary: Retrieve a stored meeting transcript.

        Importance: Supplies transcript text for summarization workflows.
        Alternatives: Load transcripts from external storage.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT meeting_id, content FROM meeting_transcripts WHERE meeting_id = ?",
                (meeting_id,),
            )
            row = cursor.fetchone()
        return StoredMeetingTranscript(*row) if row else None

    def get_message(self, message_id: int, user_id: int | None = None) -> StoredMessage | None:
        """Summary: Retrieve a message by database ID.

        Importance: Supports task extraction and draft workflows.
        Alternatives: Filter messages in memory after listing all.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            if user_id is None:
                cursor.execute(
                    """
                    SELECT id, provider_message_id, subject, sender, recipients, timestamp, snippet, body
                    FROM messages
                    WHERE id = ?
                    """,
                    (message_id,),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, provider_message_id, subject, sender, recipients, timestamp, snippet, body
                    FROM messages
                    WHERE id = ? AND user_id = ?
                    """,
                    (message_id, user_id),
                )
            row = cursor.fetchone()
        return StoredMessage(*row) if row else None

    def log_ai_request(self, request: AiRequest, user_id: int | None = None) -> int:
        """Summary: Persist an AI request for auditing.

        Importance: Tracks prompts and providers used by the system.
        Alternatives: Use structured logs instead of database storage.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO ai_requests (user_id, provider, model, prompt, purpose, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
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

    def _ensure_column(self, table: str, column: str) -> None:
        """Summary: Ensure a column exists in a table.

        Importance: Provides lightweight migration support for new fields.
        Alternatives: Use a migration tool to manage schema changes.
        """

        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(f"PRAGMA table_info({table})")
            columns = {row[1] for row in cursor.fetchall()}
            if column in columns:
                return
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} INTEGER")
            connection.commit()

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
