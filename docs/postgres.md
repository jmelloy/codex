# PostgreSQL Setup (System Database)

Codex's system database (users, workspaces, permissions, tasks, agents, comments, orgs) supports
two backends, selected by the `DATABASE_URL` environment variable:

- **SQLite** (default) - single file, single-writer. Fine for single-user installs.
- **PostgreSQL** - required once Organizations or shared workspaces are in use (see
  [issue #539](https://github.com/jmelloy/codex/issues/539), part of #521). Orgs, comments,
  events, and notifications are hot multi-writer tables; SQLite's single-writer lock is the
  first thing that falls over under concurrent access.

Per-notebook databases (`.codex/notebook.db`) always stay on SQLite regardless of this setting -
they're a derived, per-replica search index, not shared state.

## Quick start (Docker Compose)

```bash
cp .env.example .env   # set SECRET_KEY at minimum
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d
```

This starts a `postgres` service alongside the usual `redis`/`backend`/`worker`/`frontend`
services and points the backend/worker at it. Override `POSTGRES_USER` / `POSTGRES_PASSWORD` /
`POSTGRES_DB` in `.env` if you don't want the defaults (`codex`/`codex`/`codex_system`).

## Quick start (local dev, no Docker)

```bash
cd backend
pip install -e ".[dev,postgres]"

createdb codex_system
export DATABASE_URL=postgresql://localhost/codex_system
alembic upgrade head
uvicorn codex.main:app --reload --port 8000
```

The `postgres` extra installs `asyncpg` (used by the app's async engine) and `psycopg2-binary`
(used by Alembic's sync engine for migrations).

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/codex_system.db` | `postgresql://user:pass@host:5432/dbname` selects Postgres |
| `DATABASE_POOL_SIZE` | `10` | Postgres only |
| `DATABASE_MAX_OVERFLOW` | `20` | Postgres only |
| `DATABASE_POOL_RECYCLE` | `1800` (seconds) | Postgres only, avoids stale connections behind a load balancer/proxy |

`DATABASE_URL` accepts either the plain `postgresql://` scheme or a driver-qualified one
(`postgresql+asyncpg://`, `postgresql+psycopg2://`) - the app rewrites it to the right driver
for each engine (async vs. sync) automatically, so a single URL works everywhere.

## Migrating an existing SQLite install to Postgres

1. Stop the app so the SQLite file stops changing.
2. Create the target Postgres database and get its `DATABASE_URL`.
3. Run migrations against the empty Postgres database to create the schema:
   ```bash
   DATABASE_URL=postgresql://user:pass@host:5432/codex_system alembic upgrade head
   ```
4. Copy the data table-by-table. [`pgloader`](https://pgloader.io/) handles the SQLite → Postgres
   type conversions (booleans, JSON columns) directly:
   ```bash
   pgloader sqlite:///./data/codex_system.db postgresql://user:pass@host:5432/codex_system
   ```
   For a smaller install, exporting each table with `sqlite3 .dump` and re-importing via `psql`
   works too, but JSON columns (`personal_access_tokens.scopes`, `agents.scope`, etc.) are stored
   as TEXT in SQLite and must be cast to `json`/`jsonb` on the way in.
5. Point `DATABASE_URL` at the Postgres database and restart the app.
6. Verify row counts match between the old SQLite file and the new Postgres database before
   deleting the SQLite file.

## Testing against Postgres

The full backend test suite (`pytest`) respects a pre-set `DATABASE_URL`, so it runs unchanged
against either backend:

```bash
DATABASE_URL=postgresql://localhost/codex_system_test pytest -v
```

CI runs the suite against both SQLite and Postgres as a matrix job (`.github/workflows/test.yml`).

## Known SQLite-isms audited for this change

- **Boolean `server_default`s** in migrations used bare `"0"`/`"1"` string literals; these are
  rewritten as `sa.text("true")`/`sa.text("false")` so both backends parse them as booleans
  rather than relying on Postgres's implicit string-to-boolean cast.
- **String → JSON column conversions** (`personal_access_tokens.scopes`) need an explicit
  `postgresql_using="scopes::json"` cast - Postgres has no implicit assignment cast from
  `varchar` to `json`, unlike SQLite's dynamic typing.
- **Column introspection** in migrations used `PRAGMA table_info(...)`, a SQLite-only statement;
  replaced with `sqlalchemy.inspect(conn).get_columns(...)`, which works on both backends.
- **Timestamps** already used dialect-conditional `TIMESTAMP WITH TIME ZONE` handling for
  Postgres (migration `012`) - timezone-aware datetimes written from Python raise on a plain
  Postgres `TIMESTAMP` column but are accepted by SQLite regardless.
- `Block.path`'s `BINARY` collation is a per-notebook SQLite database concern only (notebook DBs
  stay SQLite always) and is out of scope for the system database covered here.
