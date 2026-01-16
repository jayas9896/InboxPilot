"""Summary: Tests for OAuth URL builders.

Importance: Ensures OAuth URL generation uses config values correctly.
Alternatives: Validate OAuth flows manually.
"""

from __future__ import annotations

from inboxpilot.config import AppConfig
from inboxpilot.oauth import (
    build_google_auth_url,
    build_microsoft_auth_url,
    _refresh_payload,
    _token_payload,
)


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
        google_api_base_url="https://gmail.googleapis.com/gmail/v1",
        microsoft_graph_base_url="https://graph.microsoft.com/v1.0",
        triage_high_keywords=["urgent"],
        triage_medium_keywords=["review"],
        token_secret="secret",
    )


def test_google_auth_url_includes_client_id() -> None:
    url = build_google_auth_url(_config(), "state123")
    assert "google-client" in url


def test_microsoft_auth_url_includes_client_id() -> None:
    url = build_microsoft_auth_url(_config(), "state123")
    assert "ms-client" in url


def test_google_token_payload_includes_redirect_uri() -> None:
    payload = _token_payload(_config(), "google", "code123")
    assert payload["redirect_uri"] == "http://localhost:8000/oauth/callback"


def test_microsoft_token_payload_includes_scope() -> None:
    payload = _token_payload(_config(), "microsoft", "code123")
    assert "scope" in payload


def test_google_refresh_payload_includes_grant_type() -> None:
    payload = _refresh_payload(_config(), "google", "refresh")
    assert payload["grant_type"] == "refresh_token"


def test_microsoft_refresh_payload_includes_scope() -> None:
    payload = _refresh_payload(_config(), "microsoft", "refresh")
    assert "scope" in payload
