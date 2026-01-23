# Notebook Database Alembic Migration Implementation

## Overview

This document describes the implementation of Alembic migrations for per-notebook databases in the Codex project. Previously, notebook databases used `SQLModel.metadata.create_all()` for schema creation and manual migration scripts. They now use Alembic for all schema management, matching the approach used for the system database.

## Architecture

### Dual Alembic Setup

The project now has two separate Alembic environments:

1. **System Database** (`backend/alembic/`)
   - Configuration: `backend/alembic.ini`
   - Manages: users, workspaces, permissions, tasks, notebook metadata
   - Database: `codex_system.db`

2. **Notebook Databases** (`backend/notebook_alembic/`)
   - Configuration: `backend/notebook_alembic.ini`
   - Manages: file_metadata, tags, file_tags, search_index
   - Database: per-notebook `.codex/notebook.db` files

### Why Separate Environments?

- Each notebook has its own database file
- The same migrations need to run on multiple database instances
- System and notebook schemas are completely independent
- Allows notebook portability (notebooks can be moved/copied)

## Implementation Details

### New Files Created

```
backend/
├── notebook_alembic.ini                # Alembic configuration for notebooks
├── notebook_alembic/
│   ├── env.py                          # Alembic environment setup
│   ├── script.py.mako                  # Migration template
│   └── versions/
│       ├── 20250123_000000_001_initial_notebook_schema.py       # Migration 001
│       └── 20250123_000001_002_rename_frontmatter_to_properties.py  # Migration 002
└── tests/
    └── test_notebook_migrations.py     # Comprehensive test suite
```

### Migration Strategy

#### Fresh Databases (No Tables)

For new notebooks, migrations run sequentially:
1. Migration 001: Create all tables (file_metadata, tags, file_tags, search_index)
2. Migration 002: No-op (column already has correct name)

Result: `alembic_version` = `002`

#### Pre-Alembic Databases (Has Tables, No alembic_version)

For existing notebooks that predate Alembic:

1. **Detect schema state** by inspecting the `file_metadata` table:
   - Has `frontmatter` column → stamp at `001`, run migration `002` to rename
   - Has `properties` column → stamp at `head` (already migrated)

2. **Auto-stamping** ensures Alembic knows the current state without re-running migrations

This approach is idempotent and safe for existing data.

### Key Code Changes

#### `backend/db/database.py`

Added `run_notebook_alembic_migrations()`:
- Detects whether database needs stamping
- Stamps pre-Alembic databases at appropriate revision
- Runs any pending migrations
- Handles both fresh installs and upgrades

Modified `init_notebook_db()`:
- Now calls `run_notebook_alembic_migrations()` instead of `SQLModel.metadata.create_all()`
- Returns the engine after migrations complete

#### `backend/notebook_alembic/env.py`

Key features:
- Reads database URL from Alembic config (set programmatically)
- Creates empty metadata (no models imported to avoid system model pollution)
- Supports both online and offline migration modes

#### Migration Files

**Migration 001: Initial Schema**
- Creates all 4 tables with proper columns
- No conditional checks (assumes fresh database)
- Includes indexes for common query patterns

**Migration 002: Frontmatter to Properties**
- Renames `frontmatter` column to `properties` if it exists
- Uses try/except to handle missing column (no-op for fresh installs)
- Compatible with SQLite's batch alter operations

### Testing

Created comprehensive test suite (`test_notebook_migrations.py`):

1. **test_init_fresh_notebook_db**: Verifies fresh database creation
2. **test_migrate_existing_notebook_with_frontmatter**: Tests upgrade path for old databases
3. **test_idempotent_migrations**: Ensures migrations can be re-run safely
4. **test_notebook_alembic_version**: Confirms version tracking works correctly

All tests pass ✅

## Usage

### Creating a New Notebook

```python
from backend.db.database import init_notebook_db

# Automatically runs Alembic migrations
engine = init_notebook_db("/path/to/notebook")
```

### Running Migrations Manually (CLI)

```bash
# From backend directory
python -m alembic -c notebook_alembic.ini \
  -x sqlalchemy.url=sqlite:////path/to/notebook/.codex/notebook.db \
  upgrade head
```

### Checking Current Version

```python
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:////path/to/notebook/.codex/notebook.db")
with engine.connect() as conn:
    result = conn.execute(text("SELECT version_num FROM alembic_version"))
    print(f"Current version: {result.scalar()}")
```

## Benefits

1. **Consistency**: Same migration approach for both system and notebook databases
2. **Versioning**: Clear tracking of schema versions via `alembic_version` table
3. **Rollback**: Downgrade support (though typically not needed)
4. **Automation**: Migrations run automatically on notebook initialization
5. **Safety**: Idempotent migrations prevent accidental re-application
6. **Portability**: Notebooks can be moved between installations
7. **Auditing**: Clear migration history for debugging

## Backward Compatibility

### Legacy Code (Deprecated)

- `backend/db/migrations.py`: Kept for reference, marked as deprecated
- `backend/db/system_migrations/`: Old manual migrations, marked as deprecated with README

### Existing Notebooks

Pre-Alembic notebooks are automatically detected and migrated:
- No manual intervention required
- Data is preserved during migration
- Auto-stamping prevents re-running migrations

## Future Migrations

### Adding a New Migration

1. Generate migration template:
   ```bash
   cd backend
   python -m alembic -c notebook_alembic.ini revision -m "add_new_column"
   ```

2. Edit the generated file in `backend/notebook_alembic/versions/`

3. Test the migration:
   ```python
   from backend.db.database import init_notebook_db
   engine = init_notebook_db("/path/to/test/notebook")
   ```

4. Verify with tests:
   ```bash
   pytest tests/test_notebook_migrations.py
   ```

### Best Practices

- Keep migrations focused and small
- Test both upgrade and downgrade paths
- Handle edge cases (missing columns, etc.)
- Document breaking changes in migration docstrings
- Test with real data when possible

## Troubleshooting

### Migration Fails with "table already exists"

This means Alembic doesn't know the current state. Solution:
- Check if `alembic_version` table exists
- If missing, the auto-stamping should handle it
- Verify `run_notebook_alembic_migrations()` is being called

### Version is incorrect

Check the version:
```sql
SELECT version_num FROM alembic_version;
```

Manually stamp if needed:
```bash
python -m alembic -c notebook_alembic.ini \
  -x sqlalchemy.url=sqlite:////path/to/notebook/.codex/notebook.db \
  stamp head
```

### Migration creates duplicate tables

This shouldn't happen with the current implementation. If it does:
1. Check that `table_exists()` logic is working
2. Verify migration has proper guards
3. Check Alembic version tracking

## References

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- System database migrations: `backend/alembic/`
- Original manual migrations (deprecated): `backend/db/migrations.py`
