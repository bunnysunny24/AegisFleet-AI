"""
Database configuration and session management.
Supports PostgreSQL (with fallback to SQLite for local tests or lightweight demonstration).
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from services.core_api.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aegis_fleet.db")

# Fix for Heroku/Render postgres:// prefix if used
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite-specific connect args
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initializes tables in database."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
