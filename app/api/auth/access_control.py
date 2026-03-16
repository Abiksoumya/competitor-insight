# app/api/auth/access_control.py
# ─────────────────────────────────────────────────────
# FastAPI route guards — control who can access what.
#
# Three levels of protection:
#   1. require_auth()           → must be logged in
#   2. require_role(role)       → must have minimum role
#   3. require_plan(plan)       → must have minimum plan
#
# Usage in routes:
#   from app.api.auth.access_control import (
#       require_auth,
#       require_role,
#       require_plan,
#   )
#
#   @router.post("/analyze")
#   def analyze(
#       current_user: TokenData = Depends(require_auth),
#   ):
#
#   @router.get("/admin/users")
#   def get_users(
#       current_user: TokenData = Depends(require_role("admin")),
#   ):
#
#   @router.post("/export/pdf")
#   def export_pdf(
#       current_user: TokenData = Depends(require_plan("pro")),
#   ):
# ─────────────────────────────────────────────────────

from __future__ import annotations

from fastapi          import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config.logging_config          import get_logger
from app.api.auth.jwt_handler       import verify_access_token
from app.api.auth.auth_types        import (
    TokenData,
    ROLE_HIERARCHY,
    PLAN_HIERARCHY,
)

logger = get_logger(__name__)

# ── BEARER SCHEME ─────────────────────────────────────
# Extracts token from "Authorization: Bearer <token>" header
# auto_error=False → we handle missing token ourselves
#                    with a clear error message
bearer_scheme = HTTPBearer(auto_error=False)


# ── GUARD 1 — AUTHENTICATION ──────────────────────────

def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> TokenData:
    """
    Route guard — verifies user is authenticated.
    Extracts and validates JWT from Authorization header.

    Use on any endpoint that requires a logged-in user.

    Raises:
        401 — Authorization header missing
        401 — Token is invalid or expired
        401 — Token is malformed

    Returns:
        TokenData with user_id, email, role, plan
    """
    # Check Authorization header exists
    if not credentials:
        logger.warning(
            "Request rejected — missing Authorization header"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Authorization header missing. "
                "Include 'Authorization: Bearer <token>' "
                "in your request headers."
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify the token
    token_data = verify_access_token(credentials.credentials)

    if not token_data:
        logger.warning(
            "Request rejected — invalid or expired token"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Token is invalid or has expired. "
                "Please login again to get a new token."
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug(
        "Authenticated — user: %s role: %s plan: %s",
        token_data.user_id,
        token_data.role,
        token_data.plan,
    )

    return token_data


# ── GUARD 2 — ROLE CHECK ──────────────────────────────

def require_role(minimum_role: str):
    """
    Route guard factory — enforces minimum role requirement.
    Builds on require_auth — user must be authenticated first.

    Role hierarchy (lowest to highest):
        guest(0) → user(1) → manager(2) → admin(3)

    Args:
        minimum_role: Minimum role needed to access the route
                      One of: "guest", "user", "manager", "admin"

    Usage:
        Depends(require_role("manager"))  ← manager or admin only
        Depends(require_role("admin"))    ← admin only

    Raises:
        401 — Not authenticated
        403 — Authenticated but insufficient role

    Returns:
        TokenData if role check passes
    """
    def _guard(
        current_user: TokenData = Depends(require_auth),
    ) -> TokenData:

        user_level     = ROLE_HIERARCHY.get(current_user.role, 0)
        required_level = ROLE_HIERARCHY.get(minimum_role, 0)

        if user_level < required_level:
            logger.warning(
                "Access denied — user: %s role: %s "
                "required: %s",
                current_user.user_id,
                current_user.role,
                minimum_role,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. "
                    f"This endpoint requires '{minimum_role}' role. "
                    f"Your current role is '{current_user.role}'."
                ),
            )

        return current_user

    return _guard


# ── GUARD 3 — PLAN CHECK ──────────────────────────────

def require_plan(minimum_plan: str):
    """
    Route guard factory — enforces minimum subscription plan.
    Builds on require_auth — user must be authenticated first.

    Plan hierarchy (lowest to highest):
        free(0) → pro(1) → enterprise(2)

    Args:
        minimum_plan: Minimum plan needed to access the route
                      One of: "free", "pro", "enterprise"

    Usage:
        Depends(require_plan("pro"))        ← pro or enterprise only
        Depends(require_plan("enterprise")) ← enterprise only

    Raises:
        401 — Not authenticated
        403 — Authenticated but insufficient plan

    Returns:
        TokenData if plan check passes
    """
    def _guard(
        current_user: TokenData = Depends(require_auth),
    ) -> TokenData:

        user_plan_level     = PLAN_HIERARCHY.get(current_user.plan, 0)
        required_plan_level = PLAN_HIERARCHY.get(minimum_plan, 0)

        if user_plan_level < required_plan_level:
            logger.warning(
                "Plan upgrade required — user: %s plan: %s "
                "required: %s",
                current_user.user_id,
                current_user.plan,
                minimum_plan,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"This feature requires '{minimum_plan}' plan. "
                    f"Your current plan is '{current_user.plan}'. "
                    f"Please upgrade your subscription."
                ),
            )

        return current_user

    return _guard


# ── OPTIONAL AUTH ─────────────────────────────────────

def optional_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> TokenData | None:
    """
    Optional authentication — does not raise if no token.
    Returns TokenData if valid token provided, None otherwise.

    Use on endpoints that behave differently for
    authenticated vs anonymous users.

    Example:
        GET /reports/demo → guests see demo report
        GET /reports/demo → authenticated users see full report

    Returns:
        TokenData if valid token present
        None      if no token or invalid token
    """
    if not credentials:
        return None

    return verify_access_token(credentials.credentials)