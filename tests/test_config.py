"""Summary: Tests for configuration loading.

Importance: Ensures defaults, .env, and environment overrides behave correctly.
Alternatives: Validate configuration manually during runtime.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from inboxpilot.config import AppConfig, load_defaults, load_dotenv


def test_load_defaults_reads_json(tmp_path: Path) -> None:
    """Summary: Verify defaults are parsed from JSON.

    Importance: Confirms config file is the source of truth for variables.
    Alternatives: Hardcode defaults in the test.
    """

    defaults_path = tmp_path / "defaults.json"
    defaults_path.write_text("{\"db_path\": \"test.db\"}", encoding="utf-8")
    defaults = load_defaults(defaults_path)
    assert defaults["db_path"] == "test.db"


def test_load_dotenv_sets_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Summary: Ensure .env values populate environment variables.

    Importance: Validates local secret loading without external tools.
    Alternatives: Assume OS environment is always set.
    """

    env_path = tmp_path / ".env"
    env_path.write_text("INBOXPILOT_AI_PROVIDER=ollama\n", encoding="utf-8")
    monkeypatch.delenv("INBOXPILOT_AI_PROVIDER", raising=False)
    load_dotenv(env_path)
    assert os.getenv("INBOXPILOT_AI_PROVIDER") == "ollama"


def test_app_config_uses_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Summary: Verify AppConfig honors defaults when env is absent.

    Importance: Confirms config file remains the baseline for variables.
    Alternatives: Inline defaults directly in the AppConfig class.
    """

    defaults_path = tmp_path / "defaults.json"
    defaults_path.write_text(
        """
        {
          \"db_path\": \"test.db\",
          \"ai_provider\": \"mock\",
          \"openai_api_key\": \"\",
          \"openai_model\": \"gpt-4o-mini\",
          \"ollama_url\": \"http://localhost:11434\",
          \"ollama_model\": \"llama3\",
          \"imap_host\": \"\",
          \"imap_user\": \"\",
          \"imap_password\": \"\",
          \"imap_mailbox\": \"INBOX\",
          \"api_host\": \"127.0.0.1\",
          \"api_port\": \"8000\",
          \"default_user_name\": \"Local User\",
          \"default_user_email\": \"local@inboxpilot\",
          \"api_key\": \"\",
          \"google_client_id\": \"\",
          \"google_client_secret\": \"\",
          \"microsoft_client_id\": \"\",
          \"microsoft_client_secret\": \"\",
          \"oauth_redirect_uri\": \"http://localhost:8000/oauth/callback\",
          \"google_token_url\": \"https://oauth2.googleapis.com/token\",
          \"microsoft_token_url\": \"https://login.microsoftonline.com/common/oauth2/v2.0/token\",
          \"triage_high_keywords\": \"urgent,asap,action required,deadline,follow up\",
          \"triage_medium_keywords\": \"review,request,question,update,meeting\",
          \"token_secret\": \"\"
        }
        """.strip(),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config").mkdir()
    defaults_path.replace(tmp_path / "config" / "defaults.json")
    monkeypatch.delenv("INBOXPILOT_DB_PATH", raising=False)
    monkeypatch.delenv("INBOXPILOT_AI_PROVIDER", raising=False)
    config = AppConfig.from_env()
    assert config.db_path == "test.db"
    assert config.ai_provider == "mock"
    assert config.default_user_name == "Local User"
    assert config.default_user_email == "local@inboxpilot"
    assert config.google_client_id == ""
    assert config.google_client_secret == ""
    assert config.microsoft_client_id == ""
    assert config.microsoft_client_secret == ""
    assert config.oauth_redirect_uri == "http://localhost:8000/oauth/callback"
    assert config.google_token_url == "https://oauth2.googleapis.com/token"
    assert config.microsoft_token_url == "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    assert config.triage_high_keywords
    assert config.triage_medium_keywords
    assert config.token_secret == ""
