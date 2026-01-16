"""Summary: Tests for connection storage.

Importance: Ensures integration records are stored and listed per user.
Alternatives: Validate connections manually through the CLI.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from inboxpilot.models import Connection, User
from inboxpilot.storage.sqlite_store import SqliteStore


def test_store_connections(tmp_path: Path) -> None:
    """Summary: Verify connection records are persisted.

    Importance: Keeps integration metadata available for UI/API views.
    Alternatives: Store connection records in config files only.
    """

    store = SqliteStore(str(tmp_path / "test.db"))
    store.initialize()
    user_id = store.ensure_user(User(display_name="Local User", email="local@inboxpilot"))
    connection = Connection(
        provider_type="email",
        provider_name="gmail",
        status="connected",
        created_at=datetime.utcnow(),
        details="read-only",
    )
    connection_id = store.add_connection(connection, user_id=user_id)
    connections = store.list_connections(user_id)
    assert connection_id > 0
    assert connections[0].provider_name == "gmail"
