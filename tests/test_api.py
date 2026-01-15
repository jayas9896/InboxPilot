"""Summary: API integration tests.

Importance: Validates FastAPI endpoints against core workflows.
Alternatives: Use manual curl testing only.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from inboxpilot.api import create_app
from inboxpilot.config import AppConfig


def _build_config(db_path: str) -> AppConfig:
    """Summary: Build an AppConfig for API tests.

    Importance: Ensures tests use isolated storage.
    Alternatives: Load AppConfig from environment variables.
    """

    return AppConfig(
        db_path=db_path,
        ai_provider="mock",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        ollama_url="http://localhost:11434",
        ollama_model="llama3",
        imap_host=None,
        imap_user=None,
        imap_password=None,
        imap_mailbox="INBOX",
        api_host="127.0.0.1",
        api_port=8000,
    )


def test_api_ingest_and_list_messages(tmp_path: Path) -> None:
    """Summary: Verify API can ingest and list messages.

    Importance: Confirms the HTTP layer wires into ingestion and storage.
    Alternatives: Validate only the CLI ingestion workflow.
    """

    fixture = tmp_path / "mock_messages.json"
    fixture.write_text(
        """
        [
          {
            "provider_message_id": "api-1",
            "subject": "Hello",
            "sender": "from@example.com",
            "recipients": "to@example.com",
            "timestamp": "2026-01-15T10:00:00",
            "snippet": "Hello",
            "body": "Hello from API"
          }
        ]
        """.strip(),
        encoding="utf-8",
    )
    config = _build_config(str(tmp_path / "test.db"))
    client = TestClient(create_app(config))
    response = client.post("/ingest/mock", json={"limit": 1, "fixture_path": str(fixture)})
    assert response.status_code == 200
    list_response = client.get("/messages")
    assert list_response.status_code == 200
    assert list_response.json()[0]["subject"] == "Hello"


def test_api_categories_and_templates(tmp_path: Path) -> None:
    """Summary: Verify category endpoints and template listing.

    Importance: Ensures category management works over HTTP.
    Alternatives: Use CLI-only category management.
    """

    config = _build_config(str(tmp_path / "test.db"))
    client = TestClient(create_app(config))
    create_response = client.post("/categories", json={"name": "Recruiting"})
    assert create_response.status_code == 200
    list_response = client.get("/categories")
    assert list_response.status_code == 200
    assert list_response.json()[0]["name"] == "Recruiting"
    templates_response = client.get("/templates")
    assert templates_response.status_code == 200
    assert templates_response.json()


def test_api_category_suggestions(tmp_path: Path) -> None:
    """Summary: Verify category suggestion endpoint responds.

    Importance: Ensures AI/category suggestion workflow is exposed via HTTP.
    Alternatives: Use CLI-only suggestions.
    """

    fixture = tmp_path / "mock_messages.json"
    fixture.write_text(
        """
        [
          {
            "provider_message_id": "api-2",
            "subject": "Interview schedule",
            "sender": "from@example.com",
            "recipients": "to@example.com",
            "timestamp": "2026-01-15T10:00:00",
            "snippet": "Interview schedule",
            "body": "Interview schedule for next week."
          }
        ]
        """.strip(),
        encoding="utf-8",
    )
    config = _build_config(str(tmp_path / "test.db"))
    client = TestClient(create_app(config))
    ingest_response = client.post(
        "/ingest/mock", json={"limit": 1, "fixture_path": str(fixture)}
    )
    assert ingest_response.status_code == 200
    category_response = client.post("/categories", json={"name": "Interview"})
    assert category_response.status_code == 200
    suggest_response = client.post("/categories/suggest", json={"message_id": 1})
    assert suggest_response.status_code == 200
    assert suggest_response.json()


def test_api_tasks(tmp_path: Path) -> None:
    """Summary: Verify task endpoints work over HTTP.

    Importance: Ensures action items can be managed via the API.
    Alternatives: Use CLI-only task workflows.
    """

    config = _build_config(str(tmp_path / "test.db"))
    client = TestClient(create_app(config))
    task_response = client.post(
        "/tasks",
        json={"parent_type": "message", "parent_id": 1, "description": "Follow up"},
    )
    assert task_response.status_code == 200
    list_response = client.get("/tasks", params={"parent_type": "message", "parent_id": 1})
    assert list_response.status_code == 200
    assert list_response.json()[0]["description"] == "Follow up"


def test_api_meeting_summary(tmp_path: Path) -> None:
    """Summary: Verify meeting transcript and summary endpoints.

    Importance: Ensures meeting notes can be generated via HTTP.
    Alternatives: Summarize meetings only via CLI.
    """

    fixture = tmp_path / "mock_meetings.json"
    fixture.write_text(
        """
        [
          {
            "provider_event_id": "meet-1",
            "title": "Sync",
            "participants": "a@example.com",
            "start_time": "2026-01-15T10:00:00",
            "end_time": "2026-01-15T10:30:00",
            "transcript_ref": null
          }
        ]
        """.strip(),
        encoding="utf-8",
    )
    config = _build_config(str(tmp_path / "test.db"))
    client = TestClient(create_app(config))
    ingest_response = client.post(
        "/ingest/calendar-mock", json={"limit": 1, "fixture_path": str(fixture)}
    )
    assert ingest_response.status_code == 200
    transcript_response = client.post(
        "/meetings/transcript",
        json={"meeting_id": 1, "content": "We agreed to ship on Friday."},
    )
    assert transcript_response.status_code == 200
    summary_response = client.post("/meetings/summary", json={"meeting_id": 1})
    assert summary_response.status_code == 200
