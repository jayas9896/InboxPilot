"""Summary: Tests for message insights.

Importance: Ensures summaries and follow-up suggestions work as expected.
Alternatives: Validate insights manually through the CLI.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from inboxpilot.ai import MockAiProvider
from inboxpilot.models import Message, User
from inboxpilot.services import MessageInsightsService
from inboxpilot.storage.sqlite_store import SqliteStore


def test_message_summary_creates_note(tmp_path: Path) -> None:
    """Summary: Verify summary creates a note.

    Importance: Confirms summaries are persisted for review.
    Alternatives: Store summaries only in memory.
    """

    store = SqliteStore(str(tmp_path / "test.db"))
    store.initialize()
    user_id = store.ensure_user(User(display_name="Local User", email="local@inboxpilot"))
    message_id = store.save_messages(
        [
            Message(
                provider_message_id="msg-1",
                subject="Status update",
                sender="sender@example.com",
                recipients="you@example.com",
                timestamp=datetime.utcnow(),
                snippet="Status",
                body="Here is the weekly update.",
            )
        ],
        user_id=user_id,
    )[0]
    service = MessageInsightsService(
        store=store,
        ai_provider=MockAiProvider(),
        provider_name="mock",
        model_name="mock",
        user_id=user_id,
    )
    note_id = service.summarize_message(message_id)
    notes = store.list_notes("message", message_id, user_id=user_id)
    assert note_id > 0
    assert notes


def test_follow_up_suggestion_returns_text(tmp_path: Path) -> None:
    """Summary: Verify follow-up suggestion returns text.

    Importance: Ensures follow-up guidance is generated.
    Alternatives: Skip follow-up suggestions.
    """

    store = SqliteStore(str(tmp_path / "test.db"))
    store.initialize()
    user_id = store.ensure_user(User(display_name="Local User", email="local@inboxpilot"))
    message_id = store.save_messages(
        [
            Message(
                provider_message_id="msg-2",
                subject="Question",
                sender="sender@example.com",
                recipients="you@example.com",
                timestamp=datetime.utcnow(),
                snippet="Question",
                body="Can you share availability?",
            )
        ],
        user_id=user_id,
    )[0]
    service = MessageInsightsService(
        store=store,
        ai_provider=MockAiProvider(),
        provider_name="mock",
        model_name="mock",
        user_id=user_id,
    )
    suggestion = service.suggest_follow_up(message_id)
    assert suggestion
