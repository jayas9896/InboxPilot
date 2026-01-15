"""Summary: Command-line interface for InboxPilot.

Importance: Provides a local-first entry point for MVP workflows.
Alternatives: Build a web UI or desktop client first.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from inboxpilot.app import build_services
from inboxpilot.calendar import MockCalendarProvider
from inboxpilot.category_templates import list_templates, load_template
from inboxpilot.config import AppConfig
from inboxpilot.email import ImapEmailProvider, MockEmailProvider


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

    ingest_calendar = subparsers.add_parser("ingest-calendar-mock", help="Ingest mock meetings")
    ingest_calendar.add_argument("--limit", type=int, default=5)
    ingest_calendar.add_argument(
        "--fixture", type=str, default=str(Path("data") / "mock_meetings.json")
    )

    add_category = subparsers.add_parser("add-category", help="Create a category")
    add_category.add_argument("name", type=str)
    add_category.add_argument("--description", type=str, default=None)

    subparsers.add_parser("list-templates", help="List category templates")
    load_templates = subparsers.add_parser("load-template", help="Load a category template")
    load_templates.add_argument("template_name", type=str)

    subparsers.add_parser("list-categories", help="List categories")

    list_messages = subparsers.add_parser("list-messages", help="List messages")
    list_messages.add_argument("--limit", type=int, default=10)

    list_meetings = subparsers.add_parser("list-meetings", help="List meetings")
    list_meetings.add_argument("--limit", type=int, default=10)

    assign_category = subparsers.add_parser("assign-category", help="Assign category")
    assign_category.add_argument("message_id", type=int)
    assign_category.add_argument("category_id", type=int)

    chat = subparsers.add_parser("chat", help="Ask a question about your inbox")
    chat.add_argument("query", type=str)

    draft = subparsers.add_parser("draft", help="Draft a reply")
    draft.add_argument("message_id", type=int)
    draft.add_argument("instructions", type=str)

    note = subparsers.add_parser("add-note", help="Add a note to a message")
    note.add_argument("message_id", type=int)
    note.add_argument("content", type=str)

    add_task = subparsers.add_parser("add-task", help="Add a task to a message")
    add_task.add_argument("message_id", type=int)
    add_task.add_argument("description", type=str)

    list_tasks = subparsers.add_parser("list-tasks", help="List tasks for a message")
    list_tasks.add_argument("message_id", type=int)

    extract_tasks = subparsers.add_parser(
        "extract-tasks", help="Extract tasks from a message using AI"
    )
    extract_tasks.add_argument("message_id", type=int)

    return parser


def run_cli() -> None:
    """Summary: Execute CLI commands based on arguments.

    Importance: Drives the MVP user experience without a UI.
    Alternatives: Invoke services via an HTTP API.
    """

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

    if args.command == "ingest-calendar-mock":
        provider = MockCalendarProvider(Path(args.fixture))
        meetings = provider.fetch_upcoming(args.limit)
        ids = services.meetings.ingest_meetings(meetings)
        print(f"Ingested {len(ids)} meetings from mock fixture.")
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
        created = load_template(services.store, args.template_name)
        print(f"Loaded {created} categories from template.")
        return

    if args.command == "list-categories":
        for category in services.store.list_categories():
            print(f"{category.id}: {category.name} - {category.description or ''}")
        return

    if args.command == "list-messages":
        for message in services.store.list_messages(args.limit):
            print(f"{message.id}: {message.subject} ({message.sender})")
        return

    if args.command == "list-meetings":
        for meeting in services.meetings.list_meetings(args.limit):
            print(f"{meeting.id}: {meeting.title} ({meeting.start_time})")
        return

    if args.command == "assign-category":
        services.categories.assign_category(args.message_id, args.category_id)
        print("Category assigned.")
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
        note_id = services.chat.add_note("message", args.message_id, args.content)
        print(f"Added note {note_id}.")
        return

    if args.command == "add-task":
        task_id = services.tasks.add_task("message", args.message_id, args.description)
        print(f"Added task {task_id}.")
        return

    if args.command == "list-tasks":
        tasks = services.tasks.list_tasks("message", args.message_id)
        for task in tasks:
            print(f"{task.id}: {task.description} [{task.status}]")
        return

    if args.command == "extract-tasks":
        task_ids = services.tasks.extract_tasks_from_message(args.message_id)
        print(f"Extracted {len(task_ids)} tasks.")
        return


if __name__ == "__main__":
    run_cli()
