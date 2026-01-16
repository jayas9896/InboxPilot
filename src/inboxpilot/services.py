"""Summary: Core application services for InboxPilot.

Importance: Orchestrates ingestion, categorization, and AI-driven chat flows.
Alternatives: Build a full service layer with dependency injection framework.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import secrets
import hashlib
from datetime import datetime, timedelta

from inboxpilot.ai import AiProvider, estimate_tokens
from inboxpilot.config import AppConfig
from inboxpilot.oauth import refresh_oauth_token
from inboxpilot.classifier import RuleBasedClassifier
from inboxpilot.models import (
    AiRequest,
    AiResponse,
    Category,
    Connection,
    Meeting,
    Message,
    Note,
    Task,
)
from inboxpilot.storage.sqlite_store import (
    SqliteStore,
    StoredApiKey,
    StoredConnection,
    StoredMeeting,
    StoredMessage,
    StoredTask,
    StoredUser,
)
from inboxpilot.token_codec import TokenCodec


logger = logging.getLogger(__name__)



@dataclass(frozen=True)
class UserService:
    """Summary: Manages user records for multi-user workflows.

    Importance: Provides user creation and lookup for per-user auth.
    Alternatives: Use an external identity provider.
    """

    store: SqliteStore

    def create_user(self, display_name: str, email: str) -> int:
        """Summary: Create or ensure a user exists.

        Importance: Allows onboarding multiple users without a schema rewrite.
        Alternatives: Keep a single hardcoded user.
        """

        return self.store.ensure_user(User(display_name=display_name, email=email))

    def list_users(self) -> list[StoredUser]:
        """Summary: List all users.

        Importance: Supports admin user management.
        Alternatives: Store users externally.
        """

        return self.store.list_users()

    def get_user_by_email(self, email: str) -> StoredUser | None:
        """Summary: Fetch a user by email.

        Importance: Enables resolving users for API key issuance.
        Alternatives: Use user IDs only.
        """

        return self.store.get_user_by_email(email)


@dataclass(frozen=True)
class ApiKeyService:
    """Summary: Issues and verifies API keys for users.

    Importance: Enables per-user API authentication tokens.
    Alternatives: Use OAuth or an external auth service.
    """

    store: SqliteStore
    token_secret: str

    def create_api_key(self, user_id: int, label: str | None = None) -> tuple[int, str]:
        """Summary: Create a new API key for a user.

        Importance: Returns a one-time plaintext token for client storage.
        Alternatives: Store raw tokens in the database.
        """

        raw_token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(raw_token)
        key_id = self.store.create_api_key(
            user_id=user_id,
            token_hash=token_hash,
            label=label,
            created_at=datetime.utcnow().isoformat(),
        )
        return key_id, raw_token

    def revoke_api_key(self, user_id: int, key_id: int) -> bool:
        """Summary: Revoke an API key for a user.

        Importance: Allows invalidating compromised keys.
        Alternatives: Rotate keys by issuing replacements only.
        """

        return self.store.delete_api_key(user_id, key_id)

    def list_api_keys(self, user_id: int) -> list[StoredApiKey]:
        """Summary: List API keys for a user.

        Importance: Supports key rotation and auditing.
        Alternatives: Store keys externally.
        """

        return self.store.list_api_keys(user_id)

    def resolve_user_id(self, token: str) -> int | None:
        """Summary: Resolve a user ID from an API key.

        Importance: Supports per-user API authentication.
        Alternatives: Validate tokens with an external service.
        """

        token_hash = self._hash_token(token)
        return self.store.get_user_id_by_api_key(token_hash)

    def _hash_token(self, token: str) -> str:
        """Summary: Hash an API token with a secret salt.

        Importance: Avoids storing raw API keys in the database.
        Alternatives: Use an HSM or external secrets manager.
        """

        salt = self.token_secret or "inboxpilot"
        digest = hashlib.sha256(f"{salt}:{token}".encode("utf-8")).hexdigest()
        return digest


@dataclass(frozen=True)
class IngestionService:
    """Summary: Handles ingestion of messages from providers.

    Importance: Centralizes ingestion logic for consistent storage behavior.
    Alternatives: Ingest directly inside CLI commands.
    """

    store: SqliteStore
    user_id: int

    def ingest_messages(self, messages: list[Message]) -> list[int]:
        """Summary: Persist incoming messages in storage.

        Importance: Normalizes ingestion across providers.
        Alternatives: Use a queue-based ingestion pipeline.
        """

        ids = self.store.save_messages(messages, user_id=self.user_id)
        logger.info("Ingested %s messages.", len(ids))
        return ids


@dataclass(frozen=True)
class MeetingService:
    """Summary: Handles ingestion and listing of meetings.

    Importance: Keeps meeting workflows consistent with email ingestion.
    Alternatives: Treat meetings as a separate service outside the MVP.
    """

    store: SqliteStore
    user_id: int

    def ingest_meetings(self, meetings: list[Meeting]) -> list[int]:
        """Summary: Persist incoming meetings in storage.

        Importance: Normalizes meeting ingestion across providers.
        Alternatives: Store meetings only in memory for each session.
        """

        ids = self.store.save_meetings(meetings, user_id=self.user_id)
        logger.info("Ingested %s meetings.", len(ids))
        return ids

    def list_meetings(self, limit: int) -> list[StoredMeeting]:
        """Summary: Return recent meetings from storage.

        Importance: Supports CLI listing and note workflows.
        Alternatives: Query meetings directly from the provider each time.
        """

        return self.store.list_meetings(limit, user_id=self.user_id)


@dataclass(frozen=True)
class CategoryService:
    """Summary: Manages category creation and assignment.

    Importance: Ensures categories remain first-class objects.
    Alternatives: Use implicit labels with no management workflow.
    """

    store: SqliteStore
    classifier: RuleBasedClassifier
    ai_provider: AiProvider
    provider_name: str
    model_name: str
    user_id: int

    def create_category(self, name: str, description: str | None) -> int:
        """Summary: Create a new category record.

        Importance: Enables user-defined organization.
        Alternatives: Auto-create categories on demand from AI output.
        """

        category = Category(name=name, description=description)
        category_id = self.store.create_category(category, user_id=self.user_id)
        logger.info("Created category %s.", name)
        return category_id

    def suggest_categories(self, message: Message) -> list[Category]:
        """Summary: Suggest categories for a message.

        Importance: Supports automatic triage and inbox organization.
        Alternatives: Require manual assignment for every message.
        """

        categories = [
            Category(name=item.name, description=item.description)
            for item in self.store.list_categories(user_id=self.user_id)
        ]
        return self.classifier.suggest(message, categories)

    def suggest_categories_ai(self, message_id: int) -> list[Category]:
        """Summary: Suggest categories using AI for a stored message.

        Importance: Provides a flexible categorization option beyond keyword rules.
        Alternatives: Use only deterministic rules or manual assignment.
        """

        message = self.store.get_message(message_id, user_id=self.user_id)
        if not message:
            raise ValueError(f"Message {message_id} not found")
        stored_categories = self.store.list_categories(user_id=self.user_id)
        categories = [
            Category(name=item.name, description=item.description) for item in stored_categories
        ]
        if not categories:
            return []
        category_list = "\n".join(f"- {category.name}" for category in categories)
        prompt = (
            "Select the most relevant categories for the email. "
            "Respond with one category name per line from the provided list.\n\n"
            f"Available categories:\n{category_list}\n\n"
            f"Email subject: {message.subject}\n"
            f"Email body: {message.body}\n"
        )
        response_text, latency_ms = self.ai_provider.generate_text(
            prompt, purpose="category_suggestion"
        )
        request = AiRequest(
            provider=self.provider_name,
            model=self.model_name,
            prompt=prompt,
            purpose="category_suggestion",
            timestamp=datetime.utcnow(),
        )
        request_id = self.store.log_ai_request(request, user_id=self.user_id)
        response = AiResponse(
            request_id=request_id,
            response_text=response_text,
            latency_ms=latency_ms,
            token_estimate=estimate_tokens(response_text),
        )
        self.store.log_ai_response(response)
        normalized = {category.name.lower(): category for category in categories}
        suggestions: list[Category] = []
        for line in response_text.splitlines():
            cleaned = line.strip().lstrip("-").strip().lower()
            if cleaned in normalized:
                suggestions.append(normalized[cleaned])
        if suggestions:
            return suggestions
        return self.classifier.suggest(
            Message(
                provider_message_id=message.provider_message_id,
                subject=message.subject,
                sender=message.sender,
                recipients=message.recipients,
                timestamp=datetime.fromisoformat(message.timestamp),
                snippet=message.snippet,
                body=message.body,
            ),
            categories,
        )

    def assign_category(self, message_id: int, category_id: int) -> None:
        """Summary: Assign a category to a stored message.

        Importance: Links messages to user-defined categories.
        Alternatives: Update message rows directly with category IDs.
        """

        self.store.assign_category(message_id, category_id)
        logger.info("Assigned category %s to message %s.", category_id, message_id)


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
    user_id: int
    user_id: int
    user_id: int

    def answer(self, query: str, limit: int = 3) -> str:
        """Summary: Answer a question using message context.

        Importance: Enables chat-style exploration of the inbox.
        Alternatives: Return search results without AI summarization.
        """

        messages = self.store.search_messages(query, limit, user_id=self.user_id)
        meetings = self.store.search_meetings(query, limit, user_id=self.user_id)
        message_context = "\n\n".join(self._format_message(message) for message in messages)
        meeting_context = "\n\n".join(self._format_meeting(meeting) for meeting in meetings)
        context = "\n\n".join(
            [section for section in [message_context, meeting_context] if section]
        )
        prompt = (
            "Answer the user question using the message and meeting context.\n\n"
            f"Question: {query}\n\n"
            f"Context:\n{context}\n"
        )
        response_text, latency_ms = self.ai_provider.generate_text(prompt, purpose="answer")
        self._log_ai(prompt, "answer", response_text, latency_ms)
        logger.info("Answered chat query.")
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
        logger.info("Drafted reply for message %s.", message_id)
        return response_text

    def add_note(self, parent_type: str, parent_id: int, content: str) -> int:
        """Summary: Add a note for a message or meeting.

        Importance: Captures action items and context for follow-ups.
        Alternatives: Store notes in a separate note-taking app.
        """

        note = Note(parent_type=parent_type, parent_id=parent_id, content=content)
        note_id = self.store.add_note(note, user_id=self.user_id)
        logger.info("Added note for %s %s.", parent_type, parent_id)
        return note_id

    def _get_message(self, message_id: int) -> StoredMessage:
        """Summary: Retrieve a single message by ID.

        Importance: Ensures drafts reference existing stored messages.
        Alternatives: Search by provider message ID instead.
        """

        message = self.store.get_message(message_id, user_id=self.user_id)
        if not message:
            raise ValueError(f"Message {message_id} not found")
        return message

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

    def _format_meeting(self, meeting: StoredMeeting) -> str:
        """Summary: Format a stored meeting for AI context.

        Importance: Allows chat to answer questions about meetings.
        Alternatives: Exclude meetings from chat context.
        """

        return (
            f"MEETING ID: {meeting.id}\n"
            f"Title: {meeting.title}\n"
            f"Participants: {meeting.participants}\n"
            f"Start: {meeting.start_time}\n"
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
        request_id = self.store.log_ai_request(request, user_id=self.user_id)
        response = AiResponse(
            request_id=request_id,
            response_text=response_text,
            latency_ms=latency_ms,
            token_estimate=estimate_tokens(response_text),
        )
        self.store.log_ai_response(response)


@dataclass(frozen=True)
class MessageInsightsService:
    """Summary: Provides summaries and follow-up suggestions for messages.

    Importance: Enables explainability and follow-up guidance for inbox workflows.
    Alternatives: Use ChatService only or rely on manual review.
    """

    store: SqliteStore
    ai_provider: AiProvider
    provider_name: str
    model_name: str
    user_id: int

    def summarize_message(self, message_id: int) -> int:
        """Summary: Summarize a message and store it as a note.

        Importance: Captures concise context for future review and follow-ups.
        Alternatives: Require users to add notes manually.
        """

        message = self.store.get_message(message_id, user_id=self.user_id)
        if not message:
            raise ValueError(f"Message {message_id} not found")
        prompt = (
            "Summarize the email with key points and any requested actions.\n\n"
            f"From: {message.sender}\n"
            f"Subject: {message.subject}\n"
            f"Body: {message.body}\n"
        )
        response_text, latency_ms = self.ai_provider.generate_text(
            prompt, purpose="message_summary"
        )
        request = AiRequest(
            provider=self.provider_name,
            model=self.model_name,
            prompt=prompt,
            purpose="message_summary",
            timestamp=datetime.utcnow(),
        )
        request_id = self.store.log_ai_request(request, user_id=self.user_id)
        response = AiResponse(
            request_id=request_id,
            response_text=response_text,
            latency_ms=latency_ms,
            token_estimate=estimate_tokens(response_text),
        )
        self.store.log_ai_response(response)
        note = Note(parent_type="message", parent_id=message_id, content=response_text)
        note_id = self.store.add_note(note, user_id=self.user_id)
        logger.info("Created message summary for message %s.", message_id)
        return note_id

    def suggest_follow_up(self, message_id: int) -> str:
        """Summary: Suggest a follow-up for a message.

        Importance: Guides users to act on pending conversations.
        Alternatives: Provide no suggestions or use manual notes only.
        """

        message = self.store.get_message(message_id, user_id=self.user_id)
        if not message:
            raise ValueError(f"Message {message_id} not found")
        prompt = (
            "Suggest a follow-up action for the email. Keep it brief.\n\n"
            f"From: {message.sender}\n"
            f"Subject: {message.subject}\n"
            f"Body: {message.body}\n"
        )
        response_text, latency_ms = self.ai_provider.generate_text(
            prompt, purpose="follow_up"
        )
        request = AiRequest(
            provider=self.provider_name,
            model=self.model_name,
            prompt=prompt,
            purpose="follow_up",
            timestamp=datetime.utcnow(),
        )
        request_id = self.store.log_ai_request(request, user_id=self.user_id)
        response = AiResponse(
            request_id=request_id,
            response_text=response_text,
            latency_ms=latency_ms,
            token_estimate=estimate_tokens(response_text),
        )
        self.store.log_ai_response(response)
        logger.info("Suggested follow-up for message %s.", message_id)
        return response_text


@dataclass(frozen=True)
class TaskService:
    """Summary: Manages action item storage and extraction.

    Importance: Captures follow-ups from emails and meetings as structured tasks.
    Alternatives: Store action items as unstructured notes only.
    """

    store: SqliteStore
    ai_provider: AiProvider
    provider_name: str
    model_name: str

    def add_task(self, parent_type: str, parent_id: int, description: str) -> int:
        """Summary: Create a task linked to a message or meeting.

        Importance: Ensures action items are tracked in structured form.
        Alternatives: Keep tasks as plain text notes without structure.
        """

        task = Task(parent_type=parent_type, parent_id=parent_id, description=description)
        task_id = self.store.add_task(task, user_id=self.user_id)
        logger.info("Added task for %s %s.", parent_type, parent_id)
        return task_id

    def list_tasks(self, parent_type: str, parent_id: int) -> list[StoredTask]:
        """Summary: List tasks for a message or meeting.

        Importance: Allows users to review extracted or added action items.
        Alternatives: Use external task systems for tracking.
        """

        return self.store.list_tasks(parent_type, parent_id, user_id=self.user_id)

    def update_task_status(self, task_id: int, status: str) -> None:
        """Summary: Update a task status.

        Importance: Allows marking follow-ups as completed or deferred.
        Alternatives: Recreate tasks with new statuses.
        """

        self.store.update_task_status(task_id, status, user_id=self.user_id)
        logger.info("Updated task %s to %s.", task_id, status)

    def extract_tasks_from_message(self, message_id: int) -> list[int]:
        """Summary: Extract action items from a message using AI.

        Importance: Automates follow-up capture while staying draft-first.
        Alternatives: Require manual task entry for each action item.
        """

        message = self.store.get_message(message_id, user_id=self.user_id)
        if not message:
            raise ValueError(f"Message {message_id} not found")
        prompt = (
            "Extract action items from the email. Respond with one task per line.\n\n"
            f"Subject: {message.subject}\n"
            f"From: {message.sender}\n"
            f"Body: {message.body}\n"
        )
        response_text, latency_ms = self.ai_provider.generate_text(prompt, purpose="extract_tasks")
        request = AiRequest(
            provider=self.provider_name,
            model=self.model_name,
            prompt=prompt,
            purpose="extract_tasks",
            timestamp=datetime.utcnow(),
        )
        request_id = self.store.log_ai_request(request, user_id=self.user_id)
        response = AiResponse(
            request_id=request_id,
            response_text=response_text,
            latency_ms=latency_ms,
            token_estimate=estimate_tokens(response_text),
        )
        self.store.log_ai_response(response)
        task_ids: list[int] = []
        for line in response_text.splitlines():
            cleaned = line.strip().lstrip("-").strip()
            if cleaned:
                task_ids.append(self.add_task("message", message_id, cleaned))
        logger.info("Extracted %s tasks from message %s.", len(task_ids), message_id)
        return task_ids

    def extract_tasks_from_meeting(self, meeting_id: int) -> list[int]:
        """Summary: Extract action items from a meeting transcript.

        Importance: Captures meeting follow-ups as structured tasks.
        Alternatives: Require manual task entry for meetings.
        """

        transcript = self.store.get_meeting_transcript(meeting_id)
        if not transcript:
            raise ValueError(f"Meeting transcript {meeting_id} not found")
        prompt = (
            "Extract action items from the meeting transcript. Respond with one task per line.\n\n"
            f"Transcript:\n{transcript.content}\n"
        )
        response_text, latency_ms = self.ai_provider.generate_text(prompt, purpose="extract_tasks")
        request = AiRequest(
            provider=self.provider_name,
            model=self.model_name,
            prompt=prompt,
            purpose="extract_tasks",
            timestamp=datetime.utcnow(),
        )
        request_id = self.store.log_ai_request(request, user_id=self.user_id)
        response = AiResponse(
            request_id=request_id,
            response_text=response_text,
            latency_ms=latency_ms,
            token_estimate=estimate_tokens(response_text),
        )
        self.store.log_ai_response(response)
        task_ids: list[int] = []
        for line in response_text.splitlines():
            cleaned = line.strip().lstrip("-").strip()
            if cleaned:
                task_ids.append(self.add_task("meeting", meeting_id, cleaned))
        logger.info("Extracted %s tasks from meeting %s.", len(task_ids), meeting_id)
        return task_ids


@dataclass(frozen=True)
class MeetingSummaryService:
    """Summary: Handles meeting transcript storage and summarization.

    Importance: Produces meeting notes and highlights from transcripts.
    Alternatives: Store only raw transcripts without summaries.
    """

    store: SqliteStore
    ai_provider: AiProvider
    provider_name: str
    model_name: str

    def add_transcript(self, meeting_id: int, content: str) -> None:
        """Summary: Persist a meeting transcript.

        Importance: Enables downstream summarization and task extraction.
        Alternatives: Use external storage for transcripts only.
        """

        self.store.save_meeting_transcript(meeting_id, content)
        logger.info("Saved transcript for meeting %s.", meeting_id)

    def summarize_meeting(self, meeting_id: int) -> int:
        """Summary: Summarize a meeting transcript into a note.

        Importance: Produces concise meeting notes for follow-ups.
        Alternatives: Require manual note creation after meetings.
        """

        transcript = self.store.get_meeting_transcript(meeting_id)
        if not transcript:
            raise ValueError(f"Meeting transcript {meeting_id} not found")
        prompt = (
            "Summarize the meeting transcript with key decisions and next steps.\n\n"
            f"Transcript:\n{transcript.content}\n"
        )
        response_text, latency_ms = self.ai_provider.generate_text(prompt, purpose="meeting_summary")
        request = AiRequest(
            provider=self.provider_name,
            model=self.model_name,
            prompt=prompt,
            purpose="meeting_summary",
            timestamp=datetime.utcnow(),
        )
        request_id = self.store.log_ai_request(request, user_id=self.user_id)
        response = AiResponse(
            request_id=request_id,
            response_text=response_text,
            latency_ms=latency_ms,
            token_estimate=estimate_tokens(response_text),
        )
        self.store.log_ai_response(response)
        note = Note(parent_type="meeting", parent_id=meeting_id, content=response_text)
        note_id = self.store.add_note(note, user_id=self.user_id)
        logger.info("Created meeting summary for meeting %s.", meeting_id)
        return note_id


@dataclass(frozen=True)
class ConnectionService:
    """Summary: Manages external provider connections.

    Importance: Tracks integration state for email and calendar providers.
    Alternatives: Store connections only in environment configuration.
    """

    store: SqliteStore
    user_id: int

    def add_connection(
        self, provider_type: str, provider_name: str, status: str, details: str | None = None
    ) -> int:
        """Summary: Create a new connection record.

        Importance: Records integration metadata without persisting secrets.
        Alternatives: Skip connection tracking in the MVP.
        """

        connection = Connection(
            provider_type=provider_type,
            provider_name=provider_name,
            status=status,
            created_at=datetime.utcnow(),
            details=details,
        )
        connection_id = self.store.add_connection(connection, user_id=self.user_id)
        logger.info("Added connection %s (%s).", provider_name, provider_type)
        return connection_id

    def list_connections(self) -> list[StoredConnection]:
        """Summary: List stored connections for the current user.

        Importance: Supports UI and API views for integrations.
        Alternatives: Store connection state in config only.
        """

        return self.store.list_connections(user_id=self.user_id)


@dataclass(frozen=True)
class TokenService:
    """Summary: Stores OAuth tokens with basic obfuscation.

    Importance: Enables future provider ingestion without raw token storage.
    Alternatives: Use a secrets manager or encrypted database.
    """

    store: SqliteStore
    user_id: int
    codec: TokenCodec
    config: AppConfig

    def store_tokens(
        self,
        provider_name: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: str | None,
    ) -> int:
        """Summary: Store OAuth tokens for a provider.

        Importance: Persists tokens needed for API calls.
        Alternatives: Require re-authentication for each run.
        """

        encoded_access = self.codec.encode(access_token)
        encoded_refresh = self.codec.encode(refresh_token) if refresh_token else None
        token_id = self.store.upsert_oauth_token(
            user_id=self.user_id,
            provider_name=provider_name,
            access_token=encoded_access,
            refresh_token=encoded_refresh,
            expires_at=expires_at,
        )
        logger.info("Stored OAuth tokens for %s.", provider_name)
        return token_id

    def load_tokens(self, provider_name: str) -> dict[str, str | None]:
        """Summary: Load OAuth tokens for a provider.

        Importance: Supports future provider ingestion logic.
        Alternatives: Keep tokens only in memory.
        """

        record = self.store.get_oauth_token(self.user_id, provider_name)
        if not record:
            raise ValueError("OAuth token not found")
        return {
            "access_token": self.codec.decode(record.access_token),
            "refresh_token": self.codec.decode(record.refresh_token)
            if record.refresh_token
            else None,
            "expires_at": record.expires_at,
        }

    def get_access_token(self, provider_name: str, refresh_if_needed: bool = True) -> str:
        """Summary: Return an access token, refreshing if expired.

        Importance: Keeps provider ingestion working without manual re-auth.
        Alternatives: Always re-run OAuth flows for each session.
        """

        record = self.store.get_oauth_token(self.user_id, provider_name)
        if not record:
            raise ValueError("OAuth token not found")
        access_token = self.codec.decode(record.access_token)
        refresh_token = (
            self.codec.decode(record.refresh_token) if record.refresh_token else None
        )
        if refresh_if_needed and self._expires_soon(record.expires_at):
            if not refresh_token:
                raise ValueError("Refresh token not available")
            token_result = refresh_oauth_token(self.config, provider_name, refresh_token)
            next_refresh = token_result.refresh_token or refresh_token
            self.store_tokens(
                provider_name,
                token_result.access_token,
                next_refresh,
                token_result.expires_at,
            )
            return token_result.access_token
        return access_token

    def _expires_soon(self, expires_at: str | None) -> bool:
        """Summary: Check if a token is expired or near expiry.

        Importance: Avoids using tokens that are about to expire.
        Alternatives: Always refresh tokens before use.
        """

        if not expires_at:
            return False
        try:
            expires = datetime.fromisoformat(expires_at)
        except ValueError:
            return False
        return expires <= datetime.utcnow() + timedelta(seconds=60)


@dataclass(frozen=True)
class StatsService:
    """Summary: Provides lightweight analytics and counts.

    Importance: Enables dashboards and quick health checks.
    Alternatives: Calculate counts directly in the API or UI.
    """

    store: SqliteStore
    user_id: int

    def snapshot(self) -> dict[str, int]:
        """Summary: Return a snapshot of counts for key entities.

        Importance: Provides a simple metrics view for the MVP.
        Alternatives: Build a full analytics pipeline.
        """

        return {
            "messages": self.store.count_messages(user_id=self.user_id),
            "meetings": self.store.count_meetings(user_id=self.user_id),
            "categories": self.store.count_categories(user_id=self.user_id),
            "tasks": self.store.count_tasks(user_id=self.user_id),
            "notes": self.store.count_notes(user_id=self.user_id),
            "connections": self.store.count_connections(user_id=self.user_id),
        }


@dataclass(frozen=True)
class AiAuditService:
    """Summary: Provides access to AI audit logs.

    Importance: Enables review of AI usage and outputs.
    Alternatives: Use raw database queries or log files.
    """

    store: SqliteStore
    user_id: int

    def list_requests(self, limit: int = 20) -> list[dict[str, str | int]]:
        """Summary: Return recent AI requests for the user.

        Importance: Supports auditing prompts and purposes.
        Alternatives: Skip AI request storage.
        """

        requests = self.store.list_ai_requests(limit, user_id=self.user_id)
        return [
            {
                "id": request.id,
                "provider": request.provider,
                "model": request.model,
                "purpose": request.purpose,
                "timestamp": request.timestamp,
            }
            for request in requests
        ]

    def list_responses(self, limit: int = 20) -> list[dict[str, str | int]]:
        """Summary: Return recent AI responses.

        Importance: Supports auditing outputs and latency.
        Alternatives: Skip AI response storage.
        """

        responses = self.store.list_ai_responses(limit)
        return [
            {
                "id": response.id,
                "request_id": response.request_id,
                "latency_ms": response.latency_ms,
                "token_estimate": response.token_estimate,
            }
            for response in responses
        ]


@dataclass(frozen=True)
class TriageService:
    """Summary: Provides priority ranking for messages.

    Importance: Enables smart inbox triage for the MVP.
    Alternatives: Use ML classifiers or user-defined rules only.
    """

    store: SqliteStore
    user_id: int
    high_keywords: list[str]
    medium_keywords: list[str]

    def rank_messages(self, limit: int = 20) -> list[dict[str, str | int]]:
        """Summary: Rank messages by simple keyword heuristics.

        Importance: Surfaces urgent messages for review.
        Alternatives: Use AI-based priority scoring.
        """

        messages = self.store.list_messages(limit, user_id=self.user_id)
        ranked: list[dict[str, str | int]] = []
        for message in messages:
            text = f"{message.subject} {message.body}".lower()
            score = 0
            if any(keyword in text for keyword in self.high_keywords):
                score += 2
            if any(keyword in text for keyword in self.medium_keywords):
                score += 1
            priority = "high" if score >= 2 else "medium" if score == 1 else "low"
            ranked.append(
                {
                    "id": message.id,
                    "subject": message.subject,
                    "sender": message.sender,
                    "priority": priority,
                    "score": score,
                }
            )
        return ranked
