"""Database session management and lightweight migrations."""

from pathlib import Path

import secrets

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from app.config import DOCUMENTS_DIR, settings
from app.models import DiscoverySession

Path(settings.database_url.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)

MIGRATION_COLUMNS = {
    "products": "TEXT DEFAULT ''",
    "access_key": "TEXT DEFAULT ''",
    "pdf_path": "TEXT",
    "excel_path": "TEXT",
    "json_path": "TEXT",
    "documents_generated_at": "TEXT",
    "approved_at": "TEXT",
}


def run_migrations(engine=None) -> None:
    target = engine or globals()["engine"]
    SQLModel.metadata.create_all(target)
    inspector = inspect(target)
    if "discovery_sessions" not in inspector.get_table_names():
        return

    existing = {c["name"] for c in inspector.get_columns("discovery_sessions")}
    with target.connect() as conn:
        for column, col_type in MIGRATION_COLUMNS.items():
            if column not in existing:
                conn.execute(
                    text(f"ALTER TABLE discovery_sessions ADD COLUMN {column} {col_type}")
                )
        rows = conn.execute(
            text("SELECT id FROM discovery_sessions WHERE access_key IS NULL OR access_key = ''")
        ).fetchall()
        for row in rows:
            key = secrets.token_urlsafe(32)
            conn.execute(
                text("UPDATE discovery_sessions SET access_key = :key WHERE id = :id"),
                {"key": key, "id": row[0]},
            )
        conn.commit()


def migrate_db(engine=None) -> None:
    """Alias used by tests to migrate a specific engine."""
    run_migrations(engine)


def create_db_and_tables() -> None:
    run_migrations()


def get_session() -> Session:
    return Session(engine)
