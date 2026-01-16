"""Summary: Tests for token storage and codec.

Importance: Ensures tokens are encoded and stored consistently.
Alternatives: Skip token storage until full OAuth flow exists.
"""

from __future__ import annotations

from inboxpilot.models import User
from inboxpilot.services import TokenService
from inboxpilot.storage.sqlite_store import SqliteStore
from inboxpilot.token_codec import TokenCodec


def test_token_codec_roundtrip() -> None:
    """Summary: Verify encoding and decoding restores plaintext.

    Importance: Ensures token storage can be reversed for use.
    Alternatives: Store tokens in a vault without encoding.
    """

    codec = TokenCodec("secret")
    encoded = codec.encode("token")
    decoded = codec.decode(encoded)
    assert decoded == "token"


def test_token_service_store_and_load(tmp_path) -> None:
    """Summary: Store and load tokens via the service.

    Importance: Confirms token storage works per user.
    Alternatives: Keep tokens in memory.
    """

    store = SqliteStore(str(tmp_path / "test.db"))
    store.initialize()
    user_id = store.ensure_user(User(display_name="Local User", email="local@inboxpilot"))
    service = TokenService(store=store, user_id=user_id, codec=TokenCodec("secret"))
    service.store_tokens("google", "access", "refresh", None)
    loaded = service.load_tokens("google")
    assert loaded["access_token"] == "access"
