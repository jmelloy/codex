# Codex Architecture

**Version**: 1.0  
**Date**: 2026-02-16  
**Status**: Current Architecture

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Architecture Patterns](#architecture-patterns)
4. [Core Components](#core-components)
5. [Data Architecture](#data-architecture)
6. [Security Architecture](#security-architecture)
7. [Integration Points](#integration-points)
8. [Deployment Architecture](#deployment-architecture)
9. [Strengths](#strengths)
10. [Recommendations](#recommendations)
11. [Future Considerations](#future-considerations)

---

## Executive Summary

Codex is a modern, hierarchical digital laboratory journal system built with a clear separation of concerns, strong typing, and extensibility in mind. The architecture follows contemporary best practices for full-stack applications with FastAPI backend and Vue.js frontend.

**Key Architectural Decisions:**
- Two-database pattern (system + per-notebook) for scalability and isolation
- Plugin-based extensibility for views, themes, and integrations
- Real-time file watching with change detection and WebSocket notifications
- Scoped AI agent system with permission boundaries
- RESTful API with clear resource hierarchy

---

## System Overview

### Technology Stack

#### Backend
- **Framework**: FastAPI 0.115+ (Python 3.13+)
- **ORM**: SQLModel (combines SQLAlchemy + Pydantic)
- **Database**: SQLite with async support (aiosqlite)
- **Migrations**: Alembic with dual migration paths
- **Authentication**: JWT tokens with OAuth2 password flow
- **Password Hashing**: PBKDF2 with SHA-256
- **Real-time**: WebSocket support via FastAPI WebSockets
- **File Watching**: Watchdog library for filesystem monitoring
- **AI Integration**: LiteLLM for multi-provider AI support

#### Frontend
- **Framework**: Vue.js 3.5+ with Composition API
- **State Management**: Pinia stores
- **Type System**: TypeScript 5.7+
- **Build Tool**: Vite 6+
- **HTTP Client**: Axios for API communication
- **Testing**: Vitest for unit/component tests

#### Infrastructure
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Docker Compose
- **Web Server**: Nginx for production frontend
- **CORS**: Configurable cross-origin support

### System Hierarchy

```
User
 └── Workspace (owns, multiple)
      ├── Notebook (contains, multiple)
      │    ├── Files (markdown, images, data files)
      │    ├── Folders (hierarchical organization)
      │    ├── Tags (file organization)
      │    └── Database (.codex/notebook.db)
      ├── Agents (AI assistants, scoped)
      └── Plugins (workspace-level configuration)
```

---

## Architecture Patterns

### 1. Two-Database Pattern

**Implementation:**
- **System Database** (`codex_system.db`): Centralized metadata
  - Users, workspaces, workspace permissions
  - Tasks, notebook registry
  - Plugin configurations and secrets
  - Agent configurations and credentials
  - Integration artifacts

- **Notebook Databases** (`.codex/notebook.db` per notebook): Isolated data
  - File metadata and properties
  - Tags and file-tag relationships
  - Full-text search index
  - Local to each notebook directory

**Rationale:**
- **Scalability**: Notebook databases can be distributed across filesystems
- **Isolation**: Notebook corruption doesn't affect system or other notebooks
- **Flexibility**: Notebooks can be moved/copied with their databases
- **Performance**: Parallel access to different notebooks

**Trade-offs:**
- Complexity in managing multiple databases
- Cross-notebook queries require aggregation at application layer
- Migration management requires dual Alembic configuration

### 2. Clean Architecture / Layered Design

```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                       │
│  ┌──────────────┐              ┌──────────────────────────┐ │
│  │ Vue.js SPA   │◄────────────►│ FastAPI REST API         │ │
│  │ - Views      │  WebSocket   │ - Routes                 │ │
│  │ - Stores     │              │ - Schemas (Pydantic)     │ │
│  │ - Services   │              │ - Auth middleware        │ │
│  └──────────────┘              └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                   │
┌─────────────────────────────────────────────────────────────┐
│                      Business Logic Layer                    │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │ Core Services   │  │ Agents       │  │ Plugins        │ │
│  │ - Watcher       │  │ - Engine     │  │ - Registry     │ │
│  │ - Metadata      │  │ - Scope      │  │ - Loader       │ │
│  │ - Git Manager   │  │ - Tools      │  │ - Executor     │ │
│  │ - WebSocket     │  │ - Provider   │  │                │ │
│  └─────────────────┘  └──────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                   │
┌─────────────────────────────────────────────────────────────┐
│                       Data Access Layer                      │
│  ┌──────────────────────┐        ┌────────────────────────┐ │
│  │ System DB Models     │        │ Notebook DB Models     │ │
│  │ - User               │        │ - FileMetadata         │ │
│  │ - Workspace          │        │ - Tag                  │ │
│  │ - Agent              │        │ - SearchIndex          │ │
│  │ - Plugin             │        │ - FileTag              │ │
│  └──────────────────────┘        └────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                   │
┌─────────────────────────────────────────────────────────────┐
│                      Infrastructure Layer                    │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────┐   │
│  │ SQLite      │  │ Filesystem  │  │ External APIs     │   │
│  │ (async)     │  │ (watched)   │  │ (integrations)    │   │
│  └─────────────┘  └─────────────┘  └───────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 3. Repository Pattern via SQLModel

All database access goes through SQLModel ORM:
- Models define both database schema and API serialization
- Sessions managed via FastAPI dependency injection
- Async/await throughout for non-blocking I/O
- Synchronous sessions available for thread pool operations

### 4. Plugin Architecture

**Three Plugin Types:**
1. **View Plugins**: Custom visualization components (Kanban, Gallery, Rollup, etc.)
2. **Theme Plugins**: Visual styling packages (Antiquarian, Notebook, etc.)
3. **Integration Plugins**: External API connections (GitHub, Weather, OpenGraph)

**Plugin Lifecycle:**
- Plugins built as Vue.js components with TypeScript
- Registered via REST API with manifest validation
- Dynamically loaded in frontend with security boundaries
- Per-workspace or per-notebook configuration

### 5. Event-Driven File Synchronization

```
Filesystem Change
       ↓
Watchdog Observer
       ↓
FileOperationQueue (batched, 5s intervals)
       ↓
Metadata Parser (frontmatter/sidecar)
       ↓
Database Update (FileMetadata)
       ↓
WebSocket Notification
       ↓
Frontend Update (reactive)
```

**Features:**
- Batched operations to reduce database writes
- Hash-based move detection
- Debouncing for rapid changes
- Git integration (auto-commit text files)
- WebSocket push to all connected clients

---

## Core Components

### Backend Components

#### 1. FastAPI Application (`backend/codex/main.py`)
- **Lifespan Management**: Initializes databases, watchers, plugins, WebSocket
- **Middleware**: CORS, request ID tracking
- **Router Inclusion**: Modular route organization
- **Health Checks**: Docker-compatible endpoints

#### 2. File System Watcher (`backend/codex/core/watcher.py`)
- **Technology**: Watchdog library with Observer pattern
- **Queue Processing**: Thread-safe queue with 5-second batching
- **Change Detection**: Hash-based for move operations
- **Metadata Parsing**: Supports multiple formats (frontmatter, JSON, XML, MD sidecars)
- **Git Integration**: Automatic commits for text files (excludes binaries)

#### 3. Database Layer (`backend/codex/db/`)
- **Models**: Split into `system.py` and `notebook.py`
- **Migrations**: Dual Alembic paths (workspace + notebook)
- **Session Management**: Async generators for dependency injection
- **Engine Management**: Separate engines for system and per-notebook databases

#### 4. Authentication (`backend/codex/api/auth.py`)
- **Token Type**: JWT with configurable expiration
- **Storage**: Access token in HTTP-only cookie or Authorization header
- **Hashing**: PBKDF2 with 100,000 iterations and random salt
- **User Retrieval**: Dependency injection for route protection

#### 5. Agent System (`backend/codex/agents/`)
- **Engine**: LiteLLM-based multi-provider support
- **Scope Guards**: Path and action permission enforcement
- **Tool Router**: Dynamic tool routing based on agent capabilities
- **Crypto**: Fernet encryption for API credentials
- **Action Logging**: Audit trail for all agent operations

#### 6. Plugin System (`backend/codex/plugins/`)
- **Registry**: Database-backed plugin registration
- **Loader**: Dynamic plugin loading from filesystem
- **Executor**: Integration plugin execution with logging
- **Security**: Validation of plugin manifests and signatures

### Frontend Components

#### 1. State Management (Pinia Stores)
- **`auth.ts`**: User authentication state
- **`workspace.ts`**: Workspace, notebook, file management with tree structure
- **`theme.ts`**: Theme switching and persistence

#### 2. Services
- **`api.ts`**: Axios client with interceptors for auth
- **`codex.ts`**: Type-safe API wrappers for all resources
- **`websocket.ts`**: Real-time file change notifications
- **`pluginRegistry.ts`**: Dynamic plugin loading and management

#### 3. Router (`frontend/src/router/index.ts`)
- **Route Guards**: Authentication checks
- **Lazy Loading**: Code splitting for better performance
- **Nested Routes**: Workspace → Notebook → File hierarchy

---

## Data Architecture

### System Database Schema

```sql
-- User Management
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR NOT NULL UNIQUE,
    email VARCHAR UNIQUE,
    password_hash VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Workspace Management
CREATE TABLE workspaces (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    slug VARCHAR UNIQUE,
    path VARCHAR NOT NULL,
    owner_id INTEGER REFERENCES users(id),
    theme_setting VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE workspace_permissions (
    id INTEGER PRIMARY KEY,
    workspace_id INTEGER REFERENCES workspaces(id),
    user_id INTEGER REFERENCES users(id),
    role VARCHAR NOT NULL, -- 'owner', 'editor', 'viewer'
    created_at TIMESTAMP
);

-- Notebook Registry
CREATE TABLE notebooks (
    id INTEGER PRIMARY KEY,
    workspace_id INTEGER REFERENCES workspaces(id),
    name VARCHAR NOT NULL,
    slug VARCHAR NOT NULL,
    path VARCHAR NOT NULL,  -- Relative to workspace
    description TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Task Queue
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    workspace_id INTEGER REFERENCES workspaces(id),
    title VARCHAR NOT NULL,
    description TEXT,
    status VARCHAR DEFAULT 'pending',
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Agent System
CREATE TABLE agents (
    id INTEGER PRIMARY KEY,
    workspace_id INTEGER REFERENCES workspaces(id),
    name VARCHAR NOT NULL,
    provider VARCHAR NOT NULL,
    model VARCHAR NOT NULL,
    scope JSON NOT NULL,
    can_read BOOLEAN DEFAULT FALSE,
    can_write BOOLEAN DEFAULT FALSE,
    can_create BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT FALSE,
    can_execute_code BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP
);

CREATE TABLE agent_credentials (
    id INTEGER PRIMARY KEY,
    agent_id INTEGER REFERENCES agents(id),
    key VARCHAR NOT NULL,
    encrypted_value BLOB NOT NULL,
    created_at TIMESTAMP
);

CREATE TABLE agent_sessions (
    id INTEGER PRIMARY KEY,
    agent_id INTEGER REFERENCES agents(id),
    created_at TIMESTAMP,
    ended_at TIMESTAMP
);

CREATE TABLE agent_action_logs (
    id INTEGER PRIMARY KEY,
    session_id INTEGER REFERENCES agent_sessions(id),
    action_type VARCHAR NOT NULL,
    target VARCHAR,
    allowed BOOLEAN NOT NULL,
    execution_time_ms INTEGER,
    created_at TIMESTAMP
);

-- Plugin System
CREATE TABLE plugins (
    id INTEGER PRIMARY KEY,
    plugin_id VARCHAR UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    version VARCHAR NOT NULL,
    plugin_type VARCHAR NOT NULL,
    manifest JSON NOT NULL,
    created_at TIMESTAMP
);

CREATE TABLE plugin_configs (
    id INTEGER PRIMARY KEY,
    workspace_id INTEGER REFERENCES workspaces(id),
    plugin_id VARCHAR REFERENCES plugins(plugin_id),
    enabled BOOLEAN DEFAULT FALSE,
    config JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Notebook Database Schema

```sql
-- File Metadata
CREATE TABLE file_metadata (
    id INTEGER PRIMARY KEY,
    notebook_id INTEGER NOT NULL,
    path VARCHAR NOT NULL UNIQUE,
    filename VARCHAR NOT NULL,
    content_type VARCHAR NOT NULL,  -- MIME type
    size INTEGER NOT NULL,
    file_hash VARCHAR,  -- For change detection
    title VARCHAR,
    description TEXT,
    properties JSON,  -- Unified metadata from frontmatter/sidecars
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP
);

-- Tag System
CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    created_at TIMESTAMP
);

CREATE TABLE file_tags (
    id INTEGER PRIMARY KEY,
    file_id INTEGER REFERENCES file_metadata(id),
    tag_id INTEGER REFERENCES tags(id),
    created_at TIMESTAMP,
    UNIQUE(file_id, tag_id)
);

-- Full-Text Search
CREATE VIRTUAL TABLE search_index USING fts5(
    file_id,
    content,
    content='file_metadata',
    content_rowid='id'
);
```

### Migration Strategy

**Alembic Configuration:**
- Single `alembic.ini` with two sections: `[alembic:workspace]` and `[alembic:notebook]`
- Workspace migrations in `backend/codex/migrations/workspace/`
- Notebook migrations in `backend/codex/migrations/notebook/`
- Pre-Alembic database detection and stamping
- Automatic migration on startup and notebook creation

---

## Security Architecture

### Authentication & Authorization

**JWT Token Flow:**
```
1. User submits credentials → /api/v1/users/token
2. Backend validates password (PBKDF2)
3. Generate JWT with user ID, expiration
4. Return token in response + set HTTP-only cookie
5. Frontend includes token in Authorization header
6. Backend validates token on each request
7. User retrieved via dependency injection
```

**Password Security:**
- PBKDF2-HMAC-SHA256 with 100,000 iterations
- Random 32-byte salt per password
- Salt and hash stored together (hex-encoded)

**Session Management:**
- 30-minute token expiration (configurable)
- Token stored in HTTP-only cookie for CSRF protection
- Refresh token pattern not implemented (planned)

### Agent Security

**Scope Enforcement:**
- Every agent operation passes through `ScopeGuard`
- Permission checks: read, write, create, delete, execute
- Path traversal protection (blocks `..` in paths)
- Folder pattern matching (glob-style)
- File type restrictions (e.g., no executing `.exe` files)

**Credential Encryption:**
- Fernet symmetric encryption (128-bit AES)
- Encryption key derived from `SECRET_KEY` environment variable
- Credentials stored encrypted in database
- Decrypted only at execution time in memory
- Never returned in API responses (write-only)

**Action Logging:**
- Every agent action logged with:
  - Timestamp, session ID, user context
  - Action type and target resource
  - Permission decision (allowed/denied)
  - Execution time
- Immutable audit trail for security reviews

### Plugin Security

**Validation:**
- Plugin manifest schema validation
- Plugin ID and version format checks
- Plugin type restrictions (view, theme, integration)
- Per-workspace plugin enablement

**Isolation:**
- Plugins run in frontend sandbox (Vue component scope)
- No direct filesystem access
- API calls go through authenticated backend
- Integration plugins execute server-side with rate limiting

### API Security

**CORS:**
- Configurable allowed origins
- Credentials support for cookies
- Preflight request handling

**Input Validation:**
- Pydantic models for request/response schemas
- Type checking at runtime
- SQL injection prevention via ORM

**Rate Limiting:**
- Not currently implemented (planned)
- Agent-level rate limiting for LLM usage

---

## Integration Points

### External Integrations

**Plugin-Based:**
- GitHub: Fetch issue data, repository info
- Weather APIs: Location-based weather data
- OpenGraph: Fetch metadata from URLs

**Architecture:**
```
Frontend Request
    ↓
Backend Integration Executor
    ↓
HTTP Request to External API
    ↓
Response Parsing & Validation
    ↓
Storage in IntegrationArtifact table
    ↓
Return to Frontend
```

### WebSocket Integration

**Real-Time File Changes:**
- WebSocket endpoint: `/api/v1/ws`
- Connection manager broadcasts to all clients
- File watcher sends notifications on changes
- Frontend updates file tree reactively

**Message Format:**
```json
{
  "type": "file_change",
  "notebook_id": 1,
  "event": "modified",
  "file_path": "experiments/results.md",
  "file_id": 42
}
```

### Git Integration

**Automatic Versioning:**
- Git repository initialized per notebook
- Text files auto-committed on change
- Binary files excluded via `.gitignore`
- Commit messages generated from file operations
- Not exposed via API (filesystem-only)

---

## Deployment Architecture

### Development

```
┌──────────────────────────────────────────────────────────┐
│ Docker Compose (Development)                             │
│                                                          │
│  ┌────────────────┐      ┌──────────────────────────┐  │
│  │ Frontend       │      │ Backend                   │  │
│  │ - Vite Dev     │      │ - FastAPI                 │  │
│  │ - Port 5173    │◄────►│ - Uvicorn                 │  │
│  │ - Hot Reload   │      │ - Port 8000               │  │
│  └────────────────┘      │ - Auto Reload             │  │
│                          └──────────────────────────┬─┘  │
│                                                     │    │
│                          ┌──────────────────────────▼─┐  │
│                          │ Shared Volume             │  │
│                          │ - ./data (workspaces)     │  │
│                          │ - ./codex_system.db       │  │
│                          └────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

**Access:**
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Production

```
┌──────────────────────────────────────────────────────────┐
│ Docker Compose (Production)                              │
│                                                          │
│  ┌────────────────┐      ┌──────────────────────────┐  │
│  │ Nginx          │      │ Backend                   │  │
│  │ - Static SPA   │      │ - FastAPI                 │  │
│  │ - Port 80/443  │◄────►│ - Uvicorn                 │  │
│  │ - Proxy /api   │      │ - Port 8000               │  │
│  └────────────────┘      └──────────────────────────┬─┘  │
│                                                     │    │
│                          ┌──────────────────────────▼─┐  │
│                          │ Persistent Volume         │  │
│                          │ - /data (workspaces)      │  │
│                          │ - /data/codex_system.db   │  │
│                          └────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

**Features:**
- Multi-stage Docker builds (production images ~300MB)
- Health check endpoints for monitoring
- Volume persistence for data
- Environment variable configuration

### Scalability Considerations

**Current Limitations:**
- SQLite is single-writer (not suitable for high concurrency)
- File watchers run in single process (memory bound)
- No horizontal scaling without shared filesystem

**Potential Solutions (Not Implemented):**
- PostgreSQL for system database
- Redis for WebSocket message broker
- Celery for distributed file watching
- S3-compatible storage for file content

---

## Strengths

### 1. Clear Separation of Concerns
- Backend/frontend completely decoupled
- Business logic separated from data access
- Plugin architecture allows extensibility without core changes

### 2. Strong Type Safety
- TypeScript in frontend
- Pydantic/SQLModel in backend
- Shared type definitions between layers

### 3. Modern Python Practices
- Async/await throughout
- Type hints everywhere
- Dependency injection via FastAPI
- Context managers for resource management

### 4. Database Isolation
- Notebook databases are portable
- Corruption limited to single notebook
- Parallel access to different notebooks

### 5. Real-Time Synchronization
- File system changes immediately reflected in database
- WebSocket notifications to all clients
- Minimal polling, event-driven

### 6. Security by Design
- JWT authentication
- Strong password hashing (PBKDF2)
- Encrypted credentials
- Agent scope guards
- Action audit logging

### 7. Extensibility
- Plugin system for views, themes, integrations
- Agent system for AI assistance
- Dynamic view queries
- Metadata format flexibility

### 8. Developer Experience
- Comprehensive documentation
- Clear project structure
- Easy local development setup
- Docker for consistent environments
- Type safety catches bugs early

---

## Recommendations

### Immediate Improvements (Low Effort, High Impact)

#### 1. Add Rate Limiting
**Issue**: No protection against API abuse  
**Solution**: Implement rate limiting middleware
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/v1/files/")
@limiter.limit("100/minute")
async def list_files(...):
    ...
```

#### 2. Add Request ID Logging
**Issue**: Request ID added but not logged consistently  
**Solution**: Add request_id to all log statements
```python
logger.info(f"[{request_id_var.get()}] Processing file operation")
```

#### 3. Add API Versioning Strategy
**Issue**: All routes hardcoded to `/api/v1/`  
**Solution**: Document versioning strategy and deprecation policy
- Maintain v1 for 6 months after v2 release
- Add `X-API-Version` header to responses
- Provide migration guides for breaking changes

#### 4. Improve Error Responses
**Issue**: Inconsistent error message formats  
**Solution**: Standardize error responses
```python
class ErrorResponse(BaseModel):
    error: str
    detail: str
    request_id: str
    timestamp: datetime
```

#### 5. Add Health Check Details
**Issue**: Health check endpoint too simple  
**Solution**: Include component status
```python
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "database": await check_db_connection(),
        "watchers": len(get_active_watchers()),
        "websocket": connection_manager.active_connections > 0
    }
```

### Medium-Term Improvements (Moderate Effort)

#### 6. Add Caching Layer
**Issue**: Repeated database queries for same data  
**Solution**: Add Redis or in-memory cache
- Cache workspace/notebook metadata (5-minute TTL)
- Invalidate on writes
- Consider using `fastapi-cache2`

#### 7. Implement Refresh Tokens
**Issue**: Users need to re-login every 30 minutes  
**Solution**: Add refresh token flow
- Short-lived access tokens (15 minutes)
- Long-lived refresh tokens (7 days)
- Secure refresh token storage

#### 8. Add Background Task Processing
**Issue**: Long-running operations block API responses  
**Solution**: Use Celery or FastAPI background tasks
- File indexing operations
- Large file uploads
- Batch metadata updates
- Agent long-running tasks

#### 9. Improve File Upload Handling
**Issue**: Large file uploads can timeout  
**Solution**: 
- Streaming uploads with chunking
- Progress reporting via WebSocket
- Resumable uploads (TUS protocol)

#### 10. Add Metrics and Monitoring
**Issue**: No visibility into production performance  
**Solution**: Add Prometheus metrics
- Request latency histograms
- Error rates by endpoint
- Database query times
- WebSocket connection counts

### Long-Term Improvements (Significant Effort)

#### 11. Database Migration Path
**Issue**: SQLite limits horizontal scaling  
**Solution**: Support PostgreSQL for system database
- Keep SQLite as default for simplicity
- Add database adapter layer
- Test suite against both databases

#### 12. Distributed File Watching
**Issue**: Single-process file watchers don't scale  
**Solution**: Event-driven architecture
- Use message queue (RabbitMQ, Redis Streams)
- Multiple watcher workers
- Coordinator for watcher assignment

#### 13. Search Improvements
**Issue**: FTS5 full-text search is basic  
**Solution**: Add Elasticsearch or Meilisearch
- Better ranking and relevance
- Faceted search
- Typo tolerance
- Advanced query syntax

#### 14. Collaborative Editing
**Issue**: No real-time collaboration  
**Solution**: Implement operational transformation or CRDT
- Y.js for collaborative text editing
- Conflict-free merging
- Presence indicators

#### 15. Audit Log UI
**Issue**: Action logs not exposed in frontend  
**Solution**: Build audit log viewer
- Filter by user, agent, date, action type
- Export capabilities
- Anomaly detection

### Security Enhancements

#### 16. Add CSRF Protection
**Issue**: No CSRF tokens for state-changing operations  
**Solution**: Implement CSRF token validation
- Use `fastapi-csrf-protect`
- Double-submit cookie pattern

#### 17. Content Security Policy
**Issue**: No CSP headers  
**Solution**: Add strict CSP
```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-eval'; style-src 'self' 'unsafe-inline';";
```

#### 18. Secret Management
**Issue**: Secrets in environment variables  
**Solution**: Use dedicated secret manager
- Vault for production
- AWS Secrets Manager / GCP Secret Manager
- Rotate secrets automatically

#### 19. Add Multi-Factor Authentication
**Issue**: Single-factor authentication only  
**Solution**: Implement TOTP 2FA
- pyotp for TOTP generation
- QR code for setup
- Recovery codes

### Code Quality Improvements

#### 20. Increase Test Coverage
**Issue**: Test coverage likely incomplete  
**Current**: Basic integration tests exist  
**Solution**: 
- Aim for 80%+ coverage
- Add unit tests for business logic
- Integration tests for all API endpoints
- E2E tests for critical workflows

#### 21. Add API Documentation
**Issue**: OpenAPI docs but no usage guides  
**Solution**: 
- Add request/response examples to all endpoints
- Create Postman collection
- Write API usage tutorial

#### 22. Refactor Large Functions
**Issue**: Some functions exceed 100 lines  
**Solution**: Extract helper functions and classes
- Keep functions under 50 lines
- Single responsibility principle

---

## Future Considerations

### 1. Multi-Tenancy
- Support for organizations with multiple users
- Tenant isolation at database level
- Billing and usage tracking

### 2. Cloud Storage Integration
- S3-compatible backends for file storage
- Hybrid: Metadata in database, content in object storage
- Cost optimization for large notebooks

### 3. Advanced AI Features
- Automatic tagging and classification
- Similar document recommendations
- Summary generation
- Question-answering over notebook content

### 4. Mobile Application
- React Native or Flutter app
- Offline-first architecture
- Sync protocol for mobile

### 5. API for Third-Party Integrations
- Public API with OAuth2 client credentials
- Rate limiting per API key
- Developer portal

### 6. Advanced Analytics
- Usage statistics and dashboards
- Notebook activity heatmaps
- Tag co-occurrence analysis
- Citation graphs for linked documents

### 7. Version Control UI
- Git interface in frontend
- Visual diff for markdown
- Branch management
- Conflict resolution UI

---

## Conclusion

Codex demonstrates a solid architectural foundation with clear separation of concerns, strong type safety, and modern development practices. The two-database pattern is innovative and provides good scalability for the target use case. The plugin system and agent integration show forward-thinking design for extensibility.

**Key Strengths:**
- Clean architecture with proper layering
- Strong type safety (TypeScript + Pydantic)
- Real-time synchronization
- Security-conscious design
- Excellent developer experience

**Primary Areas for Improvement:**
- Rate limiting and API protection
- Error handling standardization
- Test coverage expansion
- Database migration path for scaling
- Monitoring and observability

**Recommended Next Steps:**
1. Implement rate limiting (immediate security win)
2. Standardize error responses (better API UX)
3. Add comprehensive monitoring (production visibility)
4. Expand test coverage (reduce regressions)
5. Document scaling strategy (future planning)

The architecture is well-suited for the current scale and should serve the project well as it grows. The recommended improvements are mostly incremental and can be prioritized based on user needs and scaling requirements.

---

**Document Metadata:**
- **Author**: Architecture Review Team
- **Version**: 1.0
- **Date**: 2026-02-16
- **Next Review**: 2026-08-16 (6 months)
