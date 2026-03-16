# app/models/config/model_types.py
# ─────────────────────────────────────────────────────
# Types that only app/models/ uses.
# Annotated types for Pydantic validation.
# ─────────────────────────────────────────────────────

from __future__ import annotations
from typing  import Annotated
from pydantic import Field
from enum    import Enum
from shared.types import Markdown


# ── ANNOTATED PYDANTIC TYPES ──────────────────────────
# Validation rules defined once — used in every model
# that needs the same validation without repeating Field()

ValidUrl = Annotated[
    str,
    Field(
        description="A valid public HTTP or HTTPS URL",
        examples=["https://competitor.com"],
        min_length=10,
        max_length=500,
    )
]

ValidJobId = Annotated[
    str,
    Field(
        description="A UUID job identifier",
        min_length=1,
        max_length=100,
    )
]

ValidMarkdown = Annotated[
    Markdown,
    Field(
        description="Non-empty markdown formatted report",
        min_length=1,
    )
]


# ── REPORT STRUCTURE ──────────────────────────────────

class ReportSection(str, Enum):
    """
    The 5 fixed sections every report must have.
    Used to validate Claude output has all sections.
    Only models and report_service care about this.
    """
    COMPANY_OVERVIEW          = "company_overview"
    PRODUCT_ANALYSIS          = "product_analysis"
    CUSTOMER_SENTIMENT        = "customer_sentiment"
    MARKETING_STRATEGY        = "marketing_strategy"
    STRATEGIC_RECOMMENDATIONS = "strategic_recommendations"