"""Summary: Email provider interfaces and implementations.

Importance: Encapsulates read-only ingestion from email services.
Alternatives: Rely solely on provider SDKs with vendor lock-in.
"""

from __future__ import annotations

import base64
import imaplib
import json
import re
from abc import ABC, abstractmethod
from datetime import datetime
from email import message_from_bytes
from email.header import decode_header
from pathlib import Path
from typing import Any, Iterable
import urllib.error
import urllib.request

from inboxpilot.models import Message


class EmailProvider(ABC):
    """Summary: Abstract interface for email ingestion.

    Importance: Standardizes retrieval across IMAP and mocked providers.
    Alternatives: Use provider-specific classes directly in ingestion flows.
    """

    @abstractmethod
    def fetch_recent(self, limit: int) -> list[Message]:
        """Summary: Fetch recent messages from the provider.

        Importance: Drives ingestion workflows across providers.
        Alternatives: Fetch messages by cursor or date range instead.
        """


class MockEmailProvider(EmailProvider):
    """Summary: Loads email messages from a local JSON fixture.

    Importance: Supports offline testing and demos.
    Alternatives: Use SQLite fixtures or generate synthetic messages.
    """

    def __init__(self, fixture_path: Path) -> None:
        """Summary: Initialize the mock provider.

        Importance: Allows configurable sample data.
        Alternatives: Hardcode sample data in the class.
        """

        self._fixture_path = fixture_path

    def fetch_recent(self, limit: int) -> list[Message]:
        """Summary: Load recent messages from the fixture file.

        Importance: Provides predictable data for tests and demos.
        Alternatives: Return an empty list when no fixture is present.
        """

        data = json.loads(self._fixture_path.read_text(encoding="utf-8"))
        messages = [
            Message(
                provider_message_id=item["provider_message_id"],
                subject=item["subject"],
                sender=item["sender"],
                recipients=item["recipients"],
                timestamp=datetime.fromisoformat(item["timestamp"]),
                snippet=item["snippet"],
                body=item["body"],
            )
            for item in data
        ]
        return messages[:limit]


class ImapEmailProvider(EmailProvider):
    """Summary: Reads emails from an IMAP server in read-only mode.

    Importance: Provides real-world integration for Gmail/Outlook accounts.
    Alternatives: Use Gmail or Microsoft Graph APIs instead of IMAP.
    """

    def __init__(self, host: str, user: str, password: str, mailbox: str) -> None:
        """Summary: Initialize the IMAP provider.

        Importance: Stores connection details for read-only ingestion.
        Alternatives: Use OAuth tokens instead of password auth.
        """

        self._host = host
        self._user = user
        self._password = password
        self._mailbox = mailbox

    def fetch_recent(self, limit: int) -> list[Message]:
        """Summary: Fetch recent messages via IMAP.

        Importance: Supports ingestion without sending emails.
        Alternatives: Fetch by UID ranges or search queries.
        """

        with imaplib.IMAP4_SSL(self._host) as client:
            client.login(self._user, self._password)
            client.select(self._mailbox, readonly=True)
            status, data = client.search(None, "ALL")
            if status != "OK":
                raise RuntimeError("IMAP search failed")
            message_ids = data[0].split()
            recent_ids = message_ids[-limit:]
            messages = [self._fetch_message(client, message_id) for message_id in recent_ids]
            return [message for message in messages if message is not None]

    def _fetch_message(self, client: imaplib.IMAP4_SSL, message_id: bytes) -> Message | None:
        """Summary: Fetch and parse a single message.

        Importance: Extracts metadata and body for storage.
        Alternatives: Skip body parsing for faster ingestion.
        """

        status, data = client.fetch(message_id, "(RFC822)")
        if status != "OK":
            return None
        raw_email = data[0][1]
        message = message_from_bytes(raw_email)
        subject = _decode_header_value(message.get("Subject", ""))
        sender = _decode_header_value(message.get("From", ""))
        recipients = _decode_header_value(message.get("To", ""))
        date_raw = message.get("Date", "")
        timestamp = _parse_date(date_raw)
        body = _extract_body(message)
        snippet = body[:200].replace("\n", " ")
        provider_message_id = message.get("Message-Id", message_id.decode("utf-8"))
        return Message(
            provider_message_id=provider_message_id,
            subject=subject,
            sender=sender,
            recipients=recipients,
            timestamp=timestamp,
            snippet=snippet,
            body=body,
        )


class GmailEmailProvider(EmailProvider):
    """Summary: Reads emails via the Gmail API using OAuth tokens.

    Importance: Enables OAuth-based ingestion without IMAP passwords.
    Alternatives: Use IMAP or a provider SDK.
    """

    def __init__(self, access_token: str, base_url: str) -> None:
        """Summary: Initialize the Gmail provider.

        Importance: Stores access token and API base URL for requests.
        Alternatives: Fetch tokens on demand inside each request.
        """

        self._access_token = access_token
        self._base_url = base_url.rstrip("/")

    def fetch_recent(self, limit: int) -> list[Message]:
        """Summary: Fetch recent Gmail messages using the API.

        Importance: Provides OAuth-based read-only ingestion.
        Alternatives: Use provider sync APIs or push notifications.
        """

        list_url = f"{self._base_url}/users/me/messages?maxResults={limit}"
        payload = _gmail_api_get(list_url, self._access_token)
        messages: list[Message] = []
        for item in payload.get("messages", []):
            message_id = item.get("id")
            if not message_id:
                continue
            detail_url = f"{self._base_url}/users/me/messages/{message_id}?format=full"
            message_payload = _gmail_api_get(detail_url, self._access_token)
            parsed = _parse_gmail_message(message_payload)
            if parsed:
                messages.append(parsed)
        return messages


def _gmail_api_get(url: str, access_token: str) -> dict[str, Any]:
    """Summary: Fetch JSON data from the Gmail API.

    Importance: Encapsulates Gmail API calls without new dependencies.
    Alternatives: Use a third-party HTTP client or SDK.
    """

    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        raise RuntimeError(f"Gmail API request failed: {error_body or exc.reason}") from exc
    return json.loads(raw)


def _parse_gmail_message(message: dict[str, Any]) -> Message | None:
    """Summary: Parse a Gmail message payload into a Message.

    Importance: Normalizes Gmail payloads into the core message model.
    Alternatives: Store raw Gmail payloads and parse later.
    """

    payload = message.get("payload") or {}
    headers = _parse_gmail_headers(payload.get("headers", []))
    subject = headers.get("Subject", "")
    sender = headers.get("From", "")
    recipients = headers.get("To", "")
    date_raw = headers.get("Date", "")
    internal_date = message.get("internalDate")
    if internal_date:
        try:
            timestamp = datetime.fromtimestamp(int(internal_date) / 1000)
        except ValueError:
            timestamp = _parse_date(date_raw)
    else:
        timestamp = _parse_date(date_raw)
    body = _extract_gmail_body(payload)
    snippet = message.get("snippet", "")
    if not snippet:
        snippet = body[:200].replace("\n", " ") if body else ""
    provider_message_id = message.get("id", "")
    return Message(
        provider_message_id=provider_message_id,
        subject=subject,
        sender=sender,
        recipients=recipients,
        timestamp=timestamp,
        snippet=snippet,
        body=body or snippet,
    )


def _parse_gmail_headers(headers: list[dict[str, Any]]) -> dict[str, str]:
    """Summary: Normalize Gmail header list into a dictionary.

    Importance: Simplifies access to header values for parsing.
    Alternatives: Scan header lists inline for each field.
    """

    normalized: dict[str, str] = {}
    for header in headers:
        name = header.get("name")
        value = header.get("value")
        if name and value:
            normalized[name] = value
    return normalized


def _extract_gmail_body(payload: dict[str, Any]) -> str:
    """Summary: Extract a plain text body from a Gmail payload.

    Importance: Provides readable content for summarization and drafting.
    Alternatives: Store the snippet only for Gmail messages.
    """

    text_parts: list[str] = []
    fallback_parts: list[str] = []
    for part in _walk_gmail_parts(payload):
        mime_type = part.get("mimeType")
        body = part.get("body", {})
        data = body.get("data")
        if not data:
            continue
        decoded = _decode_base64url(data)
        if mime_type == "text/plain":
            text_parts.append(decoded)
        else:
            fallback_parts.append(decoded)
    if text_parts:
        return "
".join(item.strip() for item in text_parts if item.strip()).strip()
    if fallback_parts:
        return "
".join(item.strip() for item in fallback_parts if item.strip()).strip()
    return ""


def _walk_gmail_parts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Summary: Walk Gmail payload parts recursively.

    Importance: Supports nested multipart payloads from Gmail.
    Alternatives: Only inspect the top-level payload.
    """

    parts: list[dict[str, Any]] = [payload]
    for part in payload.get("parts", []) or []:
        parts.extend(_walk_gmail_parts(part))
    return parts


def _decode_base64url(data: str) -> str:
    """Summary: Decode base64url-encoded Gmail content.

    Importance: Gmail payloads use URL-safe base64 encoding.
    Alternatives: Use a third-party Gmail client library.
    """

    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8", errors="ignore")


class OutlookEmailProvider(EmailProvider):
    """Summary: Reads emails via Microsoft Graph using OAuth tokens.

    Importance: Enables OAuth-based Outlook ingestion without IMAP passwords.
    Alternatives: Use IMAP or a provider SDK.
    """

    def __init__(self, access_token: str, base_url: str) -> None:
        """Summary: Initialize the Outlook provider.

        Importance: Stores access token and base URL for Graph requests.
        Alternatives: Fetch tokens on demand inside each request.
        """

        self._access_token = access_token
        self._base_url = base_url.rstrip("/")

    def fetch_recent(self, limit: int) -> list[Message]:
        """Summary: Fetch recent Outlook messages using Microsoft Graph.

        Importance: Provides OAuth-based read-only ingestion.
        Alternatives: Use provider sync APIs or delta queries.
        """

        list_url = (
            f"{self._base_url}/me/messages?"
            f"$top={limit}&$select=id,subject,from,toRecipients,bodyPreview,body,receivedDateTime"
        )
        payload = _graph_api_get(list_url, self._access_token)
        messages: list[Message] = []
        for item in payload.get("value", []):
            parsed = _parse_outlook_message(item)
            if parsed:
                messages.append(parsed)
        return messages


def _graph_api_get(url: str, access_token: str) -> dict[str, Any]:
    """Summary: Fetch JSON data from Microsoft Graph.

    Importance: Encapsulates Graph API calls without new dependencies.
    Alternatives: Use a third-party HTTP client or SDK.
    """

    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        raise RuntimeError(f"Microsoft Graph request failed: {error_body or exc.reason}") from exc
    return json.loads(raw)


def _parse_outlook_message(message: dict[str, Any]) -> Message | None:
    """Summary: Parse a Microsoft Graph message payload into a Message.

    Importance: Normalizes Outlook payloads into the core message model.
    Alternatives: Store raw Outlook payloads and parse later.
    """

    message_id = message.get("id", "")
    subject = message.get("subject", "")
    sender = (message.get("from") or {}).get("emailAddress", {}).get("address", "")
    recipients = normalize_recipients(
        [
            item.get("emailAddress", {}).get("address", "")
            for item in message.get("toRecipients", [])
        ]
    )
    received = message.get("receivedDateTime")
    timestamp = _parse_iso_datetime(received)
    body_preview = message.get("bodyPreview", "")
    body_info = message.get("body") or {}
    if body_info.get("contentType", "").lower() == "text" and body_info.get("content"):
        body = body_info["content"]
    else:
        body = body_preview
    snippet = body_preview or (body[:200].replace("
", " ") if body else "")
    return Message(
        provider_message_id=message_id,
        subject=subject,
        sender=sender,
        recipients=recipients,
        timestamp=timestamp,
        snippet=snippet,
        body=body or snippet,
    )


def _parse_iso_datetime(value: str | None) -> datetime:
    """Summary: Parse ISO datetime strings from Graph payloads.

    Importance: Normalizes timestamps for sorting and filtering.
    Alternatives: Store raw timestamp strings in the database.
    """

    if not value:
        return datetime.utcnow()
    cleaned = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return datetime.utcnow()



def _decode_header_value(value: str) -> str:
    """Summary: Decode encoded email header values.

    Importance: Ensures metadata is readable in storage and UI.
    Alternatives: Store raw header values and decode at display time.
    """

    decoded_parts = decode_header(value)
    fragments: list[str] = []
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            fragments.append(part.decode(encoding or "utf-8", errors="ignore"))
        else:
            fragments.append(part)
    return "".join(fragments).strip()


def _extract_body(message: object) -> str:
    """Summary: Extract a plaintext body from an email message.

    Importance: Provides content for summarization and draft context.
    Alternatives: Store only HTML or raw MIME without parsing.
    """

    if message.is_multipart():
        parts = []
        for part in message.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True) or b""
                parts.append(payload.decode(part.get_content_charset() or "utf-8", errors="ignore"))
        return "\n".join(parts).strip()
    payload = message.get_payload(decode=True) or b""
    return payload.decode(message.get_content_charset() or "utf-8", errors="ignore").strip()


def _parse_date(raw_date: str) -> datetime:
    """Summary: Parse an email date into a datetime.

    Importance: Normalizes timestamps for sorting and filtering.
    Alternatives: Store raw strings and parse on demand.
    """

    cleaned = re.sub(r"\(.*?\)", "", raw_date).strip()
    try:
        return datetime.strptime(cleaned[:25], "%a, %d %b %Y %H:%M:%S")
    except ValueError:
        return datetime.utcnow()


def normalize_recipients(recipients: Iterable[str]) -> str:
    """Summary: Normalize recipients into a comma-separated string.

    Importance: Simplifies storage of email address lists.
    Alternatives: Store recipients in a separate table.
    """

    return ", ".join(recipients)


class EmlEmailProvider(EmailProvider):
    """Summary: Loads email messages from .eml files.

    Importance: Supports local email ingestion without provider APIs.
    Alternatives: Use IMAP or provider-specific APIs only.
    """

    def __init__(self, eml_paths: list[Path]) -> None:
        """Summary: Initialize with a list of .eml file paths.

        Importance: Enables batch ingestion of exported emails.
        Alternatives: Read from a directory and glob files internally.
        """

        self._eml_paths = eml_paths

    def fetch_recent(self, limit: int) -> list[Message]:
        """Summary: Parse .eml files into Message objects.

        Importance: Allows local-first ingestion of exported emails.
        Alternatives: Skip body parsing for faster ingestion.
        """

        messages: list[Message] = []
        for path in self._eml_paths[:limit]:
            raw_email = path.read_bytes()
            message = message_from_bytes(raw_email)
            subject = _decode_header_value(message.get("Subject", ""))
            sender = _decode_header_value(message.get("From", ""))
            recipients = _decode_header_value(message.get("To", ""))
            date_raw = message.get("Date", "")
            timestamp = _parse_date(date_raw)
            body = _extract_body(message)
            snippet = body[:200].replace("\n", " ")
            provider_message_id = message.get("Message-Id", path.name)
            messages.append(
                Message(
                    provider_message_id=provider_message_id,
                    subject=subject,
                    sender=sender,
                    recipients=recipients,
                    timestamp=timestamp,
                    snippet=snippet,
                    body=body,
                )
            )
        return messages
