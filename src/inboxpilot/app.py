"""Summary: Application factory wiring core services.

Importance: Centralizes dependency creation for CLI and future API layers.
Alternatives: Instantiate services manually in each entrypoint.
"""

from __future__ import annotations

from dataclasses import dataclass

from inboxpilot.ai import AiProviderFactory
from inboxpilot.classifier import RuleBasedClassifier
from inboxpilot.config import AppConfig
from inboxpilot.services import (
    CategoryService,
    ChatService,
    IngestionService,
    MeetingService,
    MeetingSummaryService,
    TaskService,
)
from inboxpilot.storage.sqlite_store import SqliteStore


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
    store: SqliteStore


def build_services(config: AppConfig) -> AppServices:
    """Summary: Build core services from configuration.

    Importance: Provides a single construction path for the application.
    Alternatives: Instantiate services directly within the CLI entrypoint.
    """

    store = SqliteStore(config.db_path)
    store.initialize()
    ai_provider = AiProviderFactory(config).build()
    classifier = RuleBasedClassifier()
    ingestion = IngestionService(store)
    categories = CategoryService(store=store, classifier=classifier)
    meetings = MeetingService(store=store)
    if config.ai_provider == "openai":
        model_name = config.openai_model
    elif config.ai_provider == "ollama":
        model_name = config.ollama_model
    else:
        model_name = "mock"
    chat = ChatService(
        store=store,
        ai_provider=ai_provider,
        provider_name=config.ai_provider,
        model_name=model_name,
    )
    tasks = TaskService(
        store=store,
        ai_provider=ai_provider,
        provider_name=config.ai_provider,
        model_name=model_name,
    )
    meeting_notes = MeetingSummaryService(
        store=store,
        ai_provider=ai_provider,
        provider_name=config.ai_provider,
        model_name=model_name,
    )
    return AppServices(
        ingestion=ingestion,
        meetings=meetings,
        categories=categories,
        chat=chat,
        tasks=tasks,
        meeting_notes=meeting_notes,
        store=store,
    )
