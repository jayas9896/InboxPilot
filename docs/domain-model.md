# Domain Model

## User
- id, display_name, email
- future: tenant_id, role, preferences

## Account / Connection
- id, user_id, provider_type (email/calendar), provider_name, status, created_at, details
- auth_type, read_only, status

## Message
- id, user_id, provider_message_id, thread_id, subject
- sender, recipients, timestamp, snippet, body
- assigned_category_ids

## Thread
- id, user_id, provider_thread_id, message_ids

## Meeting
- id, user_id, provider_event_id, title, participants, start_time, end_time
- transcript_ref (optional)

## MeetingTranscript
- meeting_id, content

## Category
- id, user_id, name, description (optional), template_tag (optional)
- user_id or tenant_id for future multi-user

## Note
- id, user_id, parent_type (message/meeting), parent_id, content

## Task / Follow-up
- id, user_id, parent_type, parent_id, description, status, due_date

## AIRequest
- id, user_id, provider, model, prompt, timestamp

## AIResponse
- id, ai_request_id, response_text, latency_ms, token_estimate

## Tenancy Boundaries
- All primary entities include user_id in the schema design, even if the initial MVP is single-user.
- This allows future multi-user support without a schema rewrite.
