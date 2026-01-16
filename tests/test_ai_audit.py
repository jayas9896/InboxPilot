"""Summary: Tests for AI audit logs.

Importance: Ensures AI request and response listing works.
Alternatives: Inspect AI logs manually.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from inboxpilot.models import AiRequest, AiResponse, User
from inboxpilot.services import AiAuditService
from inboxpilot.storage.sqlite_store import SqliteStore


def test_ai_audit_listings(tmp_path: Path) -> None:
    """Summary: Verify AI audit lists return data.

    Importance: Confirms AI audit endpoints have data to serve.
    Alternatives: Use raw SQL for audits.
    """

    store = SqliteStore(str(tmp_path / "test.db"))
    store.initialize()
    user_id = store.ensure_user(User(display_name="Local User", email="local@inboxpilot"))
    request_id = store.log_ai_request(
        AiRequest(
            provider="mock",
            model="mock",
            prompt="Hello",
            purpose="test",
            timestamp=datetime.utcnow(),
        ),
        user_id=user_id,
    )
    store.log_ai_response(
        AiResponse(request_id=request_id, response_text="Hi", latency_ms=1, token_estimate=1)
    )
    audit = AiAuditService(store=store, user_id=user_id)
    requests = audit.list_requests(limit=5)
    responses = audit.list_responses(limit=5)
    assert requests
    assert responses
