"""Summary: OAuth helper utilities for provider integrations.

Importance: Generates provider authorization URLs without extra dependencies.
Alternatives: Use provider SDKs for OAuth flows.
"""

from __future__ import annotations

import secrets
import urllib.parse

from inboxpilot.config import AppConfig


def create_state_token() -> str:
    """Summary: Generate a CSRF state token.

    Importance: Protects OAuth flows from CSRF attacks.
    Alternatives: Use server-side session storage with pre-generated tokens.
    """

    return secrets.token_urlsafe(24)


def build_google_auth_url(config: AppConfig, state: str) -> str:
    """Summary: Build a Google OAuth authorization URL.

    Importance: Enables read-only Gmail and Calendar authorization.
    Alternatives: Use a different OAuth helper library.
    """

    params = {
        "client_id": config.google_client_id,
        "redirect_uri": config.oauth_redirect_uri,
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
        "scope": "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/calendar.readonly",
        "state": state,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)


def build_microsoft_auth_url(config: AppConfig, state: str) -> str:
    """Summary: Build a Microsoft OAuth authorization URL.

    Importance: Enables Outlook and Calendar authorization.
    Alternatives: Use Microsoft Graph SDK helpers.
    """

    params = {
        "client_id": config.microsoft_client_id,
        "redirect_uri": config.oauth_redirect_uri,
        "response_type": "code",
        "response_mode": "query",
        "scope": "offline_access https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/Calendars.Read",
        "state": state,
    }
    return "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?" + urllib.parse.urlencode(params)
