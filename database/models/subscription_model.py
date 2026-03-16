# database/models/subscription_model.py
# ─────────────────────────────────────────────────────
# Two tables:
#   1. SubscriptionPlan  → defines available plans
#   2. Subscription      → links a user to a plan
#
# Why two tables?
# Plans are created/managed by admin or manager.
# Subscriptions are assigned to users.
# Separating them means plan details can change
# without affecting existing user subscriptions.
#
# Plan management:
#   Admin   → create, update, deactivate plans
#   Manager → assign plans to users
#   User    → view their own subscription status
# ─────────────────────────────────────────────────────

from __future__ import annotations
import uuid
from datetime import datetime

from sqlalchemy                     import (
    Column, String, DateTime,
    ForeignKey, Integer, Numeric,
    Boolean, Text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm                 import relationship

from database.connection import Base


# Valid plan names — enforced at service layer
VALID_PLANS = {"free", "pro", "enterprise"}

# Valid subscription statuses
VALID_STATUSES = {"active", "cancelled", "expired", "suspended"}


class SubscriptionPlan(Base):
    """
    Defines an available subscription plan.
    Created and managed by admin or manager via API.
    Never seeded — always created through proper endpoints.

    Fields:
        name            → unique plan identifier (free/pro/enterprise)
        display_name    → human readable name shown to users
        analyses_limit  → max analyses per month (-1 = unlimited)
        price_monthly   → monthly price in USD
        is_active       → inactive plans cannot be assigned
        features        → JSON object of feature flags
        description     → plan description shown to users
    """
    __tablename__ = "subscription_plans"

    id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )
    name = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        # index=True → plans are frequently looked up by name
    )
    display_name = Column(
        String(100),
        nullable=False,
        # Example: "Pro Plan", "Enterprise Plan"
    )
    analyses_limit = Column(
        Integer,
        nullable=False,
        # -1 = unlimited
        # 0  = plan disabled
        # >0 = exact monthly limit
    )
    price_monthly = Column(
        Numeric(10, 2),
        nullable=False,
        default=0.00,
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        # Inactive plans cannot be assigned to new users
        # Existing users on inactive plan are not affected
    )
    description = Column(
        Text,
        nullable=True,
    )
    features = Column(
        JSONB,
        nullable=True,
        # Flexible feature flags — no schema migration needed
        # when adding new features
        # Example:
        # {
        #   "pdf_export": true,
        #   "api_access": true,
        #   "priority_queue": false,
        #   "max_report_length": 10000
        # }
    )
    created_by = Column(
        UUID(as_uuid=False),
        nullable=True,
        # UUID of admin/manager who created this plan
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # ── RELATIONSHIP ───────────────────────────────────
    subscriptions = relationship(
        "Subscription",
        back_populates="plan",
        uselist=True,
    )

    def __repr__(self) -> str:
        return (
            f"<SubscriptionPlan "
            f"name={self.name} "
            f"limit={self.analyses_limit} "
            f"price={self.price_monthly}>"
        )


class Subscription(Base):
    """
    Links one user to one subscription plan.
    Tracks status, start date, and expiry.

    Rules:
        - One active subscription per user at a time
        - Only admin or manager can create/modify subscriptions
        - User can view their own subscription status
        - Expired subscriptions are kept for audit history
        - When plan changes → old subscription cancelled,
          new subscription created
    """
    __tablename__ = "subscriptions"

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
        # Not unique — user can have history of subscriptions
        # Active subscription determined by status field
    )
    plan_id = Column(
        UUID(as_uuid=False),
        ForeignKey("subscription_plans.id"),
        nullable=False,
    )
    status = Column(
        String(50),
        nullable=False,
        default="active",
        index=True,
        # active    → currently valid
        # cancelled → cancelled by user or admin
        # expired   → past expiry date
        # suspended → suspended by admin (non-payment etc)
    )
    starts_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    expires_at = Column(
        DateTime,
        nullable=True,
        # None = no expiry (lifetime or manual management)
    )
    cancelled_at = Column(
        DateTime,
        nullable=True,
    )
    cancelled_by = Column(
        UUID(as_uuid=False),
        nullable=True,
        # UUID of admin/manager who cancelled
        # None = self-cancelled
    )
    assigned_by = Column(
        UUID(as_uuid=False),
        nullable=True,
        # UUID of admin/manager who assigned this plan
    )
    notes = Column(
        Text,
        nullable=True,
        # Internal notes from admin/manager
        # Example: "Upgraded after sales call on 2026-03-16"
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # ── RELATIONSHIPS ──────────────────────────────────
    user = relationship(
        "User",
        back_populates="subscription",
    )
    plan = relationship(
        "SubscriptionPlan",
        back_populates="subscriptions",
    )

    def __repr__(self) -> str:
        return (
            f"<Subscription "
            f"user={self.user_id} "
            f"plan={self.plan_id} "
            f"status={self.status}>"
        )