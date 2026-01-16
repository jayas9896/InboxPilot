"""Summary: Email provider interfaces and implementations.

Importance: Encapsulates read-only ingestion from email services.
Alternatives: Rely solely on provider SDKs with vendor lock-in.
"""

from __future__ import annotations

import imaplib
import json
import re
from abc import ABC, abstractmethod
from datetime import datetime
from email import message_from_bytes
from email.header import decode_header
from pathlib import Path
from typing import Iterable

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
