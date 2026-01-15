# Tech Stack Proposal

## Recommended MVP Stack
- Language: Python 3.11
  - Reason: fast iteration, strong ecosystem for email/AI/CLI tooling.
- API/Service Layer: FastAPI (optional for HTTP API)
  - Reason: lightweight, async-friendly, easily containerized; can be added after CLI MVP.
- Storage: SQLite for local-first, with a clear path to Postgres.
  - Reason: zero-config for local, portable schema.
- ORM/DB Access: SQLite via standard library (sqlite3) for MVP.
  - Reason: minimal dependencies; swap to SQLAlchemy later if needed.
- AI Providers: local (Ollama) and cloud (OpenAI/Anthropic) via a unified interface.
  - Reason: keeps vendor-specific code isolated.
- Testing: pytest
  - Reason: standard for Python with clear fixtures.
- Linting: Ruff
  - Reason: fast, handles docstring enforcement and style checks.

## Easy Replacements
- SQLite -> Postgres/MySQL for multi-user or cloud deployments.
- CLI -> FastAPI + Web UI for richer experience.
- Requests/urllib -> provider SDKs once vendor stability is needed.

## Portability Principles
- No hard dependency on a single cloud service.
- Infrastructure adapters hide storage and queue differences.
