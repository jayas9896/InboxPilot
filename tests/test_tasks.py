"""Summary: Tests for task storage and extraction.

Importance: Ensures action items can be stored and extracted.
Alternatives: Validate tasks manually through the CLI.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from inboxpilot.ai import MockAiProvider
from inboxpilot.models import Message, Task
from inboxpilot.services import TaskService
from inboxpilot.storage.sqlite_store import SqliteStore


def _seed_message(store: SqliteStore) -> int:
    """Summary: Seed a message for task extraction tests.

    Importance: Provides stable test data without external dependencies.
    Alternatives: Use fixtures or factory libraries.
    """

    message = Message(
        provider_message_id="task-1",
        subject="Next steps",
        sender="owner@example.com",
        recipients="you@example.com",
        timestamp=datetime.utcnow(),
        snippet="Please do these",
        body="Please update the deck and send the revised version.",
    )
    return store.save_messages([message])[0]


def test_task_storage(tmp_path: Path) -> None:
    """Summary: Verify tasks are saved and listed.

    Importance: Confirms storage layer supports action items.
    Alternatives: Store tasks as notes.
    """

    store = SqliteStore(str(tmp_path / "test.db"))
    store.initialize()
    task = Task(parent_type="message", parent_id=1, description="Follow up")
    task_id = store.add_task(task)
    tasks = store.list_tasks("message", 1)
    assert task_id > 0
    assert tasks[0].description == "Follow up"


def test_task_extraction_creates_tasks(tmp_path: Path) -> None:
    """Summary: Verify task extraction uses AI and stores results.

    Importance: Ensures AI extraction produces stored tasks.
    Alternatives: Only allow manual task entry.
    """

    store = SqliteStore(str(tmp_path / "test.db"))
    store.initialize()
    message_id = _seed_message(store)
    service = TaskService(
        store=store,
        ai_provider=MockAiProvider(),
        provider_name="mock",
        model_name="mock",
    )
    task_ids = service.extract_tasks_from_message(message_id)
    assert task_ids
    tasks = store.list_tasks("message", message_id)
    assert tasks
