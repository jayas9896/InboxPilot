"""Summary: Tests for token storage and codec.

Importance: Ensures tokens are encoded and stored consistently.
Alternatives: Skip token storage until full OAuth flow exists.
"""

from __future__ import annotations

from inboxpilot.config import AppConfig
from inboxpilot.models import User
from inboxpilot.services import TokenService
from inboxpilot.storage.sqlite_store import SqliteStore
from inboxpilot.token_codec import TokenCodec


def _config() -> AppConfig:
    return AppConfig(
        db_path="test.db",
        ai_provider="mock",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        ollama_url="http://localhost:11434",
        ollama_model="llama3",
        imap_host=None,
        imap_user=None,
        imap_password=None,
        imap_mailbox="INBOX",
        api_host="127.0.0.1",
        api_port=8000,
        default_user_name="Local User",
        default_user_email="local@inboxpilot",
        api_key="",
        google_client_id="google-client",
        google_client_secret="google-secret",
        microsoft_client_id="ms-client",
        microsoft_client_secret="ms-secret",
        oauth_redirect_uri="http://localhost:8000/oauth/callback",
        google_token_url="https://oauth2.googleapis.com/token",
        microsoft_token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        triage_high_keywords=["urgent"],
        triage_medium_keywords=["review"],
        token_secret="secret",
    )


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
    service = TokenService(
        store=store,
        user_id=user_id,
        codec=TokenCodec("secret"),
        config=_config(),
    )
    service.store_tokens("google", "access", "refresh", None)
    loaded = service.load_tokens("google")
    assert loaded["access_token"] == "access"


def test_token_service_refreshes_on_expiry(tmp_path, monkeypatch) -> None:
    """Summary: Refresh tokens when they are expired.

    Importance: Ensures the refresh flow updates access tokens in storage.
    Alternatives: Require manual OAuth re-authentication.
    """

    from inboxpilot.oauth import OAuthTokenResult

    def _fake_refresh(*_args: object, **_kwargs: object) -> OAuthTokenResult:
        return OAuthTokenResult(
            access_token="new-access",
            refresh_token=None,
            expires_at=None,
            token_type="Bearer",
            raw={"access_token": "new-access"},
        )

    monkeypatch.setattr("inboxpilot.services.refresh_oauth_token", _fake_refresh)
    store = SqliteStore(str(tmp_path / "test.db"))
    store.initialize()
    user_id = store.ensure_user(User(display_name="Local User", email="local@inboxpilot"))
    service = TokenService(
        store=store,
        user_id=user_id,
        codec=TokenCodec("secret"),
        config=_config(),
    )
    service.store_tokens("google", "access", "refresh", "2000-01-01T00:00:00")
    access = service.get_access_token("google")
    assert access == "new-access"
