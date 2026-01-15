"""Summary: Tests for calendar ingestion and storage.

Importance: Ensures meeting workflows are persisted correctly.
Alternatives: Validate calendar ingestion manually.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from inboxpilot.calendar import MockCalendarProvider
from inboxpilot.models import Meeting
from inboxpilot.storage.sqlite_store import SqliteStore


def test_mock_calendar_provider_reads_fixture(tmp_path: Path) -> None:
    """Summary: Ensure mock provider returns meetings.

    Importance: Keeps demos and tests deterministic.
    Alternatives: Use generated sample data.
    """

    fixture = tmp_path / "meetings.json"
    fixture.write_text(
        """
        [
          {
            "provider_event_id": "meet-1",
            "title": "Standup",
            "participants": "team@example.com",
            "start_time": "2026-01-15T09:00:00",
            "end_time": "2026-01-15T09:15:00",
            "transcript_ref": null
          }
        ]
        """.strip(),
        encoding="utf-8",
    )
    provider = MockCalendarProvider(fixture)
    meetings = provider.fetch_upcoming(5)
    assert len(meetings) == 1
    assert meetings[0].title == "Standup"


def test_store_persists_meetings(tmp_path: Path) -> None:
    """Summary: Verify meetings are saved and listed.

    Importance: Confirms meeting ingestion storage behavior.
    Alternatives: Store meeting data in memory only.
    """

    db_path = tmp_path / "test.db"
    store = SqliteStore(str(db_path))
    store.initialize()
    meeting = Meeting(
        provider_event_id="meet-2",
        title="Review",
        participants="lead@example.com",
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow(),
        transcript_ref=None,
    )
    store.save_meetings([meeting])
    stored = store.list_meetings(10)
    assert len(stored) == 1
    assert stored[0].title == "Review"
