"""Summary: Category template packs.

Importance: Provides starter category sets for common workflows.
Alternatives: Require users to build all categories manually.
"""

from __future__ import annotations

from dataclasses import dataclass

from inboxpilot.models import Category
from inboxpilot.storage.sqlite_store import SqliteStore


@dataclass(frozen=True)
class CategoryTemplate:
    """Summary: Represents a named set of categories.

    Importance: Enables quick setup for common professional domains.
    Alternatives: Store templates in JSON files outside the codebase.
    """

    name: str
    categories: list[Category]


def list_templates() -> list[CategoryTemplate]:
    """Summary: Return available category templates.

    Importance: Powers CLI discovery of template packs.
    Alternatives: Use a plugin system to discover templates dynamically.
    """

    return [
        CategoryTemplate(
            name="real_estate",
            categories=[
                Category(name="Leads", description="Buyer and seller inquiries"),
                Category(name="Listings", description="Active listings and showings"),
                Category(name="Contracts", description="Offers and contract updates"),
                Category(name="Closings", description="Closing timelines and documents"),
            ],
        ),
        CategoryTemplate(
            name="recruiting",
            categories=[
                Category(name="Candidates", description="Applicant communications"),
                Category(name="Interviews", description="Scheduling and feedback"),
                Category(name="Offers", description="Offer logistics and negotiations"),
            ],
        ),
        CategoryTemplate(
            name="sales",
            categories=[
                Category(name="Prospects", description="Early-stage outreach"),
                Category(name="Pipeline", description="Active deals and follow-ups"),
                Category(name="Renewals", description="Existing customer renewals"),
                Category(name="Contracts", description="Pricing and legal review"),
            ],
        ),
        CategoryTemplate(
            name="freelancing",
            categories=[
                Category(name="Leads", description="Potential clients"),
                Category(name="Active Projects", description="Ongoing client work"),
                Category(name="Invoices", description="Billing and payments"),
            ],
        ),
        CategoryTemplate(
            name="personal_life",
            categories=[
                Category(name="Family", description="Family communications"),
                Category(name="Finance", description="Bills and banking"),
                Category(name="Health", description="Appointments and health topics"),
                Category(name="Travel", description="Trips and plans"),
            ],
        ),
    ]


def load_template(store: SqliteStore, template_name: str, user_id: int | None = None) -> int:
    """Summary: Load a template pack into storage.

    Importance: Accelerates onboarding with prebuilt category packs.
    Alternatives: Require manual category creation for each pack.
    """

    templates = {template.name: template for template in list_templates()}
    template = templates.get(template_name)
    if not template:
        raise ValueError(f"Unknown template: {template_name}")
    created = 0
    for category in template.categories:
        store.create_category(category, user_id=user_id)
        created += 1
    return created
