"""Summary: Application configuration for InboxPilot.

Importance: Centralizes environment, .env, and config defaults for consistent behavior.
Alternatives: Use a dedicated settings library like Pydantic Settings.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """Summary: Holds configuration values for providers and storage.

    Importance: Ensures all services derive settings from a single source of truth.
    Alternatives: Store settings in a shared config file and parse at startup.
    """

    db_path: str
    ai_provider: str
    openai_api_key: str | None
    openai_model: str
    ollama_url: str
    ollama_model: str
    imap_host: str | None
    imap_user: str | None
    imap_password: str | None
    imap_mailbox: str
    api_host: str
    api_port: int
    default_user_name: str
    default_user_email: str
    api_key: str
    google_client_id: str
    google_client_secret: str
    microsoft_client_id: str
    microsoft_client_secret: str
    oauth_redirect_uri: str

    @staticmethod
    def from_env() -> "AppConfig":
        """Summary: Build configuration from defaults, .env, and environment.

        Importance: Keeps all variables defined in config defaults while allowing overrides.
        Alternatives: Parse only environment variables without a defaults file.
        """

        defaults = load_defaults(Path("config") / "defaults.json")
        load_dotenv(Path(".env"))
        return AppConfig(
            db_path=os.getenv("INBOXPILOT_DB_PATH", defaults["db_path"]),
            ai_provider=os.getenv("INBOXPILOT_AI_PROVIDER", defaults["ai_provider"]),
            openai_api_key=os.getenv("OPENAI_API_KEY") or defaults["openai_api_key"] or None,
            openai_model=os.getenv("OPENAI_MODEL", defaults["openai_model"]),
            ollama_url=os.getenv("OLLAMA_URL", defaults["ollama_url"]),
            ollama_model=os.getenv("OLLAMA_MODEL", defaults["ollama_model"]),
            imap_host=os.getenv("INBOXPILOT_IMAP_HOST") or defaults["imap_host"] or None,
            imap_user=os.getenv("INBOXPILOT_IMAP_USER") or defaults["imap_user"] or None,
            imap_password=os.getenv("INBOXPILOT_IMAP_PASSWORD") or defaults["imap_password"] or None,
            imap_mailbox=os.getenv("INBOXPILOT_IMAP_MAILBOX", defaults["imap_mailbox"]),
            api_host=os.getenv("INBOXPILOT_API_HOST", defaults["api_host"]),
            api_port=int(os.getenv("INBOXPILOT_API_PORT", defaults["api_port"])),
            default_user_name=os.getenv(
                "INBOXPILOT_DEFAULT_USER_NAME", defaults["default_user_name"]
            ),
            default_user_email=os.getenv(
                "INBOXPILOT_DEFAULT_USER_EMAIL", defaults["default_user_email"]
            ),
            api_key=os.getenv("INBOXPILOT_API_KEY", defaults["api_key"]),
            google_client_id=os.getenv("GOOGLE_CLIENT_ID", defaults["google_client_id"]),
            google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET", defaults["google_client_secret"]),
            microsoft_client_id=os.getenv("MICROSOFT_CLIENT_ID", defaults["microsoft_client_id"]),
            microsoft_client_secret=os.getenv(
                "MICROSOFT_CLIENT_SECRET", defaults["microsoft_client_secret"]
            ),
            oauth_redirect_uri=os.getenv(
                "INBOXPILOT_OAUTH_REDIRECT_URI", defaults["oauth_redirect_uri"]
            ),
        )


def load_defaults(path: Path) -> dict[str, str]:
    """Summary: Load configuration defaults from JSON.

    Importance: Ensures all variables exist in a single config file.
    Alternatives: Inline defaults in the AppConfig initializer.
    """

    if not path.exists():
        raise FileNotFoundError(f"Defaults file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_dotenv(path: Path) -> None:
    """Summary: Load key-value pairs from a .env file into the environment.

    Importance: Keeps secrets out of code while supporting local workflows.
    Alternatives: Use python-dotenv or OS-specific secret stores.
    """

    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())
