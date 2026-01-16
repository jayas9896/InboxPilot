"""Summary: Application factory wiring core services.

Importance: Centralizes dependency creation for CLI and future API layers.
Alternatives: Instantiate services manually in each entrypoint.
"""

from __future__ import annotations

from dataclasses import dataclass

from inboxpilot.ai import AiProviderFactory
from inboxpilot.classifier import RuleBasedClassifier
from inboxpilot.config import AppConfig
from inboxpilot.models import User
from inboxpilot.services import (
    CategoryService,
    ChatService,
    ConnectionService,
    IngestionService,
    MessageInsightsService,
    MeetingService,
    MeetingSummaryService,
    StatsService,
    TriageService,
    TokenService,
    TaskService,
)
from inboxpilot.storage.sqlite_store import SqliteStore
from inboxpilot.token_codec import TokenCodec


@dataclass(frozen=True)
class AppServices:
    """Summary: Bundle of core services for InboxPilot.

    Importance: Simplifies passing dependencies to UI or API layers.
    Alternatives: Use a dependency injection container.
    """

    ingestion: IngestionService
    meetings: MeetingService
    categories: CategoryService
    chat: ChatService
    tasks: TaskService
    meeting_notes: MeetingSummaryService
    connections: ConnectionService
    stats: StatsService
    triage: TriageService
    message_insights: MessageInsightsService
    tokens: TokenService
    store: SqliteStore
    user_id: int


def build_services(config: AppConfig) -> AppServices:
    """Summary: Build core services from configuration.

    Importance: Provides a single construction path for the application.
    Alternatives: Instantiate services directly within the CLI entrypoint.
    """

    store = SqliteStore(config.db_path)
    store.initialize()
    user = User(display_name=config.default_user_name, email=config.default_user_email)
    user_id = store.ensure_user(user)
    ai_provider = AiProviderFactory(config).build()
    classifier = RuleBasedClassifier()
    if config.ai_provider == "openai":
        model_name = config.openai_model
    elif config.ai_provider == "ollama":
        model_name = config.ollama_model
    else:
        model_name = "mock"
    ingestion = IngestionService(store=store, user_id=user_id)
    categories = CategoryService(
        store=store,
        classifier=classifier,
        ai_provider=ai_provider,
        provider_name=config.ai_provider,
        model_name=model_name,
        user_id=user_id,
    )
    meetings = MeetingService(store=store, user_id=user_id)
    chat = ChatService(
        store=store,
        ai_provider=ai_provider,
        provider_name=config.ai_provider,
        model_name=model_name,
        user_id=user_id,
    )
    tasks = TaskService(
        store=store,
        ai_provider=ai_provider,
        provider_name=config.ai_provider,
        model_name=model_name,
        user_id=user_id,
    )
    meeting_notes = MeetingSummaryService(
        store=store,
        ai_provider=ai_provider,
        provider_name=config.ai_provider,
        model_name=model_name,
        user_id=user_id,
    )
    connections = ConnectionService(store=store, user_id=user_id)
    stats = StatsService(store=store, user_id=user_id)
    triage = TriageService(
        store=store,
        user_id=user_id,
        high_keywords=config.triage_high_keywords,
        medium_keywords=config.triage_medium_keywords,
    )
    message_insights = MessageInsightsService(
        store=store,
        ai_provider=ai_provider,
        provider_name=config.ai_provider,
        model_name=model_name,
        user_id=user_id,
    )
    tokens = TokenService(store=store, user_id=user_id, codec=TokenCodec(config.token_secret))
    return AppServices(
        ingestion=ingestion,
        meetings=meetings,
        categories=categories,
        chat=chat,
        tasks=tasks,
        meeting_notes=meeting_notes,
        connections=connections,
        stats=stats,
        triage=triage,
        message_insights=message_insights,
        tokens=tokens,
        store=store,
        user_id=user_id,
    )
