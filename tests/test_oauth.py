"""Summary: Tests for OAuth URL builders.

Importance: Ensures OAuth URL generation uses config values correctly.
Alternatives: Validate OAuth flows manually.
"""

from __future__ import annotations

from inboxpilot.config import AppConfig
from inboxpilot.oauth import build_google_auth_url, build_microsoft_auth_url


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
        google_client_secret="",
        microsoft_client_id="ms-client",
        microsoft_client_secret="",
        oauth_redirect_uri="http://localhost:8000/oauth/callback",
        triage_high_keywords=["urgent"],
        triage_medium_keywords=["review"],
    )


def test_google_auth_url_includes_client_id() -> None:
    url = build_google_auth_url(_config(), "state123")
    assert "google-client" in url


def test_microsoft_auth_url_includes_client_id() -> None:
    url = build_microsoft_auth_url(_config(), "state123")
    assert "ms-client" in url
