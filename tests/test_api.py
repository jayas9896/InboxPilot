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
        default_user_name="Local User",
        default_user_email="local@inboxpilot",
        api_key="",
        google_client_id="",
        google_client_secret="",
        microsoft_client_id="",
        microsoft_client_secret="",
        oauth_redirect_uri="http://localhost:8000/oauth/callback",
        triage_high_keywords=["urgent"],
        triage_medium_keywords=["review"],
        token_secret="secret",
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


def test_api_search_messages(tmp_path: Path) -> None:
    """Summary: Verify message search endpoint works.

    Importance: Ensures contextual search is available via HTTP.
    Alternatives: Use AI chat only for discovery.
    """

    fixture = tmp_path / "mock_messages.json"
    fixture.write_text(
        """
        [
          {
            "provider_message_id": "search-1",
            "subject": "Project update",
            "sender": "from@example.com",
            "recipients": "to@example.com",
            "timestamp": "2026-01-15T10:00:00",
            "snippet": "Update",
            "body": "Project update details."
          }
        ]
        """.strip(),
        encoding="utf-8",
    )
    config = _build_config(str(tmp_path / "test.db"))
    client = TestClient(create_app(config))
    client.post("/ingest/mock", json={"limit": 1, "fixture_path": str(fixture)})
    response = client.get("/messages/search", params={"query": "Project"})
    assert response.status_code == 200
    assert response.json()[0]["subject"] == "Project update"


def test_api_search_meetings(tmp_path: Path) -> None:
    """Summary: Verify meeting search endpoint works.

    Importance: Ensures meeting discovery is available via HTTP.
    Alternatives: Use list_meetings only.
    """

    fixture = tmp_path / "mock_meetings.json"
    fixture.write_text(
        """
        [
          {
            "provider_event_id": "meet-1",
            "title": "Project kickoff",
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
    client.post("/ingest/calendar-mock", json={"limit": 1, "fixture_path": str(fixture)})
    response = client.get("/meetings/search", params={"query": "Project"})
    assert response.status_code == 200
    assert response.json()[0]["title"] == "Project kickoff"


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
    task_id = task_response.json()["id"]
    update_response = client.post("/tasks/update", json={"task_id": task_id, "status": "done"})
    assert update_response.status_code == 200
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


def test_api_meeting_transcript_file(tmp_path: Path) -> None:
    """Summary: Verify transcript file ingestion endpoint.

    Importance: Ensures transcript uploads can be ingested from file paths.
    Alternatives: Use paste-based transcripts only.
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
    transcript = tmp_path / "transcript.txt"
    transcript.write_text("We agreed on next steps.", encoding="utf-8")
    config = _build_config(str(tmp_path / "test.db"))
    client = TestClient(create_app(config))
    client.post("/ingest/calendar-mock", json={"limit": 1, "fixture_path": str(fixture)})
    response = client.post(
        "/meetings/transcript-file",
        json={"meeting_id": 1, "path": str(transcript)},
    )
    assert response.status_code == 200


def test_api_connections(tmp_path: Path) -> None:
    """Summary: Verify connection endpoints work over HTTP.

    Importance: Ensures integration records are managed via the API.
    Alternatives: Use CLI-only connection workflows.
    """

    config = _build_config(str(tmp_path / "test.db"))
    client = TestClient(create_app(config))
    create_response = client.post(
        "/connections",
        json={
            "provider_type": "email",
            "provider_name": "gmail",
            "status": "connected",
            "details": "read-only",
        },
    )
    assert create_response.status_code == 200
    list_response = client.get("/connections")
    assert list_response.status_code == 200
    assert list_response.json()[0]["provider_name"] == "gmail"


def test_api_stats(tmp_path: Path) -> None:
    """Summary: Verify stats endpoint returns counts.

    Importance: Ensures dashboard metrics are exposed via the API.
    Alternatives: Use client-side counting only.
    """

    config = _build_config(str(tmp_path / "test.db"))
    client = TestClient(create_app(config))
    response = client.get("/stats")
    assert response.status_code == 200
    payload = response.json()
    assert "messages" in payload


def test_api_triage(tmp_path: Path) -> None:
    """Summary: Verify triage endpoint returns prioritized messages.

    Importance: Ensures triage data is available to the UI.
    Alternatives: Compute triage client-side only.
    """

    config = _build_config(str(tmp_path / "test.db"))
    client = TestClient(create_app(config))
    fixture = tmp_path / "mock_messages.json"
    fixture.write_text(
        """
        [
          {
            "provider_message_id": "triage-1",
            "subject": "Urgent follow up",
            "sender": "boss@example.com",
            "recipients": "you@example.com",
            "timestamp": "2026-01-15T10:00:00",
            "snippet": "Urgent follow up",
            "body": "Action required ASAP."
          }
        ]
        """.strip(),
        encoding="utf-8",
    )
    client.post("/ingest/mock", json={"limit": 1, "fixture_path": str(fixture)})
    response = client.get("/triage")
    assert response.status_code == 200
    assert response.json()[0]["priority"] in {"high", "medium", "low"}


def test_api_message_insights(tmp_path: Path) -> None:
    """Summary: Verify message summary and follow-up endpoints.

    Importance: Ensures message insights are exposed via the API.
    Alternatives: Use CLI-only message insights.
    """

    fixture = tmp_path / "mock_messages.json"
    fixture.write_text(
        """
        [
          {
            "provider_message_id": "insight-1",
            "subject": "Question",
            "sender": "from@example.com",
            "recipients": "to@example.com",
            "timestamp": "2026-01-15T10:00:00",
            "snippet": "Question",
            "body": "Can you share availability?"
          }
        ]
        """.strip(),
        encoding="utf-8",
    )
    config = _build_config(str(tmp_path / "test.db"))
    client = TestClient(create_app(config))
    client.post("/ingest/mock", json={"limit": 1, "fixture_path": str(fixture)})
    summary_response = client.post("/messages/summary", json={"message_id": 1})
    assert summary_response.status_code == 200
    follow_up_response = client.post("/messages/follow-up", json={"message_id": 1})
    assert follow_up_response.status_code == 200


def test_api_ai_audit(tmp_path: Path) -> None:
    """Summary: Verify AI audit endpoints respond.

    Importance: Ensures AI audit data is exposed via the API.
    Alternatives: Use database access for audits.
    """

    config = _build_config(str(tmp_path / "test.db"))
    client = TestClient(create_app(config))
    response = client.get("/ai/requests")
    assert response.status_code == 200


def test_api_oauth_callback(tmp_path: Path) -> None:
    """Summary: Verify OAuth callback records a connection.

    Importance: Ensures OAuth flow tracking is functional.
    Alternatives: Skip callback handling until token exchange is added.
    """

    config = _build_config(str(tmp_path / "test.db"))
    client = TestClient(create_app(config))
    oauth_response = client.get("/oauth/google")
    assert oauth_response.status_code == 200
    state = oauth_response.json()["state"]
    callback = client.get("/oauth/callback", params={"provider": "google", "code": "abc", "state": state})
    assert callback.status_code == 200
    connections = client.get("/connections")
    assert connections.status_code == 200
    assert connections.json()[0]["provider_name"] == "google"


def test_api_notes(tmp_path: Path) -> None:
    """Summary: Verify notes endpoints work over HTTP.

    Importance: Ensures notes are retrievable for UI clients.
    Alternatives: Use CLI-only notes.
    """

    config = _build_config(str(tmp_path / "test.db"))
    client = TestClient(create_app(config))
    create_response = client.post(
        "/notes",
        json={"parent_type": "message", "parent_id": 1, "content": "Follow up"},
    )
    assert create_response.status_code == 200
    list_response = client.get("/notes", params={"parent_type": "message", "parent_id": 1})
    assert list_response.status_code == 200
    assert list_response.json()[0]["content"] == "Follow up"
