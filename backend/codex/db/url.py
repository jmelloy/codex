"""Database URL / dialect helpers shared by the app and the Alembic env scripts.

Codex's system database supports two backends: SQLite (default, single-user
installs) and PostgreSQL (multi-writer installs, required for Organizations).
These helpers centralize how a single ``DATABASE_URL`` is turned into the
async driver URL (aiosqlite / asyncpg), the sync driver URL (pysqlite /
psycopg2), and the DBAPI ``connect_args`` appropriate for each backend, so
that driver-specific details don't leak into callers.
"""

from sqlalchemy.engine import make_url

SUPPORTED_BACKENDS = ("sqlite", "postgresql")


def get_backend_name(database_url: str) -> str:
    """Return 'sqlite' or 'postgresql' regardless of which driver is in the URL."""
    backend = make_url(database_url).get_backend_name()
    if backend not in SUPPORTED_BACKENDS:
        raise ValueError(
            f"Unsupported database backend {backend!r} in DATABASE_URL; "
            f"Codex supports: {', '.join(SUPPORTED_BACKENDS)}"
        )
    return backend


def is_sqlite(database_url: str) -> bool:
    return get_backend_name(database_url) == "sqlite"


def is_postgres(database_url: str) -> bool:
    return get_backend_name(database_url) == "postgresql"


def to_async_url(database_url: str) -> str:
    """Rewrite the URL to use the async DBAPI driver for its backend."""
    url = make_url(database_url)
    backend = get_backend_name(database_url)
    driver = "sqlite+aiosqlite" if backend == "sqlite" else "postgresql+asyncpg"
    return url.set(drivername=driver).render_as_string(hide_password=False)


def to_sync_url(database_url: str) -> str:
    """Rewrite the URL to use the sync DBAPI driver for its backend (used by Alembic)."""
    url = make_url(database_url)
    backend = get_backend_name(database_url)
    driver = "sqlite" if backend == "sqlite" else "postgresql+psycopg2"
    return url.set(drivername=driver).render_as_string(hide_password=False)


def connect_args_for(database_url: str) -> dict:
    """DBAPI ``connect_args`` for the backend behind ``database_url``.

    SQLite's DBAPI defaults to raising if a connection is used from a thread
    other than the one that created it; Codex shares connections across the
    async event loop and thread-pool workers, so that check must be disabled.
    Postgres drivers have no equivalent restriction.
    """
    if is_sqlite(database_url):
        return {"check_same_thread": False}
    return {}
