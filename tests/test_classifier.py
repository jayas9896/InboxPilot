"""Summary: Tests for category classifier behavior.

Importance: Validates rule-based suggestions for category assignment.
Alternatives: Use only AI-driven classification without rules.
"""

from __future__ import annotations

from datetime import datetime

from inboxpilot.classifier import RuleBasedClassifier
from inboxpilot.models import Category, Message


def test_rule_based_classifier_suggests_category() -> None:
    """Summary: Suggest category when keyword appears.

    Importance: Confirms deterministic classification for basic workflows.
    Alternatives: Skip suggestions until AI integration is active.
    """

    classifier = RuleBasedClassifier()
    message = Message(
        provider_message_id="msg-3",
        subject="Interview schedule",
        sender="hr@example.com",
        recipients="you@example.com",
        timestamp=datetime.utcnow(),
        snippet="Interview schedule",
        body="We would like to schedule an interview.",
    )
    categories = [Category(name="Recruiting", description="Hiring interviews")]
    suggestions = classifier.suggest(message, categories)
    assert suggestions
    assert suggestions[0].name == "Recruiting"
