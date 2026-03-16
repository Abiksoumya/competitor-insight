# app/api/auth/jwt_handler.py
# ─────────────────────────────────────────────────────
# Handles JWT token creation and verification.
#
# Two token types:
#   Access Token  → short lived (30 min)
#                   contains user_id, email, role, plan
#                   sent with every API request
#
#   Refresh Token → long lived (7 days)
#                   contains only user_id
#                   used only to get new access token
#                   when access token expires
#
# Why two tokens?
#   Access token expires quickly — limits damage if stolen.
#   Refresh token lets user stay logged in without
#   re-entering password every 30 minutes.
#   If refresh token is stolen → user logs out,
#   invalidating the refresh token.
# ─────────────────────────────────────────────────────

from __future__ import annotations
from datetime  import datetime, timedelta, timezone
from typing    import Optional

from jose      import jwt, JWTError

from config.settings            import settings
from config.logging_config      import get_logger
from app.api.auth.auth_types    import TokenData, TokenPair

logger = get_logger(__name__)


# ── TOKEN TYPE CONSTANTS ──────────────────────────────
_ACCESS_TYPE  = "access"
_REFRESH_TYPE = "refresh"


# ── TOKEN CREATION ────────────────────────────────────

def create_access_token(
    user_id: str,
    email:   str,
    role:    str,
    plan:    str,
) -> str:
    """
    Creates a signed JWT access token.

    Payload contains:
        sub   → user_id (standard JWT subject claim)
        email → user email
        role  → user role (admin/manager/user/guest)
        plan  → subscription plan (free/pro/enterprise)
        type  → "access" (distinguishes from refresh token)
        iat   → issued at timestamp
        exp   → expiry timestamp

    Args:
        user_id: UUID of the authenticated user
        email:   User email address
        role:    User role string
        plan:    Subscription plan name

    Returns:
        Signed JWT string

    Raises:
        RuntimeError: If token creation fails
    """
    if not all([user_id, email, role, plan]):
        raise ValueError(
            "All token claims are required — "
            "user_id, email, role and plan cannot be empty"
        )

    now    = datetime.now(timezone.utc)
    expire = now + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub":   user_id,
        "email": email,
        "role":  role,
        "plan":  plan,
        "type":  _ACCESS_TYPE,
        "iat":   now,
        "exp":   expire,
    }

    try:
        token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        logger.debug(
            "Access token created — user: %s role: %s plan: %s",
            user_id, role, plan
        )
        return token

    except Exception as e:
        logger.error("Failed to create access token: %s", str(e))
        raise RuntimeError(
            f"Token creation failed: {str(e)}"
        ) from e


def create_refresh_token(user_id: str) -> str:
    """
    Creates a signed JWT refresh token.
    Contains only user_id — minimal claims for security.
    If stolen, attacker cannot learn role or plan.

    Args:
        user_id: UUID of the authenticated user

    Returns:
        Signed JWT refresh token string

    Raises:
        RuntimeError: If token creation fails
    """
    if not user_id:
        raise ValueError("user_id cannot be empty")

    now    = datetime.now(timezone.utc)
    expire = now + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    payload = {
        "sub":  user_id,
        "type": _REFRESH_TYPE,
        "iat":  now,
        "exp":  expire,
    }

    try:
        token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        logger.debug(
            "Refresh token created — user: %s", user_id
        )
        return token

    except Exception as e:
        logger.error("Failed to create refresh token: %s", str(e))
        raise RuntimeError(
            f"Refresh token creation failed: {str(e)}"
        ) from e


def create_token_pair(
    user_id: str,
    email:   str,
    role:    str,
    plan:    str,
) -> TokenPair:
    """
    Creates both access and refresh tokens together.
    Called after successful login or registration.

    Args:
        user_id: UUID of the authenticated user
        email:   User email address
        role:    User role string
        plan:    Subscription plan name

    Returns:
        TokenPair containing both tokens
    """
    return TokenPair(
        access_token=create_access_token(
            user_id=user_id,
            email=email,
            role=role,
            plan=plan,
        ),
        refresh_token=create_refresh_token(user_id),
    )


# ── TOKEN VERIFICATION ────────────────────────────────

def verify_access_token(token: str) -> Optional[TokenData]:
    """
    Verifies and decodes a JWT access token.

    Checks performed:
        1. Signature is valid — not tampered with
        2. Token has not expired
        3. Token type is "access" not "refresh"
        4. Required claims are present

    Args:
        token: Raw JWT string from Authorization header

    Returns:
        TokenData if all checks pass
        None     if any check fails — never raises exception
                 so route handlers always get a clean result
    """
    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        # Verify token type
        if payload.get("type") != _ACCESS_TYPE:
            logger.warning(
                "Non-access token used as access token — "
                "type: %s", payload.get("type")
            )
            return None

        # Extract and validate required claims
        user_id = payload.get("sub")
        email   = payload.get("email")
        role    = payload.get("role")
        plan    = payload.get("plan")

        if not all([user_id, email, role, plan]):
            logger.warning(
                "Access token missing required claims"
            )
            return None

        return TokenData(
            user_id=str(user_id),
            email=str(email),
            role=str(role),
            plan=str(plan),
        )

    except JWTError as e:
        logger.warning(
            "JWT verification failed: %s", str(e)
        )
        return None

    except Exception as e:
        logger.error(
            "Unexpected error during token verification: %s",
            str(e)
        )
        return None


def verify_refresh_token(token: str) -> Optional[str]:
    """
    Verifies a refresh token and extracts user_id.
    Called by the token refresh endpoint.

    Args:
        token: Raw JWT refresh token string

    Returns:
        user_id string if valid
        None           if invalid or expired
    """
    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        if payload.get("type") != _REFRESH_TYPE:
            logger.warning(
                "Non-refresh token used as refresh token"
            )
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        return str(user_id)

    except JWTError as e:
        logger.warning(
            "Refresh token verification failed: %s", str(e)
        )
        return None

    except Exception as e:
        logger.error(
            "Unexpected error during refresh token verification: %s",
            str(e)
        )
        return None