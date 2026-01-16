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
    ApiKeyService,
    CategoryService,
    ChatService,
    ConnectionService,
    IngestionService,
    MessageInsightsService,
    MeetingService,
    MeetingSummaryService,
    AiAuditService,
    StatsService,
    TriageService,
    TokenService,
    TaskService,
    UserService,
)
from inboxpilot.storage.sqlite_store import SqliteStore
from inboxpilot.token_codec import TokenCodec


@dataclass(frozen=True)
class AppContext:
    """Summary: Shared application context for building user services.

    Importance: Reuses storage and AI provider across user-bound services.
    Alternatives: Rebuild dependencies for every request.
    """

    store: SqliteStore
    ai_provider: object
    model_name: str
    config: AppConfig

    def services_for_user(self, user_id: int) -> "AppServices":
        """Summary: Build user-scoped services from shared context.

        Importance: Enables per-user API tokens and data boundaries.
        Alternatives: Use a multi-tenant database with row-level security.
        """

        ingestion = IngestionService(store=self.store, user_id=user_id)
        categories = CategoryService(
            store=self.store,
            classifier=RuleBasedClassifier(),
            ai_provider=self.ai_provider,
            provider_name=self.config.ai_provider,
            model_name=self.model_name,
            user_id=user_id,
        )
        meetings = MeetingService(store=self.store, user_id=user_id)
        chat = ChatService(
            store=self.store,
            ai_provider=self.ai_provider,
            provider_name=self.config.ai_provider,
            model_name=self.model_name,
            user_id=user_id,
        )
        tasks = TaskService(
            store=self.store,
            ai_provider=self.ai_provider,
            provider_name=self.config.ai_provider,
            model_name=self.model_name,
            user_id=user_id,
        )
        meeting_notes = MeetingSummaryService(
            store=self.store,
            ai_provider=self.ai_provider,
            provider_name=self.config.ai_provider,
            model_name=self.model_name,
            user_id=user_id,
        )
        connections = ConnectionService(store=self.store, user_id=user_id)
        stats = StatsService(store=self.store, user_id=user_id)
        triage = TriageService(
            store=self.store,
            user_id=user_id,
            high_keywords=self.config.triage_high_keywords,
            medium_keywords=self.config.triage_medium_keywords,
        )
        message_insights = MessageInsightsService(
            store=self.store,
            ai_provider=self.ai_provider,
            provider_name=self.config.ai_provider,
            model_name=self.model_name,
            user_id=user_id,
        )
        tokens = TokenService(
            store=self.store,
            user_id=user_id,
            codec=TokenCodec(self.config.token_secret),
            config=self.config,
        )
        ai_audit = AiAuditService(store=self.store, user_id=user_id)
        users = UserService(store=self.store)
        api_keys = ApiKeyService(store=self.store, token_secret=self.config.token_secret)
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
            ai_audit=ai_audit,
            users=users,
            api_keys=api_keys,
            store=self.store,
            user_id=user_id,
        )


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
    ai_audit: AiAuditService
    users: UserService
    api_keys: ApiKeyService
    store: SqliteStore
    user_id: int




def build_context(config: AppConfig) -> AppContext:
    """Summary: Build shared context for user-scoped services.

    Importance: Reuses storage and AI provider across user sessions.
    Alternatives: Construct dependencies separately per request.
    """

    store = SqliteStore(config.db_path)
    store.initialize()
    ai_provider = AiProviderFactory(config).build()
    if config.ai_provider == "openai":
        model_name = config.openai_model
    elif config.ai_provider == "ollama":
        model_name = config.ollama_model
    else:
        model_name = "mock"
    return AppContext(store=store, ai_provider=ai_provider, model_name=model_name, config=config)


def build_services(config: AppConfig) -> AppServices:
    """Summary: Build core services from configuration.

    Importance: Provides a single construction path for the application.
    Alternatives: Instantiate services directly within the CLI entrypoint.
    """

    context = build_context(config)
    user = User(display_name=config.default_user_name, email=config.default_user_email)
    user_id = context.store.ensure_user(user)
    return context.services_for_user(user_id)
