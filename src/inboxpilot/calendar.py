"""Summary: Calendar provider interfaces and implementations.

Importance: Encapsulates read-only ingestion from calendar services.
Alternatives: Use provider SDKs directly without a shared abstraction.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from inboxpilot.models import Meeting


class CalendarProvider(ABC):
    """Summary: Abstract interface for calendar ingestion.

    Importance: Standardizes retrieval across mocked and real providers.
    Alternatives: Couple ingestion to a single calendar API.
    """

    @abstractmethod
    def fetch_upcoming(self, limit: int) -> list[Meeting]:
        """Summary: Fetch upcoming meetings from the provider.

        Importance: Drives meeting ingestion workflows.
        Alternatives: Fetch meetings by date range instead of a limit.
        """


class MockCalendarProvider(CalendarProvider):
    """Summary: Loads meetings from a local JSON fixture.

    Importance: Supports offline demos and tests.
    Alternatives: Generate synthetic meetings in code.
    """

    def __init__(self, fixture_path: Path) -> None:
        """Summary: Initialize the mock calendar provider.

        Importance: Allows configurable sample data for testing.
        Alternatives: Embed sample data directly in the class.
        """

        self._fixture_path = fixture_path

    def fetch_upcoming(self, limit: int) -> list[Meeting]:
        """Summary: Load upcoming meetings from the fixture file.

        Importance: Provides predictable meeting data for the MVP.
        Alternatives: Return an empty list when fixtures are missing.
        """

        data = json.loads(self._fixture_path.read_text(encoding="utf-8"))
        meetings = [
            Meeting(
                provider_event_id=item["provider_event_id"],
                title=item["title"],
                participants=item["participants"],
                start_time=datetime.fromisoformat(item["start_time"]),
                end_time=datetime.fromisoformat(item["end_time"]),
                transcript_ref=item.get("transcript_ref"),
            )
            for item in data
        ]
        return meetings[:limit]


class IcsCalendarProvider(CalendarProvider):
    """Summary: Loads meetings from an iCalendar (.ics) file.

    Importance: Enables calendar ingestion without direct provider APIs.
    Alternatives: Use Google or Microsoft APIs with OAuth.
    """

    def __init__(self, ics_path: Path) -> None:
        """Summary: Initialize the iCalendar provider.

        Importance: Allows local file-based calendar ingestion.
        Alternatives: Fetch calendar events via network APIs.
        """

        self._ics_path = ics_path

    def fetch_upcoming(self, limit: int) -> list[Meeting]:
        """Summary: Parse upcoming meetings from an .ics file.

        Importance: Supports local-first calendar imports.
        Alternatives: Use a dedicated iCalendar parsing library.
        """

        raw = self._ics_path.read_text(encoding="utf-8")
        events = _parse_ics_events(raw)
        meetings = [
            Meeting(
                provider_event_id=event.get("UID", f"ics-{index}"),
                title=event.get("SUMMARY", "Untitled"),
                participants=event.get("ATTENDEE", ""),
                start_time=_parse_ics_datetime(event.get("DTSTART", "")),
                end_time=_parse_ics_datetime(event.get("DTEND", "")),
                transcript_ref=None,
            )
            for index, event in enumerate(events)
        ]
        return meetings[:limit]


def _parse_ics_events(raw: str) -> list[dict[str, str]]:
    """Summary: Parse raw iCalendar data into event dictionaries.

    Importance: Extracts minimal fields needed for meeting ingestion.
    Alternatives: Use an iCalendar library for robust parsing.
    """

    unfolded_lines: list[str] = []
    for line in raw.splitlines():
        if line.startswith(" ") and unfolded_lines:
            unfolded_lines[-1] += line[1:]
        else:
            unfolded_lines.append(line.strip())
    events: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in unfolded_lines:
        if line == "BEGIN:VEVENT":
            current = {}
            continue
        if line == "END:VEVENT" and current is not None:
            events.append(current)
            current = None
            continue
        if current is None or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.split(";", 1)[0]
        if key == "ATTENDEE":
            existing = current.get("ATTENDEE", "")
            current["ATTENDEE"] = ", ".join(
                [item for item in [existing, value.replace("MAILTO:", "")] if item]
            )
        else:
            current[key] = value
    return events


def _parse_ics_datetime(value: str) -> datetime:
    """Summary: Parse a minimal iCalendar datetime string.

    Importance: Normalizes calendar event times for storage.
    Alternatives: Treat timestamps as raw strings.
    """

    cleaned = value.replace("Z", "")
    if len(cleaned) == 8:
        parsed = datetime.strptime(cleaned, "%Y%m%d")
    else:
        parsed = datetime.strptime(cleaned, "%Y%m%dT%H%M%S")
    if value.endswith("Z"):
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
