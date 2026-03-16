import os

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def get_database_uri() -> str:
    """Use PostgreSQL in production when DATABASE_URL exists, fallback to local SQLite."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Some platforms provide postgres:// which SQLAlchemy expects as postgresql://
        return database_url.replace("postgres://", "postgresql://", 1)

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sqlite_path = os.path.join(base_dir, "database", "lms.db")
    return f"sqlite:///{sqlite_path}"
