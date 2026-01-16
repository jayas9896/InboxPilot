"""Summary: Tests for Outlook email parsing helpers.

Importance: Ensures Graph payloads normalize into readable text.
Alternatives: Use integration tests with the live Graph API.
"""

from __future__ import annotations

from inboxpilot.email import _parse_outlook_message


def test_parse_outlook_message_basic_fields() -> None:
    """Summary: Verify Outlook payload parsing returns expected values.

    Importance: Confirms Graph fields map to the core message model.
    Alternatives: Parse fields inline in the provider.
    """

    payload = {
        "id": "msg-1",
        "subject": "Hello",
        "from": {"emailAddress": {"address": "sender@example.com"}},
        "toRecipients": [
            {"emailAddress": {"address": "to@example.com"}},
            {"emailAddress": {"address": "cc@example.com"}},
        ],
        "receivedDateTime": "2026-01-15T10:00:00Z",
        "bodyPreview": "Preview",
        "body": {"contentType": "text", "content": "Body"},
    }
    message = _parse_outlook_message(payload)
    assert message is not None
    assert message.subject == "Hello"
    assert message.sender == "sender@example.com"
    assert "to@example.com" in message.recipients
    assert message.body == "Body"
