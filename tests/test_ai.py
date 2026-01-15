"""Summary: Tests for AI abstraction layer.

Importance: Ensures AI providers return expected outputs in the MVP.
Alternatives: Skip AI testing and rely on manual verification.
"""

from __future__ import annotations

from inboxpilot.ai import MockAiProvider


def test_mock_ai_provider_returns_response() -> None:
    """Summary: Verify mock AI provider returns deterministic text.

    Importance: Confirms basic AI abstraction behavior for tests.
    Alternatives: Use live providers in integration tests only.
    """

    provider = MockAiProvider()
    response, latency = provider.generate_text("Hello", "test")
    assert "[mock:test]" in response
    assert latency >= 0
