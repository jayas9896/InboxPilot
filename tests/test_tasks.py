"""Summary: Tests for task storage and extraction.

Importance: Ensures action items can be stored and extracted.
Alternatives: Validate tasks manually through the CLI.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from inboxpilot.ai import MockAiProvider
from inboxpilot.models import Message, Task, User
from inboxpilot.services import TaskService
from inboxpilot.storage.sqlite_store import SqliteStore


def _seed_message(store: SqliteStore, user_id: int) -> int:
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
    return store.save_messages([message], user_id=user_id)[0]


def test_task_storage(tmp_path: Path) -> None:
    """Summary: Verify tasks are saved and listed.

    Importance: Confirms storage layer supports action items.
    Alternatives: Store tasks as notes.
    """

    store = SqliteStore(str(tmp_path / "test.db"))
    store.initialize()
    user_id = store.ensure_user(User(display_name="Local User", email="local@inboxpilot"))
    task = Task(parent_type="message", parent_id=1, description="Follow up")
    task_id = store.add_task(task, user_id=user_id)
    tasks = store.list_tasks("message", 1, user_id=user_id)
    assert task_id > 0
    assert tasks[0].description == "Follow up"


def test_task_extraction_creates_tasks(tmp_path: Path) -> None:
    """Summary: Verify task extraction uses AI and stores results.

    Importance: Ensures AI extraction produces stored tasks.
    Alternatives: Only allow manual task entry.
    """

    store = SqliteStore(str(tmp_path / "test.db"))
    store.initialize()
    user_id = store.ensure_user(User(display_name="Local User", email="local@inboxpilot"))
    message_id = _seed_message(store, user_id)
    service = TaskService(
        store=store,
        ai_provider=MockAiProvider(),
        provider_name="mock",
        model_name="mock",
        user_id=user_id,
    )
    task_ids = service.extract_tasks_from_message(message_id)
    assert task_ids
    tasks = store.list_tasks("message", message_id, user_id=user_id)
    assert tasks
