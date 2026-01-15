SUPER PROMPT BEGIN

You are helping me design, scaffold, and implement an enterprise-grade yet user-friendly personal communication assistant, inspired by **Fyxer AI** but **better in scope, customization, privacy, and extensibility**.

## 1. Domain & Product Concept

**Project Name (placeholder):**  
`[PROJECT_NAME]` – e.g., `ChronicleAssistant`, `InboxPilot`, `ContextWeaver`.

**One-line description:**  
“[PROJECT_NAME] is a personal communication assistant for email and meetings that organizes, drafts, and explains communication in a customizable, user-defined category system, running locally first and scalable to private cloud or public cloud later.”

### 1.1 Core Domain Goals

The system must:

- Integrate with **email** (at minimum: Gmail and/or Outlook; more providers are optional).
- Integrate with **calendar / meetings** (Google Calendar, Outlook, etc.).
- Provide a **chat-style interface** to:
  - ask questions about emails and meetings,
  - search contextually,
  - generate drafts and follow-ups.
- Support:
  - smart inbox triage / prioritization,
  - meeting note creation (from live calls, uploads, or pasted transcripts),
  - follow-up suggestions,
  - task extraction (action items).

### 1.2 Customizable Category System (Key Differentiator)

This product must be **more flexible than Fyxer** in how it categorizes and structures work:

- Users can:
  - create **custom categories** for emails/threads/contacts:
    - with a description, or
    - with no description at all (just a label).
  - assign emails and meetings to:
    - one or multiple categories,
    - or let the AI infer categories.
  - change categories over time without breaking the underlying model or storage.
- The system must:
  - support pre-built category templates (e.g., Real Estate, Recruiting, Freelancing, Sales, Personal Life, etc.).
  - let users start generic and gradually specialize.

Categories are first-class objects in the domain model and must be deeply integrated into search, analytics, and future automation.

### 1.3 UX Reality Constraints

Design and implementation must respect real-life usage:

- Do **not** assume users will:
  - switch email clients,
  - move away from Gmail/Outlook,
  - log lots of data manually.
- Do **not** assume users will:
  - buy additional hardware,
  - run complex local clusters from day one.
- Do **not** assume users will:
  - accept brittle or confusing automation that sends messages without explicit confirmation.

The assistant should always behave like a **draft-first co-pilot**, not an autonomous agent that acts without user review.

---

## 2. Architecture & Tech Stack – Flexibility Rules

You are **not** allowed to hard-code a specific tech stack (e.g., Spring Boot, Kafka, etc.) as mandatory.

### 2.1 Stack Selection

- You **must**:
  - propose a recommended stack based on:
    - my skills where possible,
    - ease of implementation,
    - portability,
    - local-first development.
- You **must**:
  - justify your choices briefly (e.g., why this language/framework/db).
- You **must not**:
  - lock the architecture to any single vendor or cloud.

### 2.2 Deployment Model – Local → Hetzner → Hyperscale

The architecture must support three phases:

1. **Local-first**  
   - Runs on a single local machine (developer laptop or home PC).
   - Minimal dependency overhead.
   - Easy startup (one or few commands).

2. **Private Cloud (Hetzner) – Multi-node**  
   - Can be deployed to one or more Hetzner cloud servers.
   - Uses containers (e.g., Docker) and optionally orchestration (e.g., k3s/k8s/Nomad) as the project matures.
   - Uses **infrastructure-as-code** where possible for reproducibility.

3. **Optional Hyperscale Migration (AWS/Azure/GCP)**  
   - Avoid cloud-specific services unless behind abstraction layers (e.g., generic S3-compatible storage, generic message queues).
   - Document how to replace:
     - local DB with RDS/Cloud SQL,
     - local object store with S3/GCS,
     - local queue with SQS/PubSub/Kafka, etc.

**Requirement:**  
Architecture must be **portable**:
- no hard dependencies on specific managed services,
- clearly separated configuration for:
  - local,
  - Hetzner,
  - public cloud modes.

---

## 3. AI Model Strategy – Hybrid

You **must** design with **hybrid AI** in mind:

- **Cloud LLM support**:
  - OpenAI / Anthropic / Gemini / other cloud providers,
  - used for heavier reasoning, drafting, summarization.

- **Local LLM support**:
  - via something like Ollama, llama.cpp, or other local engines,
  - used for:
    - privacy-sensitive workloads,
    - offline capabilities,
    - future enterprise/self-hosted deployments.

### 3.1 AI Abstraction Layer

- All AI interactions must go through a **single abstraction layer**:
  - e.g., `AiProvider` interface / service module.
  - Able to:
    - switch providers,
    - mix providers (e.g., local for some tasks, cloud for others),
    - plug in new models in the future.

- No direct vendor-specific calls scattered across the codebase.

---

## 4. Single-User First → Multi-User Later (Option 3)

Implementation roadmap:

1. **MVP: Single-user instance**
   - One user on one environment (local or personal server).
   - Focus on:
     - inbox connection,
     - calendar connection,
     - meeting note assistance,
     - category system,
     - chat interface.

2. **Extension: Multi-user / Teams**
   - Add authentication, user profiles, and permissions.
   - Support:
     - multiple users on one deployment,
     - shared categories,
     - shared meeting notes and follow-ups (where appropriate).

You must design the data model so that multi-user can be added **without a full rewrite**:
- include conceptual tenant/user boundaries early,
- even if initial deployment uses only a single user.

---

## 5. Git, Commits, and Logs – Strict Requirements

You must treat **Git discipline and documentation as part of the product**.

### 5.1 Initial Setup (Non-Negotiable)

When starting in a **new directory** (assume this is the case):

1. **Initialize Git**
   - `git init`
2. **Create basic structure:**
   - `docs/`
   - `docs/commit-log.md`
   - `docs/change-log-detailed/`
   - `docs/coding-standards.md`
   - initial `README.md`
3. **Create first change log entry**:
   - CL-0001 in `docs/commit-log.md`
   - `docs/change-log-detailed/CL-0001.md` with:
     - summary,
     - rationale,
     - files created,
     - any decisions made.
4. **Create initial commit**:
   - message: `CL-0001: Initial project scaffolding`
   - Ensure `git status` is clean after commit.

If the environment does not allow running git, you must **still generate** the expected files and clearly describe the commands that should be run.

### 5.2 Ongoing Commits

For every logical change set:

- **Create a new CL-ID**:
  - Increment: CL-0002, CL-0003, etc.
- **Update `docs/commit-log.md`**:
  - Append one line per CL:
    - `CL-000X | short title | date | brief notes`
- **Create/Update `docs/change-log-detailed/CL-000X.md`**:
  - Detailed explanation:
    - what changed,
    - why,
    - any trade-offs,
    - tests added or updated.
- **Make a Git commit**:
  - Message must start with the CL ID:
    - `CL-000X: <short human-readable summary>`

Rules:

- Do **not** batch unrelated changes in a single commit.
- Do **not** forget to update the commit logs.
- After each commit, `git status` should be clean.

---

## 6. Engineering Standards (Language-Agnostic)

Because the tech stack is flexible, documentation standards must be **language-appropriate**, not Java-only.

### 6.1 Code Documentation

- Every **class/module/component/function** must have documentation comments:
  - In Java: Javadoc
  - In Python: docstrings
  - In TypeScript/JavaScript: JSDoc / TSDoc-style comments
  - In Go: GoDoc comments
- Each doc comment must include:
  - **Summary** – what this element does.
  - **Importance** – why this exists; what role it plays in the system.
  - **Alternatives** – a brief sentence about a reasonable alternative approach or where this element could be changed in future.

### 6.2 Static Analysis & Formatting

- Configure at least one static analysis / linting / style tool:
  - Example: Checkstyle, ESLint, Flake8, Pylint, go vet, etc.
- Enforce:
  - presence of documentation comments (where reasonable),
  - code style conventions,
  - basic safety checks.

### 6.3 Testing

- Use a standard testing framework appropriate to the language (e.g., JUnit, pytest, Jest, Go test).
- Tests must:
  - cover core logic (category system, classification, AI abstraction).
  - cover email/meeting integration logic as much as possible via mocks.
- Every significant feature or bugfix must have tests added or updated.

---

## 7. Process Rules (Mandatory)

- Generate artifacts **incrementally** but **cohesively**, ensuring the system feels real, complete, and credible.
- Prefer **minimal, justified changes**:
  - explain why each component or module exists,
  - avoid speculative abstraction until needed.
- Keep all examples runnable and consistent with configuration.
- Avoid destructive commands and never remove user work unless explicitly asked.
- Maintain ASCII text unless the file already uses Unicode.
- At each “milestone” step:
  - summarize what was done,
  - what remains,
  - what the next CL should be.

---

## 8. Delivery Format (What You Must Produce)

You must produce, at minimum:

1. **High-level system architecture document**
   - describe components, boundaries, and data flow between:
     - email integration,
     - calendar/meeting integration,
     - storage,
     - AI abstraction,
     - category system,
     - chat interface,
     - background workers (if any).

2. **Domain model description**
   - Users (current and future multi-user),
   - Accounts / connections (email, calendar),
   - Messages, Threads, Meetings,
   - Categories,
   - Notes, Tasks, Follow-ups,
   - AIRequests/AIResponses (for audit / traceability).

3. **Tech stack proposal**
   - with reasons for each choice,
   - pointing out any easy replacements if needed later.

4. **Migration strategy**
   - How to:
     - run locally,
     - run on a single Hetzner host,
     - extend to multiple hosts,
     - eventually lift to AWS/Azure/GCP.

5. **Initial implementation plan**
   - broken into steps / CL-IDs,
   - with dependencies.

6. **Agile/Scrum artifacts**
   - feature backlog,
   - prioritized,
   - milestones and sprints,
   - integration order:
     - which features first,
     - which integrations next,
     - when to introduce AI,
     - when to add multi-user support.

7. **Core implementation**
   - minimal but working:
     - connecting to at least one email provider in read-only mode,
     - ingesting email metadata,
     - creating categories and assigning emails,
     - basic chat interface calling AI abstraction,
     - drafting example replies (AI-assisted),
     - storing and retrieving notes.

8. **README**
   - how to set up and run locally,
   - how to connect an email account (mock or real),
   - how to use categories,
   - how to use the chat assistant.

9. **Git logs and detailed change logs**
   - as described in the Git section above.

10. **Future work section**
    - suggested enhancements beyond MVP,
    - including when to add:
      - advanced predictions (“who to email next”),
      - vertical templates (real estate, recruiting, etc.),
      - deeper automation,
      - more providers.

---

## 9. Non-Functional Requirements

- **Security**
  - least privilege,
  - never send emails without explicit user confirmation,
  - protect secrets (API keys, tokens) via environment variables or secret stores.
- **Reliability**
  - should degrade gracefully if AI or email APIs are temporarily unavailable.
- **Observability**
  - minimal logging:
    - errors,
    - key events (ingest, draft generation),
    - basic metrics for local debugging.
- **Scalability**
  - design data structures and abstractions that allow:
    - splitting work across workers or nodes later,
    - scaling reads and writes with minimal redesign.
- **Portability**
  - minimal vendor lock-in:
    - envelope the infra behind adapters where possible.

---

## 10. Definition of Done (for MVP)

The MVP is considered **done** when:

- A single user can:
  - connect an email provider in read-only mode,
  - ingest emails and basic metadata,
  - create and manage custom categories,
  - have emails suggested or assigned to categories,
  - ask a chat interface about their inbox or meetings,
  - get AI-generated reply drafts,
  - store notes and action items linked to emails or meetings.

- The project has:
  - working local setup instructions,
  - an initial path documented for Hetzner deployment,
  - a clear future path for multi-user support.

- Engineering standards are satisfied:
  - documentation comments present,
  - static analysis configured,
  - tests implemented for core logic.

- Git discipline is followed:
  - CL-IDs created and logged,
  - `docs/commit-log.md` and `docs/change-log-detailed/CL-XXXX.md` in sync with commits.

- A **short, human-readable paragraph** is provided explaining this project in a way that:
  - a recruiter,
  - a hiring manager,
  - or a staff-level engineer
  could quickly understand the value, scope, and technical maturity.

SUPER PROMPT END