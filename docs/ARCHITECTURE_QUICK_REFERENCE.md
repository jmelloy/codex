# Architecture Quick Reference

**Quick lookup guide for common architectural questions and patterns**

## 🏗️ System Structure

```
User → Workspace → Notebook → Files
  ↓       ↓          ↓         ↓
System  System    Per-Notebook  Filesystem
  DB      DB          DB        (watched)
```

## 📁 Database Pattern

**Two-Database Architecture:**

| Database | Location | Contains | When to Query |
|----------|----------|----------|---------------|
| **System** | `codex_system.db` | Users, workspaces, permissions, agents, plugins | Auth, workspace management, agent config |
| **Notebook** | `.codex/notebook.db` | File metadata, tags, search index | File operations, search, tags |

**Rule of Thumb:** 
- System DB = "Who has access to what"
- Notebook DB = "What files exist and their metadata"

## 🔐 Authentication Flow

```
1. POST /api/v1/users/token → Returns JWT
2. Frontend stores in memory + HTTP-only cookie
3. All requests: Authorization: Bearer <token>
4. Backend validates JWT → extracts user → checks permissions
```

**Important Files:**
- `backend/codex/api/auth.py` - Auth utilities
- `backend/codex/api/routes/users.py` - Login/register endpoints
- `frontend/src/stores/auth.ts` - Auth state management

## 📡 Real-Time File Sync

```
File Change → Watchdog → Queue (5s batch) → Parse Metadata → 
Update DB → Git Commit → WebSocket Broadcast → Frontend Update
```

**Important Files:**
- `backend/codex/core/watcher.py` - File watching logic
- `backend/codex/core/metadata.py` - Metadata parsing
- `backend/codex/core/websocket.py` - WebSocket manager

## 🔌 Plugin System

**Three Types:**

| Type | Location | Technology | Use Case |
|------|----------|------------|----------|
| **View** | Frontend | Vue.js component | Custom visualizations (Kanban, Gallery) |
| **Theme** | Frontend | CSS variables | Visual styling |
| **Integration** | Backend | Python function | External APIs (GitHub, Weather) |

**Plugin Flow:**
```
Develop → Build → Register (API) → Enable (workspace) → Use
```

**Important Files:**
- `backend/codex/plugins/registry.py` - Plugin registration
- `backend/codex/plugins/executor.py` - Integration execution
- `frontend/src/services/pluginRegistry.ts` - Frontend plugin loading

## 🤖 Agent System

**Agent Architecture:**
```
Request → Agent Engine → Scope Guard → Tool Router → 
LLM Provider → Response + Action Log
```

**Key Components:**

| Component | Purpose | File |
|-----------|---------|------|
| **Agent** | LLM configuration | `backend/codex/db/models/system.py` |
| **ScopeGuard** | Permission enforcement | `backend/codex/agents/scope.py` |
| **ToolRouter** | Tool selection | `backend/codex/agents/tools.py` |
| **LiteLLMProvider** | Multi-LLM support | `backend/codex/agents/provider.py` |
| **ActionLog** | Audit trail | `backend/codex/db/models/system.py` |

**Permissions:**
- `can_read` - Read files
- `can_write` - Modify files
- `can_create` - Create files
- `can_delete` - Delete files
- `can_execute_code` - Run code (not implemented)

## 🗄️ Database Schemas

### System Database (codex_system.db)

```sql
users              -- User accounts
workspaces         -- Workspace definitions
workspace_permissions  -- User-workspace mapping
notebooks          -- Notebook registry
tasks              -- Task queue
agents             -- Agent configurations
agent_credentials  -- Encrypted API keys
agent_sessions     -- Agent conversation sessions
agent_action_logs  -- Audit trail
plugins            -- Plugin registry
plugin_configs     -- Per-workspace plugin settings
```

### Notebook Database (.codex/notebook.db)

```sql
file_metadata      -- File tracking and metadata
tags               -- Tag definitions
file_tags          -- File-tag relationships (M:N)
search_index       -- FTS5 full-text search
```

## 🛣️ API Routes

**Pattern:** `/api/v1/<resource>/`

### Core Routes

| Route | Purpose | Auth Required |
|-------|---------|---------------|
| `POST /api/v1/users/token` | Login | No |
| `GET /api/v1/workspaces/` | List workspaces | Yes |
| `GET /api/v1/notebooks/` | List notebooks | Yes |
| `GET /api/v1/files/` | List files | Yes |
| `POST /api/v1/files/` | Create file | Yes |
| `GET /api/v1/search/` | Search files | Yes |
| `POST /api/v1/query` | Dynamic views | Yes |

### Nested Routes (RESTful)

```
/api/v1/workspaces/{workspace_id}/notebooks/
/api/v1/workspaces/{workspace_id}/notebooks/{notebook_id}/files/
/api/v1/workspaces/{workspace_id}/notebooks/{notebook_id}/search/
```

## 🔒 Security Checklist

✅ **Implemented:**
- JWT authentication (30-min expiration)
- PBKDF2 password hashing (100k iterations)
- Encrypted agent credentials (Fernet)
- Scope guards for agents
- Action audit logging
- Input validation (Pydantic)

⚠️ **Needs Improvement:**
- Rate limiting (not implemented)
- CSRF protection (not implemented)
- CSP headers (not implemented)
- Refresh tokens (not implemented)
- 2FA (not implemented)

## 📦 Key Dependencies

### Backend
- **FastAPI** 0.115+ - Web framework
- **SQLModel** - ORM (SQLAlchemy + Pydantic)
- **Alembic** - Database migrations
- **Watchdog** - File system monitoring
- **LiteLLM** - Multi-LLM provider
- **Cryptography** - Fernet encryption

### Frontend
- **Vue.js** 3.5+ - UI framework
- **Pinia** - State management
- **TypeScript** 5.7+ - Type safety
- **Vite** 6+ - Build tool
- **Axios** - HTTP client

## 🚀 Quick Start Commands

```bash
# Backend
cd backend
pip install -e ".[dev]"
python -m codex.main

# Frontend
cd frontend
npm install
npm run dev

# Docker
docker compose up -d

# Tests
pytest -v  # Backend
npm test -- --run  # Frontend

# Migrations
alembic -n workspace upgrade head  # System DB
# Notebook migrations run automatically
```

## 🐛 Common Issues

### Issue: "Database is locked"
**Cause:** SQLite single-writer limitation  
**Solution:** Reduce concurrent writes or migrate to PostgreSQL

### Issue: "File changes not detected"
**Cause:** Watcher not running or crashed  
**Solution:** Check logs, restart application

### Issue: "Agent permission denied"
**Cause:** Scope restrictions  
**Solution:** Check agent scope configuration in database

### Issue: "Plugin not loading"
**Cause:** Plugin not registered or not enabled  
**Solution:** Check plugins table and plugin_configs

## 📊 Performance Tips

1. **Database Queries**: Use indexes on frequently queried columns
2. **File Watching**: Keep notebook count <1000 per instance
3. **WebSocket**: Broadcast only necessary change events
4. **Frontend**: Use virtual scrolling for large file lists
5. **Search**: FTS5 performs well up to ~100k files per notebook

## 🔍 Debugging

### Enable Debug Logging

```bash
# Backend
export DEBUG=true
export LOG_LEVEL=DEBUG
export LOG_SQL=true  # Log SQL queries

# Frontend
# In browser console
localStorage.setItem('debug', '*')
```

### Common Log Locations

```
backend/codex/main.py          # Application startup
backend/codex/core/watcher.py  # File watching
backend/codex/agents/engine.py # Agent execution
frontend/src/stores/*.ts       # State changes
```

## 📚 Further Reading

- [ARCHITECTURE.md](ARCHITECTURE.md) - Full architecture documentation
- [ARCHITECTURE_DIAGRAMS.md](ARCHITECTURE_DIAGRAMS.md) - Visual diagrams
- [ARCHITECTURE_REVIEW_SUMMARY.md](ARCHITECTURE_REVIEW_SUMMARY.md) - Executive summary
- [design/plugin-system.md](design/plugin-system.md) - Plugin details
- [design/ai-agent-integration.md](design/ai-agent-integration.md) - Agent details
- [design/dynamic-views.md](design/dynamic-views.md) - View system details

## 🆘 Getting Help

1. Check relevant design document (see above)
2. Search codebase: `grep -r "pattern" backend/`
3. Check tests: `tests/test_*.py`
4. Review API docs: http://localhost:8000/docs
5. Check WebSocket messages in browser DevTools

---

**Last Updated**: 2026-02-16  
**Maintainer**: Architecture Team
