"""Summary: Tests for SQLite storage layer.

Importance: Ensures persistence behaves as expected for core workflows.
Alternatives: Rely on manual testing for storage operations.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from inboxpilot.models import Category, Message, Note
from inboxpilot.storage.sqlite_store import SqliteStore


def test_store_persists_messages(tmp_path: Path) -> None:
    """Summary: Verify messages are saved and listed.

    Importance: Confirms ingestion can be persisted for later queries.
    Alternatives: Use in-memory fixtures without database storage.
    """

    db_path = tmp_path / "test.db"
    store = SqliteStore(str(db_path))
    store.initialize()
    message = Message(
        provider_message_id="msg-1",
        subject="Hello",
        sender="sender@example.com",
        recipients="receiver@example.com",
        timestamp=datetime.utcnow(),
        snippet="Hello",
        body="Hello world",
    )
    store.save_messages([message])
    stored = store.list_messages(10)
    assert len(stored) == 1
    assert stored[0].subject == "Hello"


def test_store_categories_and_assignments(tmp_path: Path) -> None:
    """Summary: Verify categories can be assigned to messages.

    Importance: Ensures category system remains a first-class feature.
    Alternatives: Store category labels directly on messages.
    """

    db_path = tmp_path / "test.db"
    store = SqliteStore(str(db_path))
    store.initialize()
    category_id = store.create_category(Category(name="Recruiting", description="Hiring"))
    message = Message(
        provider_message_id="msg-2",
        subject="Interview",
        sender="hr@example.com",
        recipients="you@example.com",
        timestamp=datetime.utcnow(),
        snippet="Interview invite",
        body="Interview invite",
    )
    message_id = store.save_messages([message])[0]
    store.assign_category(message_id, category_id)
    categories = store.list_message_categories(message_id)
    assert categories[0].name == "Recruiting"


def test_store_notes(tmp_path: Path) -> None:
    """Summary: Verify notes are stored and retrieved.

    Importance: Supports action-item capture for follow-ups.
    Alternatives: Store notes in a separate text file.
    """

    db_path = tmp_path / "test.db"
    store = SqliteStore(str(db_path))
    store.initialize()
    note_id = store.add_note(Note(parent_type="message", parent_id=1, content="Follow up"))
    notes = store.list_notes("message", 1)
    assert note_id > 0
    assert notes[0].content == "Follow up"
