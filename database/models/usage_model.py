# database/models/usage_model.py
# ─────────────────────────────────────────────────────
# UsageTracking table definition.
# Records every analysis run per user.
#
# Purpose:
#   - Enforce monthly quota per subscription plan
#   - Provide usage history to users
#   - Provide usage analytics to admin/manager
#
# Query pattern:
#   SELECT COUNT(*) FROM usage_tracking
#   WHERE user_id = ? AND month_year = '2026-03'
#   → gives current month usage for quota check
# ─────────────────────────────────────────────────────

from __future__ import annotations
import uuid
from datetime import datetime

from sqlalchemy                     import (
    Column, String, DateTime,
    ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm                 import relationship

from database.connection import Base


class UsageTracking(Base):
    """
    Records one analysis run for one user.
    One row inserted every time a user runs an analysis.

    Rules:
        - Inserted when pipeline starts — not when it finishes
        - Never updated or deleted — immutable audit record
        - month_year is always current month at insertion time
        - Quota check counts rows for user + current month

    Quota check example:
        User on PRO plan (limit=50)
        COUNT rows WHERE user_id=X AND month_year='2026-03'
        If count >= 50 → reject with 429
        If count < 50  → allow and insert new row
    """
    __tablename__ = "usage_tracking"

    id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id = Column(
        String(255),
        nullable=False,
        # The pipeline job UUID this usage record belongs to
        # Used to link usage record back to the actual job
    )
    competitor_url = Column(
        String(500),
        nullable=False,
        # The URL that was analyzed
        # Useful for usage history shown to user
    )
    month_year = Column(
        String(7),
        nullable=False,
        index=True,
        # Format: "YYYY-MM" e.g. "2026-03"
        # Indexed — quota check filters by this column heavily
        # String instead of Date — simpler month comparison
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # ── COMPOSITE INDEX ────────────────────────────────
    # Quota check always queries by user_id + month_year together
    # Composite index makes this query fast even with millions of rows
    __table_args__ = (
        Index(
            "ix_usage_user_month",
            "user_id",
            "month_year",
            # This index covers the exact query pattern:
            # WHERE user_id = ? AND month_year = ?
        ),
    )

    # ── RELATIONSHIP ───────────────────────────────────
    user = relationship(
        "User",
        back_populates="usage_records",
    )

    def __repr__(self) -> str:
        return (
            f"<UsageTracking "
            f"user={self.user_id} "
            f"job={self.job_id} "
            f"month={self.month_year}>"
        )