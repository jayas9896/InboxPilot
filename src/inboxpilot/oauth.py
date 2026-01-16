"""Summary: OAuth helper utilities for provider integrations.

Importance: Generates provider authorization URLs and token exchanges without extra dependencies.
Alternatives: Use provider SDKs for OAuth flows.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
import urllib.parse
import urllib.request

from inboxpilot.config import AppConfig


GOOGLE_SCOPES = "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/calendar.readonly"
MICROSOFT_SCOPES = "offline_access https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/Calendars.Read"


@dataclass(frozen=True)
class OAuthTokenResult:
    """Summary: Normalized OAuth token response data.

    Importance: Provides a consistent token representation for storage and future refresh logic.
    Alternatives: Store the raw provider response without normalization.
    """

    access_token: str
    refresh_token: str | None
    expires_at: str | None
    token_type: str | None
    raw: dict[str, Any]

    @staticmethod
    def from_response(payload: dict[str, Any]) -> "OAuthTokenResult":
        """Summary: Build an OAuthTokenResult from a provider payload.

        Importance: Normalizes expiry and optional fields across providers.
        Alternatives: Use provider-specific token response classes.
        """

        expires_in = payload.get("expires_in")
        expires_at = None
        if isinstance(expires_in, int):
            expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
        return OAuthTokenResult(
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token"),
            expires_at=expires_at,
            token_type=payload.get("token_type"),
            raw=payload,
        )


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
        "scope": GOOGLE_SCOPES,
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
        "scope": MICROSOFT_SCOPES,
        "state": state,
    }
    return "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?" + urllib.parse.urlencode(params)


def exchange_oauth_code(config: AppConfig, provider: str, code: str) -> OAuthTokenResult:
    """Summary: Exchange an OAuth authorization code for tokens.

    Importance: Completes OAuth flows by retrieving access and refresh tokens.
    Alternatives: Use provider SDKs or external auth services.
    """

    token_url = _token_url(config, provider)
    payload = _token_payload(config, provider, code)
    response = _post_form(token_url, payload)
    return OAuthTokenResult.from_response(response)


def _token_url(config: AppConfig, provider: str) -> str:
    """Summary: Resolve the token endpoint for a provider.

    Importance: Keeps token URLs configurable for local and cloud deployments.
    Alternatives: Hardcode token URLs in the exchange function.
    """

    if provider == "google":
        return config.google_token_url
    if provider == "microsoft":
        return config.microsoft_token_url
    raise ValueError(f"Unknown OAuth provider: {provider}")


def _token_payload(config: AppConfig, provider: str, code: str) -> dict[str, str]:
    """Summary: Build token request parameters for OAuth code exchange.

    Importance: Ensures provider-specific payloads include required fields.
    Alternatives: Assemble payloads inline inside the exchange function.
    """

    if provider == "google":
        _ensure_oauth_config(config.google_client_id, config.google_client_secret, provider)
        return {
            "client_id": config.google_client_id,
            "client_secret": config.google_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": config.oauth_redirect_uri,
        }
    if provider == "microsoft":
        _ensure_oauth_config(config.microsoft_client_id, config.microsoft_client_secret, provider)
        return {
            "client_id": config.microsoft_client_id,
            "client_secret": config.microsoft_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": config.oauth_redirect_uri,
            "scope": MICROSOFT_SCOPES,
        }
    raise ValueError(f"Unknown OAuth provider: {provider}")


def _ensure_oauth_config(client_id: str, client_secret: str, provider: str) -> None:
    """Summary: Validate that OAuth credentials exist.

    Importance: Prevents confusing token exchange errors when credentials are missing.
    Alternatives: Allow requests to fail at the provider endpoint.
    """

    if not client_id or not client_secret:
        raise ValueError(f"Missing OAuth client credentials for {provider}")


def _post_form(url: str, payload: dict[str, str]) -> dict[str, Any]:
    """Summary: Send a form-encoded POST request and parse JSON.

    Importance: Avoids new dependencies while supporting OAuth exchanges.
    Alternatives: Use requests or a provider SDK.
    """

    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        raise RuntimeError(f"Token exchange failed: {error_body or exc.reason}") from exc
    return json.loads(raw)
