"""Summary: Tests for meeting search.

Importance: Ensures meeting search returns expected results.
Alternatives: Rely on list_meetings only.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from inboxpilot.models import Meeting, User
from inboxpilot.storage.sqlite_store import SqliteStore


def test_search_meetings(tmp_path: Path) -> None:
    """Summary: Search meetings by title.

    Importance: Confirms meeting search functionality.
    Alternatives: Filter meetings in memory.
    """

    store = SqliteStore(str(tmp_path / "test.db"))
    store.initialize()
    user_id = store.ensure_user(User(display_name="Local User", email="local@inboxpilot"))
    store.save_meetings(
        [
            Meeting(
                provider_event_id="meet-1",
                title="Project Kickoff",
                participants="a@example.com",
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                transcript_ref=None,
            )
        ],
        user_id=user_id,
    )
    results = store.search_meetings("Project", 5, user_id=user_id)
    assert results
    assert results[0].title == "Project Kickoff"
