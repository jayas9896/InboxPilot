"""Summary: FastAPI application for InboxPilot.

Importance: Exposes HTTP endpoints for integrations and UI clients.
Alternatives: Use a CLI-only workflow or a different web framework.
"""

from __future__ import annotations

from pathlib import Path
import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from inboxpilot.app import build_services
from inboxpilot.calendar import IcsCalendarProvider, MockCalendarProvider
from inboxpilot.category_templates import list_templates, load_template
from inboxpilot.config import AppConfig
from inboxpilot.email import EmlEmailProvider, MockEmailProvider
from inboxpilot.oauth import build_google_auth_url, build_microsoft_auth_url, create_state_token


class IngestRequest(BaseModel):
    """Summary: Request payload for mock email ingestion.

    Importance: Keeps ingestion inputs explicit for API clients.
    Alternatives: Use query parameters instead of JSON payloads.
    """

    limit: int = Field(default=5, ge=1, le=200)
    fixture_path: str | None = None


class EmlIngestRequest(BaseModel):
    """Summary: Request payload for .eml ingestion.

    Importance: Supports email ingestion without provider APIs.
    Alternatives: Require IMAP or OAuth providers.
    """

    paths: list[str]
    limit: int = Field(default=25, ge=1, le=200)


class MeetingIngestRequest(BaseModel):
    """Summary: Request payload for mock meeting ingestion.

    Importance: Allows controlled meeting ingestion via the API.
    Alternatives: Use a static fixture path without overrides.
    """

    limit: int = Field(default=5, ge=1, le=200)
    fixture_path: str | None = None


class IcsIngestRequest(BaseModel):
    """Summary: Request payload for iCalendar ingestion.

    Importance: Supports calendar ingestion without provider APIs.
    Alternatives: Require direct Google or Microsoft integrations.
    """

    path: str
    limit: int = Field(default=25, ge=1, le=200)


class CategoryCreateRequest(BaseModel):
    """Summary: Request payload for category creation.

    Importance: Enables client-defined categories over HTTP.
    Alternatives: Create categories only through the CLI.
    """

    name: str
    description: str | None = None


class CategoryAssignRequest(BaseModel):
    """Summary: Request payload for assigning categories.

    Importance: Connects messages to user-defined categories.
    Alternatives: Assign categories in bulk using rules.
    """

    message_id: int
    category_id: int


class CategorySuggestRequest(BaseModel):
    """Summary: Request payload for category suggestions.

    Importance: Enables AI-based category suggestions over HTTP.
    Alternatives: Use only rule-based suggestions or manual assignment.
    """

    message_id: int


class ChatRequest(BaseModel):
    """Summary: Request payload for chat queries.

    Importance: Provides the central chat workflow over HTTP.
    Alternatives: Return raw search results without AI context.
    """

    query: str
    limit: int = Field(default=3, ge=1, le=50)


class DraftRequest(BaseModel):
    """Summary: Request payload for drafting replies.

    Importance: Keeps drafting explicit and user-controlled.
    Alternatives: Autogenerate drafts without explicit request.
    """

    message_id: int
    instructions: str


class MessageSummaryRequest(BaseModel):
    """Summary: Request payload for message summarization.

    Importance: Enables message summarization via the API.
    Alternatives: Summarize messages via CLI only.
    """

    message_id: int


class FollowUpRequest(BaseModel):
    """Summary: Request payload for follow-up suggestions.

    Importance: Enables follow-up guidance over HTTP.
    Alternatives: Use only task extraction.
    """

    message_id: int


class NoteCreateRequest(BaseModel):
    """Summary: Request payload for note creation.

    Importance: Stores follow-up context with messages or meetings.
    Alternatives: Store notes in a separate note-taking app.
    """

    parent_type: str
    parent_id: int
    content: str


class TokenStoreRequest(BaseModel):
    """Summary: Request payload for storing OAuth tokens.

    Importance: Enables saving tokens for future provider ingestion.
    Alternatives: Store tokens in an external vault.
    """

    provider_name: str
    access_token: str
    refresh_token: str | None = None
    expires_at: str | None = None


class TaskCreateRequest(BaseModel):
    """Summary: Request payload for task creation.

    Importance: Enables explicit task creation from API clients.
    Alternatives: Only allow AI-extracted tasks.
    """

    parent_type: str
    parent_id: int
    description: str


class TaskUpdateRequest(BaseModel):
    """Summary: Request payload for task status updates.

    Importance: Enables marking tasks as completed or deferred via the API.
    Alternatives: Delete and recreate tasks with new status.
    """

    task_id: int
    status: str


class TaskExtractRequest(BaseModel):
    """Summary: Request payload for task extraction.

    Importance: Allows clients to trigger AI action item extraction.
    Alternatives: Provide extraction only in the CLI.
    """

    message_id: int


class TemplateLoadRequest(BaseModel):
    """Summary: Request payload for template loading.

    Importance: Lets clients bootstrap categories quickly.
    Alternatives: Require manual category creation.
    """

    template_name: str


class MeetingTranscriptRequest(BaseModel):
    """Summary: Request payload for meeting transcript storage.

    Importance: Allows clients to submit transcripts for summarization.
    Alternatives: Store transcripts only via file uploads.
    """

    meeting_id: int
    content: str


class MeetingSummaryRequest(BaseModel):
    """Summary: Request payload for meeting summary generation.

    Importance: Allows clients to request summaries on demand.
    Alternatives: Summarize transcripts automatically on ingestion.
    """

    meeting_id: int


class ConnectionCreateRequest(BaseModel):
    """Summary: Request payload for integration connections.

    Importance: Enables tracking provider integrations over HTTP.
    Alternatives: Create connections only via CLI.
    """

    provider_type: str
    provider_name: str
    status: str
    details: str | None = None


def create_app(config: AppConfig) -> FastAPI:
    """Summary: Create a FastAPI app wired to InboxPilot services.

    Importance: Ensures the API layer shares the same configuration and storage.
    Alternatives: Instantiate services globally outside the factory.
    """

    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    app = FastAPI(title="InboxPilot API", version="0.1.0")
    services = build_services(config)
    app.state.oauth_states = {}

    def _register_state(provider: str, state: str) -> None:
        """Summary: Register an OAuth state token.

        Importance: Enables basic validation of OAuth callbacks.
        Alternatives: Store state in a database or signed cookies.
        """

        app.state.oauth_states[state] = {"provider": provider, "created_at": datetime.utcnow()}

    def _validate_state(provider: str, state: str) -> None:
        """Summary: Validate an OAuth state token.

        Importance: Reduces CSRF risks in OAuth flows.
        Alternatives: Use a dedicated session store for state.
        """

        record = app.state.oauth_states.get(state)
        if not record or record["provider"] != provider:
            raise HTTPException(status_code=400, detail="Invalid OAuth state")
        if datetime.utcnow() - record["created_at"] > timedelta(minutes=10):
            raise HTTPException(status_code=400, detail="OAuth state expired")

    def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
        """Summary: Enforce API key authentication when configured.

        Importance: Adds a minimal security layer for local and private deployments.
        Alternatives: Use OAuth or session-based authentication.
        """

        if not config.api_key:
            return
        if x_api_key != config.api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")

    @app.get("/", response_class=HTMLResponse)
    def landing() -> str:
        """Summary: Serve the local web dashboard.

        Importance: Provides a simple UI for the MVP without extra tooling.
        Alternatives: Build a separate frontend app served by a web server.
        """

        html_path = Path("web/index.html")
        if not html_path.exists():
            raise HTTPException(status_code=404, detail="Dashboard not found")
        return html_path.read_text(encoding="utf-8")

    @app.get("/health")
    def health() -> dict[str, str]:
        """Summary: Health check endpoint.

        Importance: Supports uptime checks in local and cloud deployments.
        Alternatives: Use a metrics endpoint only.
        """

        return {"status": "ok"}

    @app.post("/ingest/mock", dependencies=[Depends(require_api_key)])
    def ingest_mock(payload: IngestRequest) -> dict[str, Any]:
        """Summary: Ingest mock email messages from a fixture.

        Importance: Enables deterministic demos and integration tests.
        Alternatives: Accept raw message payloads over the API.
        """

        fixture_path = Path(payload.fixture_path) if payload.fixture_path else Path("data/mock_messages.json")
        if not fixture_path.exists():
            raise HTTPException(status_code=404, detail="Fixture not found")
        provider = MockEmailProvider(fixture_path)
        messages = provider.fetch_recent(payload.limit)
        ids = services.ingestion.ingest_messages(messages)
        return {"ingested": len(ids)}

    @app.post("/ingest/eml", dependencies=[Depends(require_api_key)])
    def ingest_eml(payload: EmlIngestRequest) -> dict[str, Any]:
        """Summary: Ingest emails from .eml files.

        Importance: Enables local email imports without API auth.
        Alternatives: Use IMAP or provider APIs.
        """

        eml_paths = [Path(path) for path in payload.paths]
        if not eml_paths:
            raise HTTPException(status_code=400, detail="No .eml paths provided")
        provider = EmlEmailProvider(eml_paths)
        messages = provider.fetch_recent(payload.limit)
        ids = services.ingestion.ingest_messages(messages)
        return {"ingested": len(ids)}

    @app.post("/ingest/calendar-mock", dependencies=[Depends(require_api_key)])
    def ingest_calendar_mock(payload: MeetingIngestRequest) -> dict[str, Any]:
        """Summary: Ingest mock meeting data from a fixture.

        Importance: Enables meeting workflows without live providers.
        Alternatives: Require live calendar integrations for all runs.
        """

        fixture_path = Path(payload.fixture_path) if payload.fixture_path else Path("data/mock_meetings.json")
        if not fixture_path.exists():
            raise HTTPException(status_code=404, detail="Fixture not found")
        provider = MockCalendarProvider(fixture_path)
        meetings = provider.fetch_upcoming(payload.limit)
        ids = services.meetings.ingest_meetings(meetings)
        return {"ingested": len(ids)}

    @app.post("/ingest/calendar-ics", dependencies=[Depends(require_api_key)])
    def ingest_calendar_ics(payload: IcsIngestRequest) -> dict[str, Any]:
        """Summary: Ingest meetings from an iCalendar (.ics) file.

        Importance: Enables local calendar ingestion without API auth.
        Alternatives: Use direct provider APIs with OAuth.
        """

        ics_path = Path(payload.path)
        if not ics_path.exists():
            raise HTTPException(status_code=404, detail="ICS file not found")
        provider = IcsCalendarProvider(ics_path)
        meetings = provider.fetch_upcoming(payload.limit)
        ids = services.meetings.ingest_meetings(meetings)
        return {"ingested": len(ids)}

    @app.get("/messages", dependencies=[Depends(require_api_key)])
    def list_messages(limit: int = 10) -> list[dict[str, Any]]:
        """Summary: List recent messages.

        Importance: Provides data for UI clients and API consumers.
        Alternatives: Return only message IDs with separate detail endpoints.
        """

        return [
            {
                "id": message.id,
                "provider_message_id": message.provider_message_id,
                "subject": message.subject,
                "sender": message.sender,
                "recipients": message.recipients,
                "timestamp": message.timestamp,
                "snippet": message.snippet,
            }
            for message in services.store.list_messages(limit, user_id=services.user_id)
        ]

    @app.get("/meetings", dependencies=[Depends(require_api_key)])
    def list_meetings(limit: int = 10) -> list[dict[str, Any]]:
        """Summary: List recent meetings.

        Importance: Supports meeting listings for clients and UI.
        Alternatives: Provide meetings only after a specific search.
        """

        return [
            {
                "id": meeting.id,
                "provider_event_id": meeting.provider_event_id,
                "title": meeting.title,
                "participants": meeting.participants,
                "start_time": meeting.start_time,
                "end_time": meeting.end_time,
                "transcript_ref": meeting.transcript_ref,
            }
            for meeting in services.meetings.list_meetings(limit)
        ]

    @app.get("/categories", dependencies=[Depends(require_api_key)])
    def list_categories() -> list[dict[str, Any]]:
        """Summary: List existing categories.

        Importance: Enables category management from clients.
        Alternatives: Cache categories in client state only.
        """

        return [
            {"id": category.id, "name": category.name, "description": category.description}
            for category in services.store.list_categories(user_id=services.user_id)
        ]

    @app.post("/categories", dependencies=[Depends(require_api_key)])
    def create_category(payload: CategoryCreateRequest) -> dict[str, Any]:
        """Summary: Create a category.

        Importance: Adds first-class user-defined organization.
        Alternatives: Auto-create categories from AI suggestions only.
        """

        category_id = services.categories.create_category(payload.name, payload.description)
        return {"id": category_id}

    @app.post("/categories/assign", dependencies=[Depends(require_api_key)])
    def assign_category(payload: CategoryAssignRequest) -> dict[str, Any]:
        """Summary: Assign a category to a message.

        Importance: Links messages to organization labels.
        Alternatives: Store category info directly on the message.
        """

        services.categories.assign_category(payload.message_id, payload.category_id)
        return {"status": "ok"}

    @app.post("/categories/suggest", dependencies=[Depends(require_api_key)])
    def suggest_categories(payload: CategorySuggestRequest) -> list[dict[str, Any]]:
        """Summary: Suggest categories for a stored message.

        Importance: Provides AI-driven suggestions for inbox organization.
        Alternatives: Use only manual or rule-based categorization.
        """

        suggestions = services.categories.suggest_categories_ai(payload.message_id)
        return [
            {"name": category.name, "description": category.description}
            for category in suggestions
        ]

    @app.get("/templates", dependencies=[Depends(require_api_key)])
    def list_category_templates() -> list[dict[str, Any]]:
        """Summary: List available category templates.

        Importance: Helps clients discover starter packs.
        Alternatives: Maintain templates only in docs.
        """

        return [
            {"name": template.name, "count": len(template.categories)}
            for template in list_templates()
        ]

    @app.post("/templates/load", dependencies=[Depends(require_api_key)])
    def load_category_template(payload: TemplateLoadRequest) -> dict[str, Any]:
        """Summary: Load a template pack into storage.

        Importance: Speeds onboarding for common domains.
        Alternatives: Require manual creation for every category.
        """

        created = load_template(services.store, payload.template_name, user_id=services.user_id)
        return {"created": created}

    @app.post("/chat", dependencies=[Depends(require_api_key)])
    def chat(payload: ChatRequest) -> dict[str, Any]:
        """Summary: Answer a question using stored messages.

        Importance: Provides the chat assistant experience over HTTP.
        Alternatives: Return raw search results instead of AI summaries.
        """

        answer = services.chat.answer(payload.query, limit=payload.limit)
        return {"answer": answer}

    @app.post("/draft", dependencies=[Depends(require_api_key)])
    def draft(payload: DraftRequest) -> dict[str, Any]:
        """Summary: Draft a reply to a message.

        Importance: Keeps drafts explicit and user-controlled.
        Alternatives: Autogenerate drafts without a user prompt.
        """

        draft_text = services.chat.draft_reply(payload.message_id, payload.instructions)
        return {"draft": draft_text}

    @app.post("/messages/summary", dependencies=[Depends(require_api_key)])
    def summarize_message(payload: MessageSummaryRequest) -> dict[str, Any]:
        """Summary: Summarize a message and store it as a note.

        Importance: Provides concise context for message review.
        Alternatives: Require manual summarization.
        """

        note_id = services.message_insights.summarize_message(payload.message_id)
        return {"note_id": note_id}

    @app.post("/messages/follow-up", dependencies=[Depends(require_api_key)])
    def suggest_follow_up(payload: FollowUpRequest) -> dict[str, Any]:
        """Summary: Suggest a follow-up action for a message.

        Importance: Guides the user toward next steps.
        Alternatives: Provide no follow-up suggestions.
        """

        suggestion = services.message_insights.suggest_follow_up(payload.message_id)
        return {"suggestion": suggestion}

    @app.post("/tokens", dependencies=[Depends(require_api_key)])
    def store_tokens(payload: TokenStoreRequest) -> dict[str, Any]:
        """Summary: Store OAuth tokens for a provider.

        Importance: Prepares provider ingestion with saved tokens.
        Alternatives: Require interactive OAuth for each run.
        """

        token_id = services.tokens.store_tokens(
            payload.provider_name,
            payload.access_token,
            payload.refresh_token,
            payload.expires_at,
        )
        return {"id": token_id}

    @app.post("/notes", dependencies=[Depends(require_api_key)])
    def add_note(payload: NoteCreateRequest) -> dict[str, Any]:
        """Summary: Create a note for a message or meeting.

        Importance: Stores user context and action items.
        Alternatives: Store notes in a separate system.
        """

        note_id = services.chat.add_note(payload.parent_type, payload.parent_id, payload.content)
        return {"id": note_id}

    @app.get("/notes", dependencies=[Depends(require_api_key)])
    def list_notes(parent_type: str, parent_id: int) -> list[dict[str, Any]]:
        """Summary: List notes for a message or meeting.

        Importance: Exposes stored notes for UI clients.
        Alternatives: List notes only through CLI.
        """

        return [
            {"parent_type": note.parent_type, "parent_id": note.parent_id, "content": note.content}
            for note in services.store.list_notes(parent_type, parent_id, user_id=services.user_id)
        ]

    @app.post("/tasks", dependencies=[Depends(require_api_key)])
    def add_task(payload: TaskCreateRequest) -> dict[str, Any]:
        """Summary: Create a task for a message or meeting.

        Importance: Allows clients to capture action items explicitly.
        Alternatives: Rely only on AI extraction.
        """

        task_id = services.tasks.add_task(payload.parent_type, payload.parent_id, payload.description)
        return {"id": task_id}

    @app.post("/tasks/update", dependencies=[Depends(require_api_key)])
    def update_task(payload: TaskUpdateRequest) -> dict[str, Any]:
        """Summary: Update task status.

        Importance: Supports task completion workflows.
        Alternatives: Use a separate task management system.
        """

        services.tasks.update_task_status(payload.task_id, payload.status)
        return {"status": "ok"}

    @app.get("/tasks", dependencies=[Depends(require_api_key)])
    def list_tasks(parent_type: str, parent_id: int) -> list[dict[str, Any]]:
        """Summary: List tasks for a message or meeting.

        Importance: Enables action-item review in client apps.
        Alternatives: Return tasks only when requested by AI.
        """

        return [
            {
                "id": task.id,
                "parent_type": task.parent_type,
                "parent_id": task.parent_id,
                "description": task.description,
                "status": task.status,
                "due_date": task.due_date,
            }
            for task in services.tasks.list_tasks(parent_type, parent_id)
        ]

    @app.post("/tasks/extract", dependencies=[Depends(require_api_key)])
    def extract_tasks(payload: TaskExtractRequest) -> dict[str, Any]:
        """Summary: Extract tasks from a message using AI.

        Importance: Captures follow-ups in a structured way.
        Alternatives: Require manual task entry for each action item.
        """

        task_ids = services.tasks.extract_tasks_from_message(payload.message_id)
        return {"created": len(task_ids)}

    @app.post("/tasks/extract-meeting", dependencies=[Depends(require_api_key)])
    def extract_meeting_tasks(payload: MeetingSummaryRequest) -> dict[str, Any]:
        """Summary: Extract tasks from a meeting transcript.

        Importance: Captures meeting follow-ups in a structured format.
        Alternatives: Require manual task entry for meetings.
        """

        task_ids = services.tasks.extract_tasks_from_meeting(payload.meeting_id)
        return {"created": len(task_ids)}

    @app.post("/meetings/transcript", dependencies=[Depends(require_api_key)])
    def add_meeting_transcript(payload: MeetingTranscriptRequest) -> dict[str, Any]:
        """Summary: Store a meeting transcript for summarization.

        Importance: Enables AI summaries and task extraction for meetings.
        Alternatives: Store transcripts only as attachments.
        """

        services.meeting_notes.add_transcript(payload.meeting_id, payload.content)
        return {"status": "ok"}

    @app.post("/meetings/summary", dependencies=[Depends(require_api_key)])
    def summarize_meeting(payload: MeetingSummaryRequest) -> dict[str, Any]:
        """Summary: Summarize a meeting transcript into a note.

        Importance: Produces readable meeting notes for follow-ups.
        Alternatives: Require manual note creation for meetings.
        """

        note_id = services.meeting_notes.summarize_meeting(payload.meeting_id)
        return {"note_id": note_id}

    @app.post("/connections", dependencies=[Depends(require_api_key)])
    def add_connection(payload: ConnectionCreateRequest) -> dict[str, Any]:
        """Summary: Create a connection record.

        Importance: Tracks provider integration state for UI clients.
        Alternatives: Store connection data outside the API.
        """

        connection_id = services.connections.add_connection(
            payload.provider_type,
            payload.provider_name,
            payload.status,
            payload.details,
        )
        return {"id": connection_id}

    @app.get("/connections", dependencies=[Depends(require_api_key)])
    def list_connections() -> list[dict[str, Any]]:
        """Summary: List integration connections.

        Importance: Exposes integration status to clients.
        Alternatives: Keep connections private to the server only.
        """

        return [
            {
                "id": connection.id,
                "provider_type": connection.provider_type,
                "provider_name": connection.provider_name,
                "status": connection.status,
                "created_at": connection.created_at,
                "details": connection.details,
            }
            for connection in services.connections.list_connections()
        ]

    @app.get("/stats", dependencies=[Depends(require_api_key)])
    def stats() -> dict[str, int]:
        """Summary: Return a snapshot of entity counts.

        Importance: Provides lightweight analytics for dashboards.
        Alternatives: Build a separate analytics service.
        """

        return services.stats.snapshot()

    @app.get("/triage", dependencies=[Depends(require_api_key)])
    def triage(limit: int = 20) -> list[dict[str, Any]]:
        """Summary: Return prioritized messages.

        Importance: Supports inbox triage views in the UI.
        Alternatives: Use AI-based scoring or rules-only filters.
        """

        return services.triage.rank_messages(limit=limit)

    @app.get("/oauth/google", dependencies=[Depends(require_api_key)])
    def oauth_google() -> dict[str, str]:
        """Summary: Return the Google OAuth authorization URL.

        Importance: Enables initiating OAuth flows for Gmail/Calendar.
        Alternatives: Use CLI-only OAuth helpers.
        """

        state = create_state_token()
        _register_state("google", state)
        return {"url": build_google_auth_url(config, state), "state": state}

    @app.get("/oauth/microsoft", dependencies=[Depends(require_api_key)])
    def oauth_microsoft() -> dict[str, str]:
        """Summary: Return the Microsoft OAuth authorization URL.

        Importance: Enables initiating OAuth flows for Outlook/Calendar.
        Alternatives: Use CLI-only OAuth helpers.
        """

        state = create_state_token()
        _register_state("microsoft", state)
        return {"url": build_microsoft_auth_url(config, state), "state": state}

    @app.get("/oauth/callback", response_class=HTMLResponse)
    def oauth_callback(provider: str, code: str, state: str) -> str:
        """Summary: Handle OAuth callback and record a connection.

        Importance: Completes OAuth flow tracking without storing secrets.
        Alternatives: Implement full token exchange and storage.
        """

        if provider not in {"google", "microsoft"}:
            raise HTTPException(status_code=400, detail="Unknown provider")
        _validate_state(provider, state)
        services.connections.add_connection(
            provider_type="oauth",
            provider_name=provider,
            status="authorized",
            details="auth_code_received",
        )
        return "<h1>InboxPilot OAuth connected</h1><p>You can close this window.</p>"

    return app


app = create_app(AppConfig.from_env())
