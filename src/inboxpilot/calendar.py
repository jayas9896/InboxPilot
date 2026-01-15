"""Summary: Calendar provider interfaces and implementations.

Importance: Encapsulates read-only ingestion from calendar services.
Alternatives: Use provider SDKs directly without a shared abstraction.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
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
