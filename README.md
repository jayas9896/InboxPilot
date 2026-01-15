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
python -m inboxpilot.cli suggest-categories 1
python -m inboxpilot.cli ingest-calendar-mock --limit 2
python -m inboxpilot.cli list-meetings
python -m inboxpilot.cli chat "What emails need follow up?"
python -m inboxpilot.cli draft 1 "Thank them and ask for availability"
python -m inboxpilot.cli add-task 1 "Send revised deck"
python -m inboxpilot.cli list-tasks 1
python -m inboxpilot.cli extract-tasks 1
python -m inboxpilot.cli add-meeting-transcript 1 "We agreed to ship on Friday."
python -m inboxpilot.cli summarize-meeting 1
python -m inboxpilot.cli extract-meeting-tasks 1
```

### Run the API (FastAPI)
Install runtime dependencies:
```
pip install -r requirements.txt
```

Start the server:
```
uvicorn inboxpilot.api:app --host 127.0.0.1 --port 8000
```

Open the local dashboard at `http://127.0.0.1:8000/`.

Example requests:
```
curl -X POST http://127.0.0.1:8000/ingest/mock -H "Content-Type: application/json" -d "{\"limit\":3}"
curl http://127.0.0.1:8000/messages
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
- Single-user mode uses `INBOXPILOT_DEFAULT_USER_NAME` and `INBOXPILOT_DEFAULT_USER_EMAIL`.

## Categories
- Categories are first-class objects stored in SQLite.
- You can create categories with or without descriptions.
- Manual assignment is supported via the CLI, and AI-based suggestions are available.
- Starter templates are available with `list-templates` and `load-template`.
- AI-based suggestions are available via `suggest-categories`.

## Chat Assistant
- `chat` searches stored messages and uses the AI abstraction to answer questions.
- `draft` creates reply drafts but never sends emails.
- `extract-tasks` extracts action items from a message and stores them as tasks.

## Repository Docs
- Architecture: `docs/architecture.md`
- Domain model: `docs/domain-model.md`
- Tech stack: `docs/tech-stack.md`
- Migration strategy: `docs/migration-strategy.md`
- Agile plan: `docs/agile-plan.md`
- Future work: `docs/future-work.md`
