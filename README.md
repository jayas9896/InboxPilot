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
python -m inboxpilot.cli ingest-eml path\\to\\email.eml
python -m inboxpilot.cli list-messages
python -m inboxpilot.cli add-category Recruiting --description "Hiring workflow"
python -m inboxpilot.cli assign-category 1 1
python -m inboxpilot.cli suggest-categories 1
python -m inboxpilot.cli ingest-calendar-mock --limit 2
python -m inboxpilot.cli ingest-calendar-ics path\\to\\calendar.ics
python -m inboxpilot.cli list-meetings
python -m inboxpilot.cli chat "What emails need follow up?"
python -m inboxpilot.cli draft 1 "Thank them and ask for availability"
python -m inboxpilot.cli add-task 1 "Send revised deck"
python -m inboxpilot.cli list-tasks 1
python -m inboxpilot.cli update-task 1 done
python -m inboxpilot.cli extract-tasks 1
python -m inboxpilot.cli add-meeting-transcript 1 "We agreed to ship on Friday."
python -m inboxpilot.cli summarize-meeting 1
python -m inboxpilot.cli extract-meeting-tasks 1
python -m inboxpilot.cli list-notes message 1
python -m inboxpilot.cli add-connection email gmail connected --details "read-only"
python -m inboxpilot.cli list-connections
python -m inboxpilot.cli stats
python -m inboxpilot.cli triage --limit 10
python -m inboxpilot.cli summarize-message 1
python -m inboxpilot.cli suggest-follow-up 1
python -m inboxpilot.cli store-token google ACCESS_TOKEN --refresh-token REFRESH_TOKEN
python -m inboxpilot.cli oauth-google
python -m inboxpilot.cli oauth-microsoft
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
curl http://127.0.0.1:8000/stats
curl -X POST http://127.0.0.1:8000/ingest/calendar-ics -H "Content-Type: application/json" -d "{\"path\":\"C:\\\\path\\\\to\\\\calendar.ics\"}"
curl -X POST http://127.0.0.1:8000/ingest/eml -H "Content-Type: application/json" -d "{\"paths\":[\"C:\\\\path\\\\to\\\\email.eml\"]}"
curl http://127.0.0.1:8000/notes?parent_type=message&parent_id=1
curl http://127.0.0.1:8000/oauth/google
curl http://127.0.0.1:8000/oauth/microsoft
curl http://127.0.0.1:8000/triage
curl -X POST http://127.0.0.1:8000/messages/summary -H "Content-Type: application/json" -d "{\"message_id\":1}"
curl -X POST http://127.0.0.1:8000/messages/follow-up -H "Content-Type: application/json" -d "{\"message_id\":1}"
curl "http://127.0.0.1:8000/oauth/callback?provider=google&code=demo&state=STATE_FROM_OAUTH"
curl -X POST http://127.0.0.1:8000/tasks/update -H "Content-Type: application/json" -d "{\"task_id\":1,\"status\":\"done\"}"
curl -X POST http://127.0.0.1:8000/tokens -H "Content-Type: application/json" -d "{\"provider_name\":\"google\",\"access_token\":\"ACCESS\",\"refresh_token\":\"REFRESH\"}"
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
- Set `INBOXPILOT_API_KEY` to require `X-API-Key` for API requests.
- OAuth client IDs and secrets live in `.env` as `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `MICROSOFT_CLIENT_ID`, and `MICROSOFT_CLIENT_SECRET`.
- Set `INBOXPILOT_OAUTH_REDIRECT_URI` to match your OAuth app redirect URL.
- Triage keywords can be customized with `INBOXPILOT_TRIAGE_HIGH_KEYWORDS` and `INBOXPILOT_TRIAGE_MEDIUM_KEYWORDS`.
- OAuth callback at `/oauth/callback` records a connection without storing tokens.
- Store tokens using `INBOXPILOT_TOKEN_SECRET` (obfuscation only; replace with a real vault for production).

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
