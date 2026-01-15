# Initial Implementation Plan

## CL-0002: Architecture and planning docs
- Add architecture, domain model, tech stack, migration strategy.
- Add agile backlog and MVP definition.
- Update README with a recruiter-friendly summary.

## CL-0003: Core MVP implementation
- Implement AI abstraction layer with mock, local, and cloud adapters.
- Implement email ingestion via IMAP (read-only) plus a mock provider.
- Implement category system and basic rule-based classification.
- Implement storage layer (SQLite) for messages, categories, notes, and AI logs.
- Implement CLI chat interface for queries and drafting.
- Add pytest coverage for core services and AI abstraction.
- Add Ruff config for linting and docstring enforcement.

## CL-0004: Optional enhancements
- Add calendar integration mock and interface.
- Add template category packs.
- Add HTTP API layer (FastAPI) and web UI scaffolding.
