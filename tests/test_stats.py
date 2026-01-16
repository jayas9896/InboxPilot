"""Summary: Tests for stats snapshot.

Importance: Ensures analytics counts reflect stored data.
Alternatives: Validate stats manually via the API.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from inboxpilot.models import Category, Meeting, Message, Note, Task, User
from inboxpilot.services import StatsService
from inboxpilot.storage.sqlite_store import SqliteStore


def test_stats_snapshot(tmp_path: Path) -> None:
    """Summary: Verify stats include counts for core entities.

    Importance: Confirms dashboard metrics are populated.
    Alternatives: Use direct SQL queries in the API.
    """

    store = SqliteStore(str(tmp_path / "test.db"))
    store.initialize()
    user_id = store.ensure_user(User(display_name="Local User", email="local@inboxpilot"))
    store.create_category(Category(name="Test"), user_id=user_id)
    store.save_messages(
        [
            Message(
                provider_message_id="msg-1",
                subject="Hello",
                sender="a@example.com",
                recipients="b@example.com",
                timestamp=datetime.utcnow(),
                snippet="Hello",
                body="Hello",
            )
        ],
        user_id=user_id,
    )
    store.save_meetings(
        [
            Meeting(
                provider_event_id="meet-1",
                title="Sync",
                participants="a@example.com",
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                transcript_ref=None,
            )
        ],
        user_id=user_id,
    )
    store.add_note(Note(parent_type="message", parent_id=1, content="Note"), user_id=user_id)
    store.add_task(Task(parent_type="message", parent_id=1, description="Task"), user_id=user_id)
    stats = StatsService(store=store, user_id=user_id).snapshot()
    assert stats["messages"] == 1
    assert stats["meetings"] == 1
    assert stats["categories"] == 1
    assert stats["tasks"] == 1
    assert stats["notes"] == 1
