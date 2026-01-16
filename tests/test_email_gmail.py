"""Summary: Tests for Gmail email parsing helpers.

Importance: Ensures Gmail payloads are normalized into readable text.
Alternatives: Use integration tests with the live Gmail API.
"""

from __future__ import annotations

import base64

from inboxpilot.email import _extract_gmail_body, _parse_gmail_headers


def _encode(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8").rstrip("=")


def test_parse_gmail_headers() -> None:
    """Summary: Verify header parsing returns expected values.

    Importance: Confirms Gmail headers are mapped correctly for ingestion.
    Alternatives: Access header list directly in parsing logic.
    """

    headers = [
        {"name": "Subject", "value": "Hello"},
        {"name": "From", "value": "sender@example.com"},
    ]
    parsed = _parse_gmail_headers(headers)
    assert parsed["Subject"] == "Hello"
    assert parsed["From"] == "sender@example.com"


def test_extract_gmail_body_prefers_plain_text() -> None:
    """Summary: Extract plain text bodies from Gmail payloads.

    Importance: Ensures readable text is stored for AI workflows.
    Alternatives: Fall back to Gmail snippets only.
    """

    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/plain", "body": {"data": _encode("Hello")}},
            {"mimeType": "text/html", "body": {"data": _encode("<p>Hello</p>")}},
        ],
    }
    body = _extract_gmail_body(payload)
    assert body == "Hello"
