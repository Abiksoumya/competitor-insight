# database/models/__init__.py
# ─────────────────────────────────────────────────────
# Exports all models from a single import point.
#
# Why this file?
# Instead of importing from individual model files:
#   from database.models.user_model import User
#   from database.models.role_model import UserRole
#   ...
#
# You can import from one place:
#   from database.models import User, UserRole, SubscriptionPlan
#
# Also ensures all models are registered with Base.metadata
# when database.models is imported — required for
# Base.metadata.create_all() to find all tables.
# ─────────────────────────────────────────────────────

from database.models.user_model         import User
from database.models.role_model         import UserRole
from database.models.subscription_model import SubscriptionPlan, Subscription
from database.models.usage_model        import UsageTracking

__all__ = [
    "User",
    "UserRole",
    "SubscriptionPlan",
    "Subscription",
    "UsageTracking",
]