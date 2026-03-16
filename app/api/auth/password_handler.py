# app/api/auth/password_handler.py
# ─────────────────────────────────────────────────────
# Handles all password hashing and verification.
#
# Why bcrypt?
#   - Industry standard for password hashing
#   - Intentionally slow — prevents brute force attacks
#   - Each hash includes a random salt automatically
#     so same password → different hash every time
#   - Work factor (rounds) can be increased over time
#     as hardware gets faster
#
# Rules:
#   - NEVER store plain text passwords
#   - NEVER log passwords anywhere
#   - NEVER compare passwords with == 
#     always use verify_password()
# ─────────────────────────────────────────────────────

from __future__ import annotations
from passlib.context import CryptContext
from config.logging_config import get_logger

logger = get_logger(__name__)

# ── CONTEXT ───────────────────────────────────────────
# CryptContext manages hashing schemes.
# schemes=["bcrypt"] → use bcrypt algorithm
# deprecated="auto"  → automatically upgrade old hashes
#                       if we ever change the algorithm
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


# ── PUBLIC FUNCTIONS ──────────────────────────────────

def hash_password(plain_password: str) -> str:
    """
    Hashes a plain text password using bcrypt.

    Always call this before storing any password.
    The result is safe to store in the database.

    Example:
        hash_password("MyPassword123!")
        → "$2b$12$rAnDoMsAlTxxxxxxxxxhashedvalue"

    Args:
        plain_password: Raw password from user input

    Returns:
        Bcrypt hash string — safe to store in DB

    Raises:
        ValueError: If password is empty
    """
    if not plain_password or not plain_password.strip():
        raise ValueError("Password cannot be empty")

    if len(plain_password) < 8:
        raise ValueError(
            "Password must be at least 8 characters long"
        )

    if len(plain_password) > 128:
        # bcrypt silently truncates passwords over 72 bytes.
        # We reject passwords over 128 chars explicitly
        # so users are not surprised by truncation behavior.
        raise ValueError(
            "Password cannot exceed 128 characters"
        )

    return pwd_context.hash(plain_password)


def verify_password(
    plain_password:  str,
    hashed_password: str,
) -> bool:
    """
    Verifies a plain password against a stored bcrypt hash.

    bcrypt extracts the salt from the stored hash,
    re-hashes the plain password with the same salt,
    and compares the results in constant time.
    Constant time comparison prevents timing attacks.

    Args:
        plain_password:  Password from login request
        hashed_password: Hash retrieved from database

    Returns:
        True  → password matches
        False → password does not match

    Note:
        Never raises an exception on wrong password.
        Always returns False — never leaks error details.
    """
    if not plain_password or not hashed_password:
        return False

    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        # Log the error but never expose it to the caller.
        # Returning False is always safe — worst case is
        # a valid login attempt being rejected.
        logger.error(
            "Password verification error: %s", str(e)
        )
        return False


def is_password_strong(plain_password: str) -> tuple[bool, str]:
    """
    Validates password strength before hashing.
    Call this during registration to enforce strong passwords.

    Rules:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character

    Args:
        plain_password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
        is_valid=True  → password meets requirements
        is_valid=False → error_message explains why
    """
    if len(plain_password) < 8:
        return False, "Password must be at least 8 characters"

    if len(plain_password) > 128:
        return False, "Password cannot exceed 128 characters"

    if not any(c.isupper() for c in plain_password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in plain_password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in plain_password):
        return False, "Password must contain at least one number"

    special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
    if not any(c in special_chars for c in plain_password):
        return False, "Password must contain at least one special character"

    return True, ""