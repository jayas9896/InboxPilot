"""Summary: Tests for meeting transcripts and summaries.

Importance: Ensures meeting transcript storage and summarization work.
Alternatives: Rely on manual testing for meeting summaries.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from inboxpilot.ai import MockAiProvider
from inboxpilot.models import Meeting
from inboxpilot.services import MeetingSummaryService
from inboxpilot.storage.sqlite_store import SqliteStore


def test_meeting_summary_creates_note(tmp_path: Path) -> None:
    """Summary: Verify meeting summarization creates a note.

    Importance: Confirms meeting summaries are persisted as notes.
    Alternatives: Store summaries as plain text files.
    """

    store = SqliteStore(str(tmp_path / "test.db"))
    store.initialize()
    service = MeetingSummaryService(
        store=store,
        ai_provider=MockAiProvider(),
        provider_name="mock",
        model_name="mock",
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
        ]
    )
    service.add_transcript(1, "We decided to ship on Friday.")
    note_id = service.summarize_meeting(1)
    notes = store.list_notes("meeting", 1)
    assert note_id > 0
    assert notes
