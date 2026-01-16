"""Summary: Tests for .eml email ingestion.

Importance: Ensures .eml parsing works for local email imports.
Alternatives: Use only mock email data for tests.
"""

from __future__ import annotations

from pathlib import Path

from inboxpilot.email import EmlEmailProvider


def test_eml_provider_parses_message(tmp_path: Path) -> None:
    """Summary: Parse a .eml file into a Message.

    Importance: Validates local email ingestion.
    Alternatives: Skip .eml support tests.
    """

    eml = tmp_path / "sample.eml"
    eml.write_text(
        """
        From: sender@example.com
        To: receiver@example.com
        Subject: Hello
        Date: Mon, 15 Jan 2026 10:00:00 +0000
        Message-Id: <test-1@example.com>

        Hello there.
        """.strip(),
        encoding="utf-8",
    )
    provider = EmlEmailProvider([eml])
    messages = provider.fetch_recent(5)
    assert messages[0].subject == "Hello"
    assert "sender@example.com" in messages[0].sender
