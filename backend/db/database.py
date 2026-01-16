"""Database connection and session management."""

from sqlmodel import create_engine, Session, SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
import os


# System database (users, workspaces, permissions, tasks)
SYSTEM_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./codex_system.db")

# Data directory for workspaces (derived from database path or env var)
_default_data_dir = os.path.dirname(SYSTEM_DATABASE_URL.replace("sqlite:///", "")) or "./data"
DATA_DIRECTORY = os.getenv("DATA_DIRECTORY", _default_data_dir)
SYSTEM_DATABASE_URL_ASYNC = SYSTEM_DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")

system_engine = create_async_engine(SYSTEM_DATABASE_URL_ASYNC, echo=True, connect_args={"check_same_thread": False})

async_session_maker = sessionmaker(system_engine, class_=AsyncSession, expire_on_commit=False)


async def get_system_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session for system database."""
    async with async_session_maker() as session:
        yield session


async def init_system_db():
    """Initialize system database tables."""
    async with system_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


def get_notebook_engine(notebook_path: str):
    """Get database engine for a specific notebook."""
    db_path = os.path.join(notebook_path, ".codex", "notebook.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return create_engine(f"sqlite:///{db_path}", echo=False)


def init_notebook_db(notebook_path: str):
    """Initialize notebook database tables."""
    engine = get_notebook_engine(notebook_path)
    SQLModel.metadata.create_all(engine)
    return engine


def get_notebook_session(notebook_path: str):
    """Get database session for a specific notebook."""
    engine = get_notebook_engine(notebook_path)
    return Session(engine)
