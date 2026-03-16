# database/models/user_model.py
# ─────────────────────────────────────────────────────
# User table definition.
# Stores registered users of the application.
#
# One user has:
#   - One role         (UserRole table)
#   - One subscription (Subscription table)
#   - Many usage records (UsageTracking table)
# ─────────────────────────────────────────────────────

from __future__ import annotations
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database.connection import Base


class User(Base):
    """
    Represents a registered user.

    Rules:
        - Email must be unique across all users
        - Password is always stored as bcrypt hash
        - is_active=False means soft deleted — never hard delete
        - created_at and updated_at are set automatically
    """
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        # index=True — speeds up login queries
        # Login always queries by email — needs index
    )
    password_hash = Column(
        String(255),
        nullable=False,
        # Never store plain text password
        # Always bcrypt hashed before storing
    )
    full_name = Column(
        String(255),
        nullable=True,
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        # False = account deactivated
        # Deactivated users cannot login
        # We never hard delete users — audit trail
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
    # SQLAlchemy loads related records automatically
    # uselist=False → one-to-one relationship
    # uselist=True  → one-to-many relationship

    role = relationship(
        "UserRole",
        back_populates="user",
        uselist=False,
        # uselist=False → one user has one role
        cascade="all, delete-orphan",
        # delete-orphan → deleting user deletes their role too
    )

    subscription = relationship(
        "Subscription",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    usage_records = relationship(
        "UsageTracking",
        back_populates="user",
        uselist=True,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} active={self.is_active}>"