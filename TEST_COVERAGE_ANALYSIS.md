# Test Coverage Analysis

**Date:** 2026-02-22
**Backend coverage:** 55% (472 passed, 5 failed, 1 skipped)
**Frontend coverage:** 41% statement coverage (398 passed, 4 skipped)

---

## Executive Summary

The codebase has reasonable coverage on core utilities and models but significant gaps in API route handlers, the agent subsystem, and most frontend components. The backend's 55% overall coverage is dragged down by low-coverage route files (files.py at 22%, workspaces.py at 35%). The frontend's 41% is dominated by untested components — 39 source files have zero dedicated test files.

---

## Existing Test Failures

Five `test_image_watcher.py` tests are currently failing due to a `MultipleResultsFound` SQLAlchemy error. These should be fixed before adding new tests to ensure CI stays green.

---

## Backend Coverage Breakdown

### Well-Covered Areas (70%+)
| Module | Coverage | Notes |
|--------|----------|-------|
| `codex/db/models/` | 100% | All ORM models fully covered |
| `codex/api/schemas.py` | 100% | Pydantic schemas |
| `codex/agents/scope.py` | 100% | Scope guard logic |
| `codex/agents/crypto.py` | 100% | Encrypt/decrypt |
| `codex/core/property_validator.py` | 100% | Property validation |
| `codex/core/custom_blocks.py` | 96% | Block parsing |
| `codex/plugins/models.py` | 93% | Plugin models |
| `codex/api/routes/tokens.py` | 85% | PAT management |
| `codex/main.py` | 84% | App startup |
| `codex/plugins/loader.py` | 83% | Plugin loading |
| `codex/core/websocket.py` | 81% | WebSocket manager |
| `codex/plugins/opengraph_scraper.py` | 80% | OG scraping |

### Critical Gaps (below 50%)
| Module | Coverage | Untested Functionality |
|--------|----------|----------------------|
| `codex/api/routes/files.py` | **22%** | File upload, move/rename, template system, link resolution, git history, content serving |
| `codex/api/routes/integrations.py` | **34%** | Plugin registry listing, enable/disable, config CRUD, connection testing, endpoint execution with artifact caching |
| `codex/api/routes/workspaces.py` | **35%** | Workspace creation (slug, path validation), theme updates, plugin config CRUD, cascade deletion |
| `codex/api/routes/users.py` | **36%** | User registration, account deletion (cascade), theme update |
| `codex/api/routes/agents.py` | **37%** | Agent CRUD, credential encryption, session management, message sending/execution loop |
| `codex/core/link_resolver.py` | **38%** | Link resolution (relative/absolute paths, URL encoding, anchors) |
| `codex/core/google_calendar.py` | **40%** | Calendar event listing, OAuth token refresh |
| `codex/core/oauth.py` | **37%** | OAuth flow (Google), token exchange, refresh logic |
| `codex/api/routes/snippets.py` | **41%** | Snippet creation, filename generation, workspace resolution |
| `codex/api/routes/tasks.py` | **42%** | Task CRUD (list, get, create, update) |
| `codex/api/routes/query.py` | **42%** | Advanced query execution, filtering, sorting |
| `codex/api/routes/notebooks.py` | **47%** | Notebook creation, deletion, plugin config, indexing status |
| `codex/agents/engine.py` | **19%** | Main agent execution loop, system prompt generation |
| `codex/core/logging.py` | **0%** | All formatters and logging config |
| `codex/db/migrations.py` | **0%** | Migration runner |
| `codex/scripts/` | **0%** | All CLI scripts |

---

## Frontend Coverage Breakdown

### Well-Covered Areas (80%+)
| Module | Coverage | Notes |
|--------|----------|-------|
| `services/auth.ts` | 100% | Auth service |
| `services/queryService.ts` | 100% | Query building |
| `services/viewParser.ts` | 97% | View YAML parsing |
| `services/viewPathResolver.ts` | 97% | View path resolution |
| `services/codex.ts` | 93% | Main API service |
| `services/pluginDevLoader.ts` | 90% | Dev plugin loading |
| `utils/contentType.ts` | 100% | Content type utils |
| `utils/validation.ts` | 100% | Validation utils |
| `utils/toast.ts` | 100% | Toast utils |
| `utils/fileTree.ts` | 98% | File tree builder |
| `stores/integration.ts` | 100% | Integration store |
| `stores/theme.ts` | 89% | Theme store |
| `stores/auth.ts` | 89% | Auth store |

### Critical Gaps (below 50%)
| Module | Coverage | Untested Functionality |
|--------|----------|----------------------|
| `services/integration.ts` | **0%** | All 8 integration API functions |
| `services/agent.ts` | **3%** | All 13 agent API methods |
| `services/oauth.ts` | **8%** | OAuth URL generation, callback handling |
| `services/pluginRegistry.ts` | **10%** | Plugin discovery, registration, caching |
| `services/viewPluginService.ts` | **22%** | View initialization, loading, fallbacks |
| `services/api.ts` | **27%** | Axios interceptors, base config |
| `services/pluginLoader.ts` | **36%** | Manifest parsing, CSS loading, dynamic imports |
| `stores/agent.ts` | **10%** | All agent state management, session handling |
| `utils/date.ts` | **55%** | Relative date formatting |
| `services/websocket.ts` | **59%** | Reconnection, keep-alive, error handling |

### 39 Source Files With Zero Test Files
- **3 Views:** CalendarView, MarkdownView, OAuthCallbackView
- **13 Components:** CodeViewer, CreateViewModal, CustomPropertiesEditor, FileHeader, FileTreeItem, FolderPropertiesPanel, FolderView, GoogleAuthButton, MarkdownLiveEditor, SettingsDialog, TagsEditor, TemplateSelector, ThemeSwitcher
- **5 Agent Components:** AgentActionCard, AgentActivityLog, AgentChat, AgentConfig, AgentScopeEditor
- **5 Settings Components:** AgentsPanel, IntegrationsPanel, NotebookSettingsPanel, UserSettingsPanel, WorkspaceSettingsPanel
- **10 Services:** agent, calendar, integration, oauth, pluginRegistry, pluginLoader, plugins, viewPluginService, websocket, pluginDevLoader
- **1 Store:** agent
- **1 Composable:** useProperties
- **1 Router:** index

---

## Recommended Priorities

### Priority 1 — Fix Existing Failures
- **Fix 5 failing `test_image_watcher.py` tests** — `MultipleResultsFound` SQLAlchemy error indicates a data isolation issue in the test fixtures

### Priority 2 — High-Value, Low-Effort Backend Tests
These are straightforward CRUD routes with no complex dependencies:

1. **`api/routes/tasks.py`** (42% → ~90%) — 4 simple CRUD endpoints, easy to test with existing conftest fixtures
2. **`api/routes/users.py`** (36% → ~85%) — Registration, deletion cascade, theme update; uses existing auth fixtures
3. **`core/logging.py`** (0% → ~90%) — Pure formatting logic, no dependencies. Create LogRecord mocks and assert output strings
4. **`core/link_resolver.py`** (38% → ~90%) — Pure path computation. Parametrized unit tests with various path inputs

### Priority 3 — High-Value Backend Integration Tests
These require database and filesystem setup but cover core functionality:

5. **`api/routes/files.py`** (22% → ~60%) — Focus on: file upload, move/rename, content serving. The template and git-history endpoints can follow later
6. **`api/routes/notebooks.py`** (47% → ~75%) — Notebook creation/deletion including watcher lifecycle
7. **`api/routes/workspaces.py`** (35% → ~65%) — Workspace creation with slug generation, workspace deletion cascade
8. **`api/routes/snippets.py`** (41% → ~75%) — Snippet creation with frontmatter generation and filename collision handling
9. **`core/metadata.py`** (58% → ~80%) — Sidecar parsing (JSON/XML/markdown), image metadata extraction

### Priority 4 — High-Value, Low-Effort Frontend Tests
Pure API wrapper services that only need `apiClient` mocking:

10. **`services/agent.ts`** (3% → ~95%) — Mock apiClient, verify all 13 API methods call correct URLs/methods
11. **`services/integration.ts`** (0% → ~95%) — Mock apiClient, verify all 8 functions
12. **`services/oauth.ts`** (8% → ~90%) — Mock apiClient, test URL generation and callback handling
13. **`stores/agent.ts`** (10% → ~70%) — Mock agent service, test state transitions and error handling
14. **`utils/date.ts`** (55% → ~95%) — Pure function, parametrized tests for relative date formatting

### Priority 5 — Medium-Effort Frontend Tests

15. **`services/pluginRegistry.ts`** (10% → ~70%) — Test dev/prod loading paths, registration deduplication
16. **`services/websocket.ts`** (59% → ~80%) — Fake timers for reconnection logic, mock WebSocket API
17. **`composables/useProperties.ts`** (48% → ~80%) — Test property editing state management
18. **`router/index.ts`** — Test route definitions, navigation guards, auth redirect logic

### Priority 6 — Component Tests (Higher Effort)
Start with simpler, reusable components before tackling full-page views:

19. **ThemeSwitcher.vue** — Small, isolated component; test theme selection emits
20. **TagsEditor.vue** — Test add/remove tag interactions
21. **TemplateSelector.vue** — Test template list rendering and selection
22. **FileTreeItem.vue** — Test expand/collapse, click events, context menu
23. **SettingsDialog.vue** — Test tab switching, panel rendering
24. **AgentChat.vue** — Test message sending, session lifecycle display

### Priority 7 — Hard Backend Tests

25. **`agents/engine.py`** (19%) — Mock LLM provider and tool router, test execution loop iterations, tool call handling, message serialization
26. **`api/routes/integrations.py`** (34%) — Test endpoint execution, artifact caching, connection testing with mocked plugins
27. **`api/routes/query.py`** (42%) — Test query building, filtering, sorting with various operator combinations

---

## Coverage Targets

| Area | Current | Suggested Target |
|------|---------|-----------------|
| Backend overall | 55% | 70% |
| Backend API routes | ~40% avg | 65% |
| Backend core | ~55% avg | 80% |
| Frontend overall | 41% | 55% |
| Frontend services | ~50% avg | 75% |
| Frontend stores | ~61% avg | 75% |
| Frontend utils | 93% | 95% |
| Frontend components | ~29% avg | 45% |
