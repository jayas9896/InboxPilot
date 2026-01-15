# System Architecture

## Overview
InboxPilot is a local-first personal communication assistant with modular integrations for email, calendars, AI providers, and storage. The system is designed to run on a single machine, scale to a private cloud, and later migrate to hyperscale providers behind clean abstractions.

## Core Components
- Client Interface (CLI/Web): Chat-style entry point for search, drafts, and explanations.
- HTTP API: FastAPI layer for UI clients and integrations.
- Email Integration: Read-only connectors (IMAP or provider APIs) that ingest metadata and message bodies.
- Calendar Integration: Read-only connectors that ingest meetings, participants, and transcripts when available.
- Category System: First-class category model, templates, and assignment logic (manual and AI-assisted).
- Task & Follow-up System: Structured action items linked to messages or meetings.
- Meeting Notes: Transcript storage and AI summarization into notes.
- AI Abstraction Layer: A provider interface that routes to local or cloud LLMs without vendor-specific coupling.
- Storage Layer: Local SQL database with room for later migration to managed SQL and object storage.
- Background Workers (optional): Periodic ingestion, classification, and summarization tasks.
- Observability: Structured logs for ingestion and AI events, plus lightweight metrics.

## Data Flow
1. User connects an email provider in read-only mode.
2. Email integration ingests message metadata and bodies into storage.
3. Category system suggests or assigns categories to messages and threads.
4. User interacts with chat interface to search, summarize, and draft replies.
5. AI abstraction handles summarization and drafting with either local or cloud models.
6. Notes and action items are stored and linked to emails or meetings.

## Boundaries and Interfaces
- EmailProvider: list messages, fetch message bodies, list threads.
- CalendarProvider: list meetings, fetch meeting details.
- AiProvider: generate summaries, drafts, and classification suggestions.
- Storage: CRUD for messages, categories, notes, tasks, and AI audit logs.

## Deployment Modes
- Local-first: single process, SQLite, optional local LLM.
- Private cloud: containerized services with a shared SQL database and object storage.
- Hyperscale: replace storage and queues via adapters without app changes.
