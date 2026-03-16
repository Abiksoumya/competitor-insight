# database/models/role_model.py
# ─────────────────────────────────────────────────────
# UserRole table definition.
# Stores the role assigned to each user.
#
# Why a separate table instead of a column on users?
# 1. Role changes don't touch the users table
# 2. Audit trail — we can track when role changed
# 3. Future-proof — easy to add multi-role support
#
# Valid roles:
#   admin   → full system access
#   manager → manage team, create subscriptions
#   user    → run analyses, view own reports
#   guest   → read-only demo access
# ─────────────────────────────────────────────────────

from __future__ import annotations
import uuid
from datetime import datetime

from sqlalchemy             import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm         import relationship

from database.connection import Base


# Valid role values — enforced at service layer
VALID_ROLES = {"admin", "manager", "user", "guest"}


class UserRole(Base):
    """
    Stores the role for one user.
    One user → one role at any time.

    Rules:
        - role must be one of VALID_ROLES
        - Every user must have a role record
        - Role is assigned at registration (default: user)
        - Only admin can change roles
    """
    __tablename__ = "user_roles"

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
        unique=True,
        # unique=True → one role record per user
        # ondelete CASCADE → deleting user deletes role
    )
    role = Column(
        String(50),
        nullable=False,
        default="user",
        # Default role for all new registrations
    )
    assigned_by = Column(
        UUID(as_uuid=False),
        nullable=True,
        # UUID of admin who assigned this role
        # None = self-assigned at registration
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
    user = relationship(
        "User",
        back_populates="role",
    )

    def __repr__(self) -> str:
        return f"<UserRole user={self.user_id} role={self.role}>"