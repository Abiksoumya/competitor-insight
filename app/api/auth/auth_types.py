# app/api/auth/config/auth_types.py
# ─────────────────────────────────────────────────────
# Types used only inside the auth layer.
# Defines roles, plans, and token data structures.
# ─────────────────────────────────────────────────────

from __future__ import annotations
from dataclasses import dataclass
from enum        import Enum


# ── ROLE ENUM ─────────────────────────────────────────
class RoleEnum(str, Enum):
    """
    Valid user roles.
    Inherits str so values serialize to JSON automatically.

    Hierarchy (lowest to highest):
        guest → user → manager → admin
    """
    ADMIN   = "admin"
    MANAGER = "manager"
    USER    = "user"
    GUEST   = "guest"


# ── PLAN ENUM ─────────────────────────────────────────
class PlanEnum(str, Enum):
    """
    Valid subscription plan names.
    Must match name column in subscription_plans table.

    Hierarchy (lowest to highest):
        free → pro → enterprise
    """
    FREE       = "free"
    PRO        = "pro"
    ENTERPRISE = "enterprise"


# ── ROLE HIERARCHY ────────────────────────────────────
# Used by access_control.py to compare role levels.
# Higher number = more permissions.
ROLE_HIERARCHY: dict[str, int] = {
    RoleEnum.GUEST:   0,
    RoleEnum.USER:    1,
    RoleEnum.MANAGER: 2,
    RoleEnum.ADMIN:   3,
}

# ── PLAN HIERARCHY ────────────────────────────────────
# Used by access_control.py to compare plan levels.
PLAN_HIERARCHY: dict[str, int] = {
    PlanEnum.FREE:       0,
    PlanEnum.PRO:        1,
    PlanEnum.ENTERPRISE: 2,
}


# ── TOKEN DATA ────────────────────────────────────────
@dataclass
class TokenData:
    """
    Decoded data extracted from a verified JWT token.
    Created by jwt_handler.verify_access_token().
    Passed to route handlers via access_control.py.

    This is what every protected route knows about
    the current user without hitting the database.
    """
    user_id: str
    email:   str
    role:    str
    plan:    str


@dataclass
class TokenPair:
    """
    Access + refresh token pair.
    Returned after successful login or registration.

    access_token  → short lived (30 min)
                    sent with every API request
    refresh_token → long lived (7 days)
                    used only to get new access token
    """
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"