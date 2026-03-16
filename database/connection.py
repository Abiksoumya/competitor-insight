# database/connection.py
# ─────────────────────────────────────────────────────
# Central database connectivity module.
# Shared across FastAPI, pipeline, and CLI layers.
#
# Responsibilities:
#   - Create SQLAlchemy engine (one per application)
#   - Provide session factory for all DB operations
#   - Provide Base class for all table models
#   - Provide get_db() dependency for FastAPI routes
#   - Provide health check for startup verification
# ─────────────────────────────────────────────────────

from __future__ import annotations

from sqlalchemy             import create_engine, text
from sqlalchemy.orm         import sessionmaker, DeclarativeBase, Session
from sqlalchemy.pool        import NullPool
from sqlalchemy.exc         import OperationalError, DatabaseError

from config.settings        import settings
from config.logging_config  import get_logger

logger = get_logger(__name__)


# ── ENGINE ────────────────────────────────────────────
# Created once at module import time.
# Shared across the entire application.
#
# NullPool — do not maintain idle connections.
# Required for Supabase free tier which has a
# strict limit on simultaneous open connections.
# Without NullPool, connections stay open even when
# idle and exhaust the Supabase connection limit.
try:
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        echo=False,
        # Never set echo=True in production.
        # It logs every SQL query including values —
        # exposes passwords, tokens, and PII in logs.
    )
    logger.info("Database engine created successfully")

except Exception as e:
    logger.critical(
        "Failed to create database engine: %s", str(e)
    )
    raise


# ── SESSION FACTORY ───────────────────────────────────
# Call SessionLocal() to get a new Session instance.
# Never share Session instances across requests or threads.
#
# autocommit=False  → we explicitly call db.commit()
# autoflush=False   → we control when changes are sent to DB
# expire_on_commit=False → objects remain usable after commit
#                          without triggering extra DB queries
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ── BASE CLASS ────────────────────────────────────────
# Every table model inherits from Base.
# Base.metadata tracks all table definitions.
# Base.metadata.create_all(engine) creates all tables.
class Base(DeclarativeBase):
    pass


# ── FASTAPI SESSION DEPENDENCY ────────────────────────
def get_db():
    """
    FastAPI dependency — yields a database session.

    Guarantees:
        Session is always closed after request ends
        Rolls back automatically on unhandled exception
        Never leaks open connections to Supabase

    Usage in routes:
        from sqlalchemy.orm import Session
        from fastapi import Depends
        from database.connection import get_db

        @router.post("/example")
        def example(db: Session = Depends(get_db)):
            result = db.query(SomeModel).all()
            return result
    """
    db: Session = SessionLocal()
    try:
        yield db
    except DatabaseError as e:
        db.rollback()
        logger.error("Database error during request: %s", str(e))
        raise
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error during request: %s", str(e))
        raise
    finally:
        db.close()


# ── DATABASE HEALTH CHECK ─────────────────────────────
def check_db_connection() -> bool:
    """
    Verifies database is reachable and responsive.
    Called during application startup in main.py.
    Fails fast if database is unavailable —
    better to crash on startup than fail silently later.

    Returns:
        True  — connection successful
        False — connection failed
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database health check passed")
        return True

    except OperationalError as e:
        logger.critical(
            "Database unreachable — check DATABASE_URL and "
            "Supabase connection settings: %s", str(e)
        )
        return False

    except Exception as e:
        logger.critical(
            "Unexpected error during database health check: %s",
            str(e)
        )
        return False


# ── TABLE INITIALIZER ─────────────────────────────────
def init_db() -> None:
    """
    Creates all tables that don't already exist.
    Called once during application startup.
    Safe to call multiple times — skips existing tables.

    All models must be imported before calling this
    so Base.metadata knows about them.
    This is handled by importing database.models
    before calling init_db().
    """
    try:
        import database.models  # noqa: F401
        # noqa: F401 — suppresses "imported but unused" warning.
        # Import is intentional — registers models with Base.

        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")

    except Exception as e:
        logger.critical(
            "Failed to initialize database tables: %s", str(e)
        )
        raise