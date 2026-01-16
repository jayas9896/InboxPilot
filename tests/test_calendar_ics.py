"""Summary: Tests for iCalendar ingestion.

Importance: Ensures .ics parsing works for calendar ingestion.
Alternatives: Use only mock calendar data for tests.
"""

from __future__ import annotations

from pathlib import Path

from inboxpilot.calendar import IcsCalendarProvider


def test_ics_calendar_provider(tmp_path: Path) -> None:
    """Summary: Parse an .ics file into meeting records.

    Importance: Validates local calendar imports.
    Alternatives: Skip .ics support tests.
    """

    ics = tmp_path / "sample.ics"
    ics.write_text(
        """
        BEGIN:VCALENDAR
        BEGIN:VEVENT
        UID:test-1
        DTSTART:20260115T100000Z
        DTEND:20260115T103000Z
        SUMMARY:Team Sync
        ATTENDEE:MAILTO:a@example.com
        ATTENDEE:MAILTO:b@example.com
        END:VEVENT
        END:VCALENDAR
        """.strip(),
        encoding="utf-8",
    )
    provider = IcsCalendarProvider(ics)
    meetings = provider.fetch_upcoming(5)
    assert meetings[0].provider_event_id == "test-1"
    assert "a@example.com" in meetings[0].participants
