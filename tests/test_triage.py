"""Summary: Tests for triage scoring.

Importance: Ensures priority scoring works for urgent and normal messages.
Alternatives: Validate triage manually through the API.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from inboxpilot.models import Message, User
from inboxpilot.services import TriageService
from inboxpilot.storage.sqlite_store import SqliteStore


def test_triage_scores_high(tmp_path: Path) -> None:
    """Summary: Verify urgent keywords yield high priority.

    Importance: Confirms triage highlights urgent messages.
    Alternatives: Use manual triage only.
    """

    store = SqliteStore(str(tmp_path / "test.db"))
    store.initialize()
    user_id = store.ensure_user(User(display_name="Local User", email="local@inboxpilot"))
    store.save_messages(
        [
            Message(
                provider_message_id="msg-urgent",
                subject="Urgent request",
                sender="boss@example.com",
                recipients="you@example.com",
                timestamp=datetime.utcnow(),
                snippet="Urgent",
                body="Please follow up ASAP",
            )
        ],
        user_id=user_id,
    )
    service = TriageService(
        store=store,
        user_id=user_id,
        high_keywords=["urgent", "asap"],
        medium_keywords=["review"],
    )
    ranked = service.rank_messages(limit=5)
    assert ranked[0]["priority"] == "high"
