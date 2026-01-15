# InboxPilot

InboxPilot is a local-first personal communication assistant for email and meetings. It organizes messages into user-defined categories, explains context through a chat interface, and drafts replies while keeping the user in control.

Recruiter-friendly summary: InboxPilot is a privacy-aware inbox assistant that ingests email metadata, lets users define their own categorization system, and uses a pluggable AI layer to summarize and draft replies without auto-sending anything. The architecture is local-first with a clear upgrade path to private cloud and hyperscale deployments.

## Local Setup

### Prerequisites
- Python 3.11+

### Install
Create a `.env` file (already scaffolded) and edit values as needed. Do not commit secrets.

Install the package locally:
```
pip install -e .
```

For dev tools:
```
pip install -r requirements-dev.txt
```

### Run with Mock Data
```
python -m inboxpilot.cli ingest-mock --limit 3
python -m inboxpilot.cli list-messages
python -m inboxpilot.cli add-category Recruiting --description "Hiring workflow"
python -m inboxpilot.cli assign-category 1 1
python -m inboxpilot.cli ingest-calendar-mock --limit 2
python -m inboxpilot.cli list-meetings
python -m inboxpilot.cli chat "What emails need follow up?"
python -m inboxpilot.cli draft 1 "Thank them and ask for availability"
```

### Run with IMAP (Read-only)
Set environment variables:
- `INBOXPILOT_IMAP_HOST`
- `INBOXPILOT_IMAP_USER`
- `INBOXPILOT_IMAP_PASSWORD`
- `INBOXPILOT_IMAP_MAILBOX` (optional, default `INBOX`)

Then ingest:
```
python -m inboxpilot.cli ingest-imap --limit 10
```

## AI Providers
Set `INBOXPILOT_AI_PROVIDER` to:
- `mock` (default)
- `ollama` (requires local Ollama server)
- `openai` (requires `OPENAI_API_KEY`)

## Configuration
- All variables are defined in `config/defaults.json`.
- Secrets live in `.env` and override defaults via `src/inboxpilot/config.py`.

## Categories
- Categories are first-class objects stored in SQLite.
- You can create categories with or without descriptions.
- Manual assignment is supported via the CLI. AI-based suggestions are planned for future iterations.
- Starter templates are available with `list-templates` and `load-template`.

## Chat Assistant
- `chat` searches stored messages and uses the AI abstraction to answer questions.
- `draft` creates reply drafts but never sends emails.

## Repository Docs
- Architecture: `docs/architecture.md`
- Domain model: `docs/domain-model.md`
- Tech stack: `docs/tech-stack.md`
- Migration strategy: `docs/migration-strategy.md`
- Agile plan: `docs/agile-plan.md`
- Future work: `docs/future-work.md`
