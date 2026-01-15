"""Summary: Domain model dataclasses for InboxPilot.

Importance: Defines the core entities shared across services and storage.
Alternatives: Use Pydantic models or ORM classes directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Message:
    """Summary: Represents an email message with metadata and content.

    Importance: Core unit for ingestion, categorization, and drafting workflows.
    Alternatives: Model only threads and store messages as embedded records.
    """

    provider_message_id: str
    subject: str
    sender: str
    recipients: str
    timestamp: datetime
    snippet: str
    body: str


@dataclass(frozen=True)
class Category:
    """Summary: Represents a user-defined category.

    Importance: Categories drive customization and organization across workflows.
    Alternatives: Use fixed system labels with limited user customization.
    """

    name: str
    description: str | None = None


@dataclass(frozen=True)
class Meeting:
    """Summary: Represents a calendar meeting or event.

    Importance: Enables meeting ingestion and note workflows alongside email.
    Alternatives: Store meetings as raw calendar provider payloads.
    """

    provider_event_id: str
    title: str
    participants: str
    start_time: datetime
    end_time: datetime
    transcript_ref: str | None = None


@dataclass(frozen=True)
class Note:
    """Summary: Represents a note linked to a message or meeting.

    Importance: Captures user context and action items outside raw messages.
    Alternatives: Store notes inside the message body or as AI-generated summaries.
    """

    parent_type: str
    parent_id: int
    content: str


@dataclass(frozen=True)
class AiRequest:
    """Summary: Records an AI request for audit and traceability.

    Importance: Provides visibility into prompts and provider usage.
    Alternatives: Log requests only in observability logs.
    """

    provider: str
    model: str
    prompt: str
    purpose: str
    timestamp: datetime


@dataclass(frozen=True)
class AiResponse:
    """Summary: Records an AI response paired to a request.

    Importance: Enables audit trails and future tuning based on outputs.
    Alternatives: Store only final outputs in the message or note records.
    """

    request_id: int
    response_text: str
    latency_ms: int
    token_estimate: int
