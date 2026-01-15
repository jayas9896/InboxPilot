"""Summary: Category classification helpers.

Importance: Provides lightweight suggestions for message categorization.
Alternatives: Use an LLM-based classifier for higher accuracy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from inboxpilot.models import Category, Message


@dataclass(frozen=True)
class RuleBasedClassifier:
    """Summary: Simple keyword-based category classifier.

    Importance: Offers deterministic, fast categorization without AI.
    Alternatives: Use a supervised ML classifier or LLM-based categorizer.
    """

    def suggest(self, message: Message, categories: list[Category]) -> list[Category]:
        """Summary: Suggest categories based on keyword matches.

        Importance: Supports automatic triage when AI is unavailable.
        Alternatives: Require manual category assignment.
        """

        text = f"{message.subject} {message.body}".lower()
        suggestions: list[Category] = []
        for category in categories:
            keywords = _extract_keywords(category)
            if any(keyword in text for keyword in keywords):
                suggestions.append(category)
        return suggestions


def _extract_keywords(category: Category) -> list[str]:
    """Summary: Extract keywords from a category name and description.

    Importance: Drives rule-based matching with minimal configuration.
    Alternatives: Store explicit keyword lists on categories.
    """

    text = f"{category.name} {category.description or ''}".lower()
    tokens = re.split(r"\W+", text)
    return [token for token in tokens if token]
