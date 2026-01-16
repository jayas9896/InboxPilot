"""Summary: Command-line interface for InboxPilot.

Importance: Provides a local-first entry point for MVP workflows.
Alternatives: Build a web UI or desktop client first.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from inboxpilot.app import build_services
from inboxpilot.calendar import IcsCalendarProvider, MockCalendarProvider
from inboxpilot.category_templates import list_templates, load_template
from inboxpilot.config import AppConfig
from inboxpilot.email import EmlEmailProvider, GmailEmailProvider, ImapEmailProvider, MockEmailProvider, OutlookEmailProvider
from inboxpilot.oauth import build_google_auth_url, build_microsoft_auth_url, create_state_token


def build_parser() -> argparse.ArgumentParser:
    """Summary: Build the CLI argument parser.

    Importance: Defines supported commands for local operation.
    Alternatives: Use a CLI framework like Typer or Click.
    """

    parser = argparse.ArgumentParser(description="InboxPilot CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_mock = subparsers.add_parser("ingest-mock", help="Ingest mock emails")
    ingest_mock.add_argument("--limit", type=int, default=5)
    ingest_mock.add_argument(
        "--fixture", type=str, default=str(Path("data") / "mock_messages.json")
    )

    ingest_imap = subparsers.add_parser("ingest-imap", help="Ingest emails via IMAP")
    ingest_imap.add_argument("--limit", type=int, default=5)

    ingest_gmail = subparsers.add_parser("ingest-gmail", help="Ingest emails via Gmail OAuth")
    ingest_gmail.add_argument("--limit", type=int, default=5)

    ingest_outlook = subparsers.add_parser("ingest-outlook", help="Ingest emails via Outlook OAuth")
    ingest_outlook.add_argument("--limit", type=int, default=5)

    ingest_eml = subparsers.add_parser("ingest-eml", help="Ingest emails from .eml files")
    ingest_eml.add_argument("paths", nargs="+", type=str)
    ingest_eml.add_argument("--limit", type=int, default=25)

    ingest_calendar = subparsers.add_parser("ingest-calendar-mock", help="Ingest mock meetings")
    ingest_calendar.add_argument("--limit", type=int, default=5)
    ingest_calendar.add_argument(
        "--fixture", type=str, default=str(Path("data") / "mock_meetings.json")
    )

    ingest_calendar_ics = subparsers.add_parser("ingest-calendar-ics", help="Ingest meetings from .ics")
    ingest_calendar_ics.add_argument("path", type=str)
    ingest_calendar_ics.add_argument("--limit", type=int, default=25)

    add_category = subparsers.add_parser("add-category", help="Create a category")
    add_category.add_argument("name", type=str)
    add_category.add_argument("--description", type=str, default=None)

    subparsers.add_parser("list-templates", help="List category templates")
    load_templates = subparsers.add_parser("load-template", help="Load a category template")
    load_templates.add_argument("template_name", type=str)

    subparsers.add_parser("list-categories", help="List categories")

    list_messages = subparsers.add_parser("list-messages", help="List messages")
    list_messages.add_argument("--limit", type=int, default=10)

    search_messages = subparsers.add_parser("search", help="Search messages")
    search_messages.add_argument("query", type=str)
    search_messages.add_argument("--limit", type=int, default=10)

    list_meetings = subparsers.add_parser("list-meetings", help="List meetings")
    list_meetings.add_argument("--limit", type=int, default=10)

    search_meetings = subparsers.add_parser("search-meetings", help="Search meetings")
    search_meetings.add_argument("query", type=str)
    search_meetings.add_argument("--limit", type=int, default=10)

    assign_category = subparsers.add_parser("assign-category", help="Assign category")
    assign_category.add_argument("message_id", type=int)
    assign_category.add_argument("category_id", type=int)

    suggest_categories = subparsers.add_parser(
        "suggest-categories", help="Suggest categories using AI"
    )
    suggest_categories.add_argument("message_id", type=int)

    chat = subparsers.add_parser("chat", help="Ask a question about your inbox")
    chat.add_argument("query", type=str)

    draft = subparsers.add_parser("draft", help="Draft a reply")
    draft.add_argument("message_id", type=int)
    draft.add_argument("instructions", type=str)

    note = subparsers.add_parser("add-note", help="Add a note to a message or meeting")
    note.add_argument("parent_type", type=str)
    note.add_argument("parent_id", type=int)
    note.add_argument("content", type=str)

    list_notes = subparsers.add_parser("list-notes", help="List notes")
    list_notes.add_argument("parent_type", type=str)
    list_notes.add_argument("parent_id", type=int)

    add_task = subparsers.add_parser("add-task", help="Add a task to a message or meeting")
    add_task.add_argument("parent_type", type=str)
    add_task.add_argument("parent_id", type=int)
    add_task.add_argument("description", type=str)

    list_tasks = subparsers.add_parser("list-tasks", help="List tasks for a message or meeting")
    list_tasks.add_argument("parent_type", type=str)
    list_tasks.add_argument("parent_id", type=int)

    update_task = subparsers.add_parser("update-task", help="Update a task status")
    update_task.add_argument("task_id", type=int)
    update_task.add_argument("status", type=str)

    extract_tasks = subparsers.add_parser(
        "extract-tasks", help="Extract tasks from a message using AI"
    )
    extract_tasks.add_argument("message_id", type=int)

    add_transcript = subparsers.add_parser("add-meeting-transcript", help="Add meeting transcript")
    add_transcript.add_argument("meeting_id", type=int)
    add_transcript.add_argument("content", type=str)

    add_transcript_file = subparsers.add_parser(
        "add-meeting-transcript-file", help="Add meeting transcript from a file"
    )
    add_transcript_file.add_argument("meeting_id", type=int)
    add_transcript_file.add_argument("path", type=str)

    summarize_meeting = subparsers.add_parser(
        "summarize-meeting", help="Summarize a meeting transcript"
    )
    summarize_meeting.add_argument("meeting_id", type=int)

    extract_meeting_tasks = subparsers.add_parser(
        "extract-meeting-tasks", help="Extract tasks from a meeting transcript"
    )
    extract_meeting_tasks.add_argument("meeting_id", type=int)

    add_connection = subparsers.add_parser("add-connection", help="Add an integration record")
    add_connection.add_argument("provider_type", type=str)
    add_connection.add_argument("provider_name", type=str)
    add_connection.add_argument("status", type=str)
    add_connection.add_argument("--details", type=str, default=None)

    subparsers.add_parser("list-connections", help="List integration records")

    subparsers.add_parser("stats", help="Show inbox statistics")
    triage = subparsers.add_parser("triage", help="Show prioritized messages")
    triage.add_argument("--limit", type=int, default=20)

    summarize_message = subparsers.add_parser("summarize-message", help="Summarize a message")
    summarize_message.add_argument("message_id", type=int)

    follow_up = subparsers.add_parser("suggest-follow-up", help="Suggest a follow-up action")
    follow_up.add_argument("message_id", type=int)

    store_token = subparsers.add_parser("store-token", help="Store OAuth tokens")
    store_token.add_argument("provider_name", type=str)
    store_token.add_argument("access_token", type=str)
    store_token.add_argument("--refresh-token", type=str, default=None)
    store_token.add_argument("--expires-at", type=str, default=None)

    list_ai_requests = subparsers.add_parser("list-ai-requests", help="List AI requests")
    list_ai_requests.add_argument("--limit", type=int, default=20)

    list_ai_responses = subparsers.add_parser("list-ai-responses", help="List AI responses")
    list_ai_responses.add_argument("--limit", type=int, default=20)

    subparsers.add_parser("oauth-google", help="Print Google OAuth URL")
    subparsers.add_parser("oauth-microsoft", help="Print Microsoft OAuth URL")

    create_user = subparsers.add_parser("create-user", help="Create or ensure a user")
    create_user.add_argument("display_name", type=str)
    create_user.add_argument("email", type=str)

    subparsers.add_parser("list-users", help="List users")

    create_key = subparsers.add_parser("create-api-key", help="Create an API key for a user")
    create_key.add_argument("user_email", type=str)
    create_key.add_argument("--label", type=str, default=None)

    list_keys = subparsers.add_parser("list-api-keys", help="List API keys for a user")
    list_keys.add_argument("user_email", type=str)

    return parser


def run_cli() -> None:
    """Summary: Execute CLI commands based on arguments.

    Importance: Drives the MVP user experience without a UI.
    Alternatives: Invoke services via an HTTP API.
    """

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args()
    config = AppConfig.from_env()
    services = build_services(config)

    if args.command == "ingest-mock":
        provider = MockEmailProvider(Path(args.fixture))
        messages = provider.fetch_recent(args.limit)
        ids = services.ingestion.ingest_messages(messages)
        print(f"Ingested {len(ids)} messages from mock fixture.")
        return

    if args.command == "ingest-imap":
        if not (config.imap_host and config.imap_user and config.imap_password):
            raise ValueError("IMAP configuration missing in environment variables")
        provider = ImapEmailProvider(
            host=config.imap_host,
            user=config.imap_user,
            password=config.imap_password,
            mailbox=config.imap_mailbox,
        )
        messages = provider.fetch_recent(args.limit)
        ids = services.ingestion.ingest_messages(messages)
        print(f"Ingested {len(ids)} messages from IMAP.")
        return

    if args.command == "ingest-gmail":
        access_token = services.tokens.get_access_token("google")
        provider = GmailEmailProvider(access_token, config.google_api_base_url)
        messages = provider.fetch_recent(args.limit)
        ids = services.ingestion.ingest_messages(messages)
        print(f"Ingested {len(ids)} messages from Gmail API.")
        return

    if args.command == "ingest-outlook":
        access_token = services.tokens.get_access_token("microsoft")
        provider = OutlookEmailProvider(access_token, config.microsoft_graph_base_url)
        messages = provider.fetch_recent(args.limit)
        ids = services.ingestion.ingest_messages(messages)
        print(f"Ingested {len(ids)} messages from Outlook API.")
        return

    if args.command == "ingest-eml":
        provider = EmlEmailProvider([Path(path) for path in args.paths])
        messages = provider.fetch_recent(args.limit)
        ids = services.ingestion.ingest_messages(messages)
        print(f"Ingested {len(ids)} messages from .eml files.")
        return

    if args.command == "ingest-calendar-mock":
        provider = MockCalendarProvider(Path(args.fixture))
        meetings = provider.fetch_upcoming(args.limit)
        ids = services.meetings.ingest_meetings(meetings)
        print(f"Ingested {len(ids)} meetings from mock fixture.")
        return

    if args.command == "ingest-calendar-ics":
        provider = IcsCalendarProvider(Path(args.path))
        meetings = provider.fetch_upcoming(args.limit)
        ids = services.meetings.ingest_meetings(meetings)
        print(f"Ingested {len(ids)} meetings from iCalendar.")
        return

    if args.command == "add-category":
        category_id = services.categories.create_category(args.name, args.description)
        print(f"Created category {category_id} ({args.name}).")
        return

    if args.command == "list-templates":
        for template in list_templates():
            print(template.name)
        return

    if args.command == "load-template":
        created = load_template(services.store, args.template_name, user_id=services.user_id)
        print(f"Loaded {created} categories from template.")
        return

    if args.command == "list-categories":
        for category in services.store.list_categories(user_id=services.user_id):
            print(f"{category.id}: {category.name} - {category.description or ''}")
        return

    if args.command == "list-messages":
        for message in services.store.list_messages(args.limit, user_id=services.user_id):
            print(f"{message.id}: {message.subject} ({message.sender})")
        return

    if args.command == "search":
        results = services.store.search_messages(args.query, args.limit, user_id=services.user_id)
        for message in results:
            print(f"{message.id}: {message.subject} ({message.sender})")
        return

    if args.command == "list-meetings":
        for meeting in services.meetings.list_meetings(args.limit):
            print(f"{meeting.id}: {meeting.title} ({meeting.start_time})")
        return

    if args.command == "search-meetings":
        meetings = services.store.search_meetings(
            args.query, args.limit, user_id=services.user_id
        )
        for meeting in meetings:
            print(f"{meeting.id}: {meeting.title} ({meeting.start_time})")
        return

    if args.command == "assign-category":
        services.categories.assign_category(args.message_id, args.category_id)
        print("Category assigned.")
        return

    if args.command == "suggest-categories":
        suggestions = services.categories.suggest_categories_ai(args.message_id)
        if not suggestions:
            print("No suggestions.")
            return
        for category in suggestions:
            print(f"{category.name} - {category.description or ''}")
        return

    if args.command == "chat":
        answer = services.chat.answer(args.query)
        print(answer)
        return

    if args.command == "draft":
        draft_text = services.chat.draft_reply(args.message_id, args.instructions)
        print(draft_text)
        return

    if args.command == "add-note":
        note_id = services.chat.add_note(args.parent_type, args.parent_id, args.content)
        print(f"Added note {note_id}.")
        return

    if args.command == "list-notes":
        notes = services.store.list_notes(
            args.parent_type, args.parent_id, user_id=services.user_id
        )
        for note in notes:
            print(f"{note.parent_type}:{note.parent_id} {note.content}")
        return

    if args.command == "add-task":
        task_id = services.tasks.add_task(args.parent_type, args.parent_id, args.description)
        print(f"Added task {task_id}.")
        return

    if args.command == "list-tasks":
        tasks = services.tasks.list_tasks(args.parent_type, args.parent_id)
        for task in tasks:
            print(f"{task.id}: {task.description} [{task.status}]")
        return

    if args.command == "update-task":
        services.tasks.update_task_status(args.task_id, args.status)
        print("Task updated.")
        return

    if args.command == "extract-tasks":
        task_ids = services.tasks.extract_tasks_from_message(args.message_id)
        print(f"Extracted {len(task_ids)} tasks.")
        return

    if args.command == "add-meeting-transcript":
        services.meeting_notes.add_transcript(args.meeting_id, args.content)
        print("Meeting transcript saved.")
        return

    if args.command == "add-meeting-transcript-file":
        content = Path(args.path).read_text(encoding="utf-8")
        services.meeting_notes.add_transcript(args.meeting_id, content)
        print("Meeting transcript saved.")
        return

    if args.command == "summarize-meeting":
        note_id = services.meeting_notes.summarize_meeting(args.meeting_id)
        print(f"Created meeting note {note_id}.")
        return

    if args.command == "extract-meeting-tasks":
        task_ids = services.tasks.extract_tasks_from_meeting(args.meeting_id)
        print(f"Extracted {len(task_ids)} tasks.")
        return

    if args.command == "add-connection":
        connection_id = services.connections.add_connection(
            args.provider_type, args.provider_name, args.status, args.details
        )
        print(f"Added connection {connection_id}.")
        return

    if args.command == "list-connections":
        for connection in services.connections.list_connections():
            print(
                f"{connection.id}: {connection.provider_type}/{connection.provider_name} "
                f"{connection.status} ({connection.created_at})"
            )
        return

    if args.command == "stats":
        snapshot = services.stats.snapshot()
        for key, value in snapshot.items():
            print(f"{key}: {value}")
        return

    if args.command == "triage":
        ranked = services.triage.rank_messages(limit=args.limit)
        for item in ranked:
            print(f"{item['priority']}: #{item['id']} {item['subject']} ({item['sender']})")
        return

    if args.command == "summarize-message":
        note_id = services.message_insights.summarize_message(args.message_id)
        print(f"Created message summary note {note_id}.")
        return

    if args.command == "suggest-follow-up":
        suggestion = services.message_insights.suggest_follow_up(args.message_id)
        print(suggestion)
        return

    if args.command == "store-token":
        token_id = services.tokens.store_tokens(
            args.provider_name, args.access_token, args.refresh_token, args.expires_at
        )
        print(f"Stored token {token_id}.")
        return

    if args.command == "list-ai-requests":
        requests = services.ai_audit.list_requests(limit=args.limit)
        for request in requests:
            print(
                f"{request['id']}: {request['provider']} {request['model']} "
                f"{request['purpose']} {request['timestamp']}"
            )
        return

    if args.command == "list-ai-responses":
        responses = services.ai_audit.list_responses(limit=args.limit)
        for response in responses:
            print(
                f"{response['id']}: request {response['request_id']} "
                f"latency {response['latency_ms']}ms tokens {response['token_estimate']}"
            )
        return

    if args.command == "oauth-google":
        config = AppConfig.from_env()
        state = create_state_token()
        print(build_google_auth_url(config, state))
        return

    if args.command == "oauth-microsoft":
        config = AppConfig.from_env()
        state = create_state_token()
        print(build_microsoft_auth_url(config, state))
        return

    if args.command == "create-user":
        user_id = services.users.create_user(args.display_name, args.email)
        print(f"User {args.email} -> {user_id}")
        return

    if args.command == "list-users":
        for user in services.users.list_users():
            print(f"{user.id}: {user.display_name} <{user.email}>")
        return

    if args.command == "create-api-key":
        user = services.users.get_user_by_email(args.user_email)
        if not user:
            raise ValueError("User not found")
        key_id, token = services.api_keys.create_api_key(user.id, args.label)
        print(f"Key {key_id}: {token}")
        return

    if args.command == "list-api-keys":
        user = services.users.get_user_by_email(args.user_email)
        if not user:
            raise ValueError("User not found")
        keys = services.api_keys.list_api_keys(user.id)
        for key in keys:
            label = key.label or ""
            print(f"{key.id}: {label} ({key.created_at})")
        return


if __name__ == "__main__":
    run_cli()
