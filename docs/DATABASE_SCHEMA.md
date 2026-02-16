# Codex Database Schema Documentation

**Version:** 1.0 | **Date:** 2026-02-16

## Overview

Codex uses a unique two-database architecture:
- **System Database** (`codex_system.db`) - Global entities
- **Notebook Databases** (`.codex/notebook.db` per notebook) - Per-notebook data

This design enables horizontal scalability while maintaining simplicity for single-server deployments.

## System Database Schema

**Location:** `codex_system.db` (SQLite, upgradeable to PostgreSQL)

### Entity Relationship Diagram

```
┌─────────────┐
│    User     │
│─────────────│
│ id (PK)     │◄──┐
│ username    │   │
│ email       │   │
│ password_hash│  │
│ created_at  │   │
└─────────────┘   │
                  │ owner_id
                  │
┌─────────────┐   │
│  Workspace  │   │
│─────────────│   │
│ id (PK)     │◄──┘
│ name        │
│ slug        │
│ path        │◄──┐
│ owner_id(FK)│   │
│ created_at  │   │
└──────┬──────┘   │
       │          │ workspace_id
       │          │
       ├──────────┼─────────────────┐
       │          │                 │
       ▼          │                 ▼
┌─────────────┐   │      ┌─────────────────┐
│ Notebook    │   │      │WorkspacePermission│
│─────────────│   │      │─────────────────│
│ id (PK)     │   │      │ id (PK)         │
│ workspace_id├───┘      │ workspace_id(FK)│
│ name        │          │ user_id (FK)    │
│ path        │          │ role            │
│ created_at  │          │ created_at      │
└──────┬──────┘          └─────────────────┘
       │
       │
       ├─────────────────────┬──────────────┐
       │                     │              │
       ▼                     ▼              ▼
┌─────────────┐      ┌─────────────┐  ┌─────────────┐
│    Task     │      │   Agent     │  │PluginConfig │
│─────────────│      │─────────────│  │─────────────│
│ id (PK)     │      │ id (PK)     │  │ id (PK)     │
│ notebook_id │      │ workspace_id│  │ workspace_id│
│ type        │      │ name        │  │ plugin_id   │
│ status      │      │ provider    │  │ config      │
│ created_at  │      │ model       │  │ enabled     │
└─────────────┘      └──────┬──────┘  └─────────────┘
                            │
                            │
                            ▼
                    ┌─────────────┐
                    │AgentSession │
                    │─────────────│
                    │ id (PK)     │
                    │ agent_id(FK)│
                    │ notebook_id │
                    │ status      │
                    │ messages    │
                    │ created_at  │
                    └─────────────┘

┌─────────────┐
│   Plugin    │
│─────────────│
│ id (PK)     │◄───┐
│ name        │    │
│ version     │    │
│ manifest    │    │
│ enabled     │    │
└─────────────┘    │ plugin_id
                   │
            ┌──────┴─────┐
            │            │
            ▼            ▼
    ┌─────────────┐  ┌─────────────┐
    │PluginConfig │  │PluginSecret │
    │─────────────│  │─────────────│
    │ id (PK)     │  │ id (PK)     │
    │ plugin_id   │  │ plugin_id   │
    │ workspace_id│  │ workspace_id│
    │ config      │  │ key         │
    │ enabled     │  │ encrypted_val│
    └─────────────┘  └─────────────┘
```

### Table Definitions

#### User

```sql
CREATE TABLE user (
    id TEXT PRIMARY KEY,              -- ULID
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    hashed_password TEXT NOT NULL,    -- PBKDF2-SHA256
    full_name TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_username ON user (username);
CREATE INDEX idx_user_email ON user (email);
```

**Columns:**
- `id`: ULID primary key for distributed compatibility
- `username`: Unique username for login (3-32 chars)
- `email`: Optional email for password recovery
- `hashed_password`: Format: `pbkdf2_sha256:100000:salt:hash`
- `is_active`: Soft account disable flag
- `is_superuser`: Admin privileges flag

#### Workspace

```sql
CREATE TABLE workspace (
    id TEXT PRIMARY KEY,              -- ULID
    name TEXT NOT NULL,
    slug TEXT UNIQUE,                 -- URL-friendly identifier
    path TEXT NOT NULL,               -- Absolute filesystem path
    description TEXT,
    owner_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES user (id) ON DELETE CASCADE
);

CREATE INDEX idx_workspace_owner ON workspace (owner_id);
CREATE INDEX idx_workspace_slug ON workspace (slug);
```

**Columns:**
- `slug`: Auto-generated from name (e.g., "My Lab" → "my-lab")
- `path`: Absolute path where notebooks are stored
- `owner_id`: Primary owner (can delegate via permissions)

**Constraints:**
- Unique slug across all workspaces
- Path must be absolute and exist on filesystem
- Owner must be active user

#### WorkspacePermission

```sql
CREATE TABLE workspace_permission (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,              -- owner, editor, viewer
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workspace_id) REFERENCES workspace (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
    UNIQUE (workspace_id, user_id)
);

CREATE INDEX idx_permission_workspace ON workspace_permission (workspace_id);
CREATE INDEX idx_permission_user ON workspace_permission (user_id);
```

**Roles:**
- `owner`: Full control (delete workspace, manage permissions)
- `editor`: Read/write files, create notebooks
- `viewer`: Read-only access

#### Notebook

```sql
CREATE TABLE notebook (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    path TEXT NOT NULL,              -- Relative to workspace path
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workspace_id) REFERENCES workspace (id) ON DELETE CASCADE,
    UNIQUE (workspace_id, path)
);

CREATE INDEX idx_notebook_workspace ON notebook (workspace_id);
CREATE INDEX idx_notebook_path ON notebook (path);
```

**Columns:**
- `path`: Relative to workspace (e.g., "experiments/ml-2024")
- Each notebook has own database at `<full_path>/.codex/notebook.db`

#### Task

```sql
CREATE TABLE task (
    id TEXT PRIMARY KEY,
    workspace_id TEXT,
    notebook_id TEXT,
    agent_id TEXT,
    type TEXT NOT NULL,              -- agent_execution, indexing, sync
    status TEXT NOT NULL,            -- pending, running, completed, failed
    input_data TEXT,                 -- JSON
    output_data TEXT,                -- JSON
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (workspace_id) REFERENCES workspace (id) ON DELETE CASCADE,
    FOREIGN KEY (notebook_id) REFERENCES notebook (id) ON DELETE CASCADE
);

CREATE INDEX idx_task_status ON task (status, created_at);
CREATE INDEX idx_task_workspace ON task (workspace_id);
```

**Task Types:**
- `agent_execution`: AI agent task
- `indexing`: Full-text search index update
- `sync`: Manual sync request

**Status Flow:**
```
pending → running → completed
              ↓
            failed
```

#### Plugin

```sql
CREATE TABLE plugin (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    plugin_type TEXT NOT NULL,       -- view, theme, integration, combo
    manifest TEXT NOT NULL,          -- JSON manifest content
    enabled BOOLEAN DEFAULT TRUE,
    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_plugin_type ON plugin (plugin_type);
CREATE INDEX idx_plugin_enabled ON plugin (enabled);
```

**Plugin Types:**
- `view`: Custom UI components
- `theme`: Visual styling
- `integration`: External API connection
- `combo`: Multiple types in one plugin

#### PluginConfig

```sql
CREATE TABLE plugin_config (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    plugin_id TEXT NOT NULL,
    config TEXT,                     -- JSON configuration
    enabled BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (workspace_id) REFERENCES workspace (id) ON DELETE CASCADE,
    FOREIGN KEY (plugin_id) REFERENCES plugin (id) ON DELETE CASCADE,
    UNIQUE (workspace_id, plugin_id)
);

CREATE INDEX idx_plugin_config_workspace ON plugin_config (workspace_id);
```

**Purpose:** Per-workspace plugin settings

#### PluginSecret

```sql
CREATE TABLE plugin_secret (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    plugin_id TEXT NOT NULL,
    key TEXT NOT NULL,
    encrypted_value TEXT NOT NULL,   -- Fernet-encrypted
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workspace_id) REFERENCES workspace (id) ON DELETE CASCADE,
    FOREIGN KEY (plugin_id) REFERENCES plugin (id) ON DELETE CASCADE,
    UNIQUE (workspace_id, plugin_id, key)
);

CREATE INDEX idx_plugin_secret_workspace ON plugin_secret (workspace_id);
```

**Encryption:** Uses Fernet (symmetric encryption) with key derived from `SECRET_KEY`

#### Agent

```sql
CREATE TABLE agent (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    provider TEXT NOT NULL,          -- openai, anthropic, litellm
    model TEXT NOT NULL,             -- gpt-4, claude-3-opus, etc.
    system_prompt TEXT,
    tools TEXT,                      -- JSON array of tool names
    config TEXT,                     -- JSON provider-specific config
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workspace_id) REFERENCES workspace (id) ON DELETE CASCADE
);

CREATE INDEX idx_agent_workspace ON agent (workspace_id);
```

**Providers:**
- `openai`: OpenAI API
- `anthropic`: Anthropic API
- `litellm`: LiteLLM unified interface

#### AgentSession

```sql
CREATE TABLE agent_session (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    notebook_id TEXT,
    status TEXT NOT NULL,            -- active, completed, failed
    messages TEXT,                   -- JSON array of messages
    actions TEXT,                    -- JSON array (audit log)
    token_usage TEXT,                -- JSON token stats
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agent (id) ON DELETE CASCADE,
    FOREIGN KEY (notebook_id) REFERENCES notebook (id) ON DELETE SET NULL
);

CREATE INDEX idx_agent_session_agent ON agent_session (agent_id);
CREATE INDEX idx_agent_session_status ON agent_session (status);
```

**Session Lifecycle:**
```
User creates session → active
  ↓
Agent processes messages → active (with message history)
  ↓
Completes or errors → completed/failed
```

## Notebook Database Schema

**Location:** `<notebook_path>/.codex/notebook.db` (one per notebook)

### Entity Relationship Diagram

```
┌─────────────┐
│FileMetadata │
│─────────────│
│ id (PK)     │◄────┐
│ path        │     │
│ filename    │     │ file_id
│ size        │     │
│ mime_type   │     │
│ content_hash│     │
│ title       │     │
│ properties  │     │
│ git_tracked │     ▼
│ created_at  │  ┌─────────┐
└──────┬──────┘  │FileTag  │
       │         │─────────│
       │         │ id (PK) │
       │         │ file_id │◄──┐
       │         │ tag_id  │   │
       │         └────┬────┘   │
       │              │ tag_id │
       │              │        │
       │              ▼        │
       │         ┌─────────┐   │
       └────────►│   Tag   │◄──┘
                 │─────────│
                 │ id (PK) │
                 │ name    │
                 │ color   │
                 └─────────┘

┌──────────────┐
│ SearchIndex  │  (FTS5 virtual table)
│──────────────│
│ file_id      │
│ path         │
│ title        │
│ content      │
│ tags         │
└──────────────┘
```

### Table Definitions

#### FileMetadata

```sql
CREATE TABLE file_metadata (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,       -- Relative to notebook root
    filename TEXT NOT NULL,
    extension TEXT,
    size INTEGER,
    mime_type TEXT,
    
    -- Content tracking
    content_hash TEXT,               -- SHA256 for change detection
    last_modified TIMESTAMP,
    
    -- Parsed metadata
    title TEXT,
    properties TEXT,                 -- JSON (flexible metadata)
    
    -- Git integration
    git_tracked BOOLEAN DEFAULT FALSE,
    git_commit_hash TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP             -- Soft delete
);

CREATE INDEX idx_file_path ON file_metadata (path);
CREATE INDEX idx_file_updated ON file_metadata (updated_at DESC);
CREATE INDEX idx_file_deleted ON file_metadata (deleted_at);
CREATE INDEX idx_file_extension ON file_metadata (extension);
```

**Properties JSON Format:**
```json
{
  "status": "in-progress",
  "date": "2024-01-01",
  "author": "John Doe",
  "experiment_id": "exp-123",
  "custom_field": "value"
}
```

#### Tag

```sql
CREATE TABLE tag (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    color TEXT,                      -- Hex color code (#3b82f6)
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tag_name ON tag (name);
```

**Common Tags:**
- `experiment`
- `analysis`
- `results`
- `todo`
- `in-progress`
- `completed`

#### FileTag

```sql
CREATE TABLE file_tag (
    id TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    tag_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES file_metadata (id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tag (id) ON DELETE CASCADE,
    UNIQUE (file_id, tag_id)
);

CREATE INDEX idx_file_tag_file ON file_tag (file_id);
CREATE INDEX idx_file_tag_tag ON file_tag (tag_id);
```

#### SearchIndex (FTS5 Virtual Table)

```sql
CREATE VIRTUAL TABLE search_index USING fts5(
    file_id UNINDEXED,
    path UNINDEXED,
    title,
    content,
    tags,
    tokenize='porter unicode61'
);
```

**Usage:**
```sql
-- Full-text search
SELECT file_id, highlight(search_index, 2, '<mark>', '</mark>') as snippet
FROM search_index
WHERE search_index MATCH 'experiment AND results'
ORDER BY rank;
```

## Data Migration Patterns

### Cross-Database Queries

**Pattern:** Query system DB for permissions, then query notebook DB for data

```python
# 1. Validate access (system DB)
notebook = session.exec(
    select(Notebook).where(Notebook.id == notebook_id)
).first()

if not has_permission(user, notebook.workspace):
    raise HTTPException(403, "Access denied")

# 2. Get notebook session
notebook_session = get_notebook_session(notebook.db_path)

# 3. Query file data (notebook DB)
files = notebook_session.exec(
    select(FileMetadata)
    .where(FileMetadata.deleted_at.is_(None))
).all()
```

### Alembic Migrations

**Workspace Migrations:**
```bash
# Create migration
alembic -n workspace revision -m "Add agent_session table"

# Generated file: codex/migrations/workspace/versions/xxx_add_agent_session.py
def upgrade():
    op.create_table(
        'agent_session',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        # ...
    )

# Apply
alembic -n workspace upgrade head
```

**Notebook Migrations:**
```bash
# Create migration
alembic -n notebook revision -m "Add search_index table"

# Apply to all notebooks (automated on startup)
for notebook in notebooks:
    alembic -n notebook -x db_path=<notebook_db_path> upgrade head
```

### SQLite to PostgreSQL Migration

**Migration Script:**
```python
# scripts/migrate_to_postgres.py
import sqlite3
import psycopg2

def migrate_system_db():
    # 1. Export SQLite to SQL dump
    sqlite_conn = sqlite3.connect('codex_system.db')
    dump = sqlite_conn.iterdump()
    
    # 2. Convert SQLite syntax to PostgreSQL
    pg_dump = convert_sqlite_to_postgres(dump)
    
    # 3. Import to PostgreSQL
    pg_conn = psycopg2.connect(DATABASE_URL)
    cursor = pg_conn.cursor()
    cursor.execute(pg_dump)
    pg_conn.commit()

# Notebook DBs remain SQLite (distributed)
```

## Query Optimization

### Common Query Patterns

**List Files with Tags:**
```sql
SELECT 
    fm.id, 
    fm.path, 
    fm.title,
    GROUP_CONCAT(t.name) as tags
FROM file_metadata fm
LEFT JOIN file_tag ft ON fm.id = ft.file_id
LEFT JOIN tag t ON ft.tag_id = t.id
WHERE fm.deleted_at IS NULL
GROUP BY fm.id
ORDER BY fm.updated_at DESC
LIMIT 50;
```

**Full-Text Search with Metadata:**
```sql
SELECT 
    fm.*,
    snippet(search_index, 3, '<mark>', '</mark>', '...', 32) as snippet,
    rank
FROM search_index si
JOIN file_metadata fm ON si.file_id = fm.id
WHERE search_index MATCH 'experiment AND pytorch'
AND fm.deleted_at IS NULL
ORDER BY rank
LIMIT 20;
```

**Filter by Properties:**
```sql
SELECT *
FROM file_metadata
WHERE 
    json_extract(properties, '$.status') = 'in-progress'
    AND json_extract(properties, '$.date') >= '2024-01-01'
    AND deleted_at IS NULL;
```

### Index Strategy

**High-Cardinality Columns:**
- `user.username` - UNIQUE index
- `workspace.slug` - UNIQUE index
- `file_metadata.path` - UNIQUE index

**Composite Indexes:**
```sql
-- Common workspace queries
CREATE INDEX idx_notebook_workspace_path ON notebook (workspace_id, path);

-- Common file queries
CREATE INDEX idx_file_tags ON file_metadata (deleted_at, updated_at);
```

**FTS5 Index:**
- Automatically maintained
- Tokenizes with Porter stemming + Unicode normalization

## Database Maintenance

### Vacuum (SQLite)

```bash
# System DB
sqlite3 codex_system.db "VACUUM;"

# Notebook DBs
find /data/workspaces -name "notebook.db" -exec sqlite3 {} "VACUUM;" \;
```

**Frequency:** Monthly or after large deletes

### Analyze (Query Planner)

```bash
# Update statistics for query optimizer
sqlite3 codex_system.db "ANALYZE;"
```

**Frequency:** Weekly or after schema changes

### Integrity Check

```bash
# Check for corruption
sqlite3 codex_system.db "PRAGMA integrity_check;"
```

**Frequency:** Daily in production

### Backup

**SQLite Backup:**
```bash
# System DB
sqlite3 codex_system.db ".backup /backups/codex_system_$(date +%Y%m%d).db"

# Notebook DBs
for db in $(find /data/workspaces -name "notebook.db"); do
    sqlite3 "$db" ".backup ${db}.backup"
done
```

**PostgreSQL Backup:**
```bash
pg_dump -Fc codex_system > /backups/codex_system_$(date +%Y%m%d).dump
```

## Schema Evolution

### Version History

| Version | Date       | Changes                                |
|---------|------------|----------------------------------------|
| 1.0     | 2024-01-15 | Initial schema                         |
| 1.1     | 2024-02-20 | Add plugin system tables               |
| 1.2     | 2024-03-10 | Add agent and agent_session tables     |
| 1.3     | 2024-04-05 | Add search_index FTS5 table            |
| 1.4     | 2024-05-15 | Rename frontmatter to properties       |
| 1.5     | 2026-01-28 | Add plugin_secret for encrypted keys   |

### Migration Best Practices

1. **Backward Compatible Changes:**
   - Add new columns with defaults
   - Add new tables
   - Add new indexes

2. **Breaking Changes:**
   - Rename columns (require data migration)
   - Change column types
   - Remove tables/columns

3. **Migration Testing:**
   - Test on copy of production data
   - Verify rollback procedure
   - Document manual steps

4. **Zero-Downtime Migrations:**
   - Add new column → deploy code → backfill → remove old column
   - Use feature flags for gradual rollout

---

*This document is maintained by the Codex development team. For questions, see the main [ARCHITECTURE.md](ARCHITECTURE.md) document.*
