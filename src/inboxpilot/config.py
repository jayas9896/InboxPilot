"""Summary: Application configuration for InboxPilot.

Importance: Centralizes environment and CLI defaults for consistent behavior.
Alternatives: Use a dedicated settings library like Pydantic Settings.
"""

from __future__ import annotations

import os
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

    @staticmethod
    def from_env() -> "AppConfig":
        """Summary: Build configuration from environment variables.

        Importance: Enables flexible deployment without code changes.
        Alternatives: Parse a local .env file directly in the config layer.
        """

        return AppConfig(
            db_path=os.getenv("INBOXPILOT_DB_PATH", "inboxpilot.db"),
            ai_provider=os.getenv("INBOXPILOT_AI_PROVIDER", "mock"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3"),
            imap_host=os.getenv("INBOXPILOT_IMAP_HOST"),
            imap_user=os.getenv("INBOXPILOT_IMAP_USER"),
            imap_password=os.getenv("INBOXPILOT_IMAP_PASSWORD"),
            imap_mailbox=os.getenv("INBOXPILOT_IMAP_MAILBOX", "INBOX"),
        )
