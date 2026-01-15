"""Summary: Core application services for InboxPilot.

Importance: Orchestrates ingestion, categorization, and AI-driven chat flows.
Alternatives: Build a full service layer with dependency injection framework.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from inboxpilot.ai import AiProvider, estimate_tokens
from inboxpilot.classifier import RuleBasedClassifier
from inboxpilot.models import AiRequest, AiResponse, Category, Message, Note
from inboxpilot.storage.sqlite_store import SqliteStore, StoredMessage


@dataclass(frozen=True)
class IngestionService:
    """Summary: Handles ingestion of messages from providers.

    Importance: Centralizes ingestion logic for consistent storage behavior.
    Alternatives: Ingest directly inside CLI commands.
    """

    store: SqliteStore

    def ingest_messages(self, messages: list[Message]) -> list[int]:
        """Summary: Persist incoming messages in storage.

        Importance: Normalizes ingestion across providers.
        Alternatives: Use a queue-based ingestion pipeline.
        """

        return self.store.save_messages(messages)


@dataclass(frozen=True)
class CategoryService:
    """Summary: Manages category creation and assignment.

    Importance: Ensures categories remain first-class objects.
    Alternatives: Use implicit labels with no management workflow.
    """

    store: SqliteStore
    classifier: RuleBasedClassifier

    def create_category(self, name: str, description: str | None) -> int:
        """Summary: Create a new category record.

        Importance: Enables user-defined organization.
        Alternatives: Auto-create categories on demand from AI output.
        """

        category = Category(name=name, description=description)
        return self.store.create_category(category)

    def suggest_categories(self, message: Message) -> list[Category]:
        """Summary: Suggest categories for a message.

        Importance: Supports automatic triage and inbox organization.
        Alternatives: Require manual assignment for every message.
        """

        categories = [
            Category(name=item.name, description=item.description) for item in self.store.list_categories()
        ]
        return self.classifier.suggest(message, categories)

    def assign_category(self, message_id: int, category_id: int) -> None:
        """Summary: Assign a category to a stored message.

        Importance: Links messages to user-defined categories.
        Alternatives: Update message rows directly with category IDs.
        """

        self.store.assign_category(message_id, category_id)


@dataclass(frozen=True)
class ChatService:
    """Summary: Provides AI-assisted chat and drafting features.

    Importance: Central user experience for search and reply drafting.
    Alternatives: Expose AI directly in the CLI without service mediation.
    """

    store: SqliteStore
    ai_provider: AiProvider
    provider_name: str
    model_name: str

    def answer(self, query: str, limit: int = 3) -> str:
        """Summary: Answer a question using message context.

        Importance: Enables chat-style exploration of the inbox.
        Alternatives: Return search results without AI summarization.
        """

        messages = self.store.search_messages(query, limit)
        context = "\n\n".join(self._format_message(message) for message in messages)
        prompt = (
            "Answer the user question using the message context.\n\n"
            f"Question: {query}\n\n"
            f"Messages:\n{context}\n"
        )
        response_text, latency_ms = self.ai_provider.generate_text(prompt, purpose="answer")
        self._log_ai(prompt, "answer", response_text, latency_ms)
        return response_text

    def draft_reply(self, message_id: int, instructions: str) -> str:
        """Summary: Draft a reply for a specific message.

        Importance: Keeps the system draft-first with explicit user control.
        Alternatives: Auto-send replies based on inferred intent.
        """

        message = self._get_message(message_id)
        prompt = (
            "Draft a helpful reply. Do not send the email.\n\n"
            f"Email from: {message.sender}\n"
            f"Subject: {message.subject}\n"
            f"Body: {message.body}\n\n"
            f"User instructions: {instructions}\n"
        )
        response_text, latency_ms = self.ai_provider.generate_text(prompt, purpose="draft")
        self._log_ai(prompt, "draft", response_text, latency_ms)
        return response_text

    def add_note(self, parent_type: str, parent_id: int, content: str) -> int:
        """Summary: Add a note for a message or meeting.

        Importance: Captures action items and context for follow-ups.
        Alternatives: Store notes in a separate note-taking app.
        """

        note = Note(parent_type=parent_type, parent_id=parent_id, content=content)
        return self.store.add_note(note)

    def _get_message(self, message_id: int) -> StoredMessage:
        """Summary: Retrieve a single message by ID.

        Importance: Ensures drafts reference existing stored messages.
        Alternatives: Search by provider message ID instead.
        """

        messages = [message for message in self.store.list_messages(200) if message.id == message_id]
        if not messages:
            raise ValueError(f"Message {message_id} not found")
        return messages[0]

    def _format_message(self, message: StoredMessage) -> str:
        """Summary: Format a stored message for AI context.

        Importance: Keeps prompts consistent and readable.
        Alternatives: Include full raw email headers.
        """

        return (
            f"ID: {message.id}\n"
            f"From: {message.sender}\n"
            f"Subject: {message.subject}\n"
            f"Snippet: {message.snippet}\n"
        )

    def _log_ai(self, prompt: str, purpose: str, response_text: str, latency_ms: int) -> None:
        """Summary: Store AI request and response metadata.

        Importance: Provides auditability for AI usage.
        Alternatives: Rely solely on logs without persistence.
        """

        request = AiRequest(
            provider=self.provider_name,
            model=self.model_name,
            prompt=prompt,
            purpose=purpose,
            timestamp=datetime.utcnow(),
        )
        request_id = self.store.log_ai_request(request)
        response = AiResponse(
            request_id=request_id,
            response_text=response_text,
            latency_ms=latency_ms,
            token_estimate=estimate_tokens(response_text),
        )
        self.store.log_ai_response(response)
