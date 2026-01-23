# System Migrations (DEPRECATED)

**This directory contains legacy migration scripts that are no longer used.**

## Current Migration System

The system database now uses **Alembic** for all migrations:
- Configuration: `backend/alembic.ini`
- Environment: `backend/alembic/env.py`
- Migrations: `backend/alembic/versions/`

## Historical Migrations

The scripts in this directory were used before Alembic was adopted:

- `add_notebooks_to_system_db.py` - Added notebooks table (now handled by Alembic migration 001)
- `add_theme_setting.py` - Added theme_setting column (now handled by Alembic migration 001)

These files are kept for historical reference only and should not be used for new installations or upgrades.

## Migration Status

All functionality from these legacy scripts has been incorporated into Alembic migrations:
- `backend/alembic/versions/20250123_000000_001_initial_system_schema.py` includes all tables and columns

New system database installations use Alembic migrations exclusively.
