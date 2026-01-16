"""Summary: Tests for API key service logic.

Importance: Ensures per-user API key issuance and resolution work.
Alternatives: Validate keys manually through the API.
"""

from __future__ import annotations

from inboxpilot.models import User
from inboxpilot.services import ApiKeyService
from inboxpilot.storage.sqlite_store import SqliteStore


def test_api_key_roundtrip(tmp_path) -> None:
    """Summary: Verify API key creation and resolution.

    Importance: Confirms keys map back to the intended user.
    Alternatives: Use API integration tests only.
    """

    store = SqliteStore(str(tmp_path / "test.db"))
    store.initialize()
    user_id = store.ensure_user(User(display_name="Local User", email="local@inboxpilot"))
    service = ApiKeyService(store=store, token_secret="secret")
    key_id, token = service.create_api_key(user_id, label="test")
    assert key_id > 0
    resolved = service.resolve_user_id(token)
    assert resolved == user_id
    stored = service.list_api_keys(user_id)
    assert stored
    assert stored[0].token_hash != token


def test_api_key_revocation(tmp_path) -> None:
    """Summary: Verify API key revocation removes access.

    Importance: Confirms revoked keys no longer resolve to a user.
    Alternatives: Use status flags instead of deletion.
    """

    store = SqliteStore(str(tmp_path / "test.db"))
    store.initialize()
    user_id = store.ensure_user(User(display_name="Local User", email="local@inboxpilot"))
    service = ApiKeyService(store=store, token_secret="secret")
    key_id, token = service.create_api_key(user_id, label="test")
    assert service.resolve_user_id(token) == user_id
    deleted = service.revoke_api_key(user_id, key_id)
    assert deleted is True
    assert service.resolve_user_id(token) is None
