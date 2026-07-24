# Multi-User & Multi-Org Design

**Status**: Draft
**Version**: 0.1
**Date**: 2026-07-19

## Summary

Codex today is a single-user system wearing multi-user clothes. There is a `users` table, JWT auth,
personal access tokens, and even a `workspace_permissions` table — but every workspace query filters
on `owner_id == current_user.id`, so nothing is actually shareable. This document describes how to
get from there to real multi-user collaboration inside organizations, with comments, notifications,
and bots as first-class participants.

The central architectural decision: **for shared workspaces, S3 becomes the source of truth for
content, and the backend becomes the token authority.** The local filesystem (and the watcher built
on it) stays for personal workspaces, but demotes to a cache/working-copy for shared ones. Multiple
humans and bots on multiple machines cannot share a server's local disk; they can share a bucket.

## Goals

- Organizations with role-based membership; workspaces owned by an org or by an individual.
- Enforced sharing: workspace permissions actually gate every route, WebSocket, and search.
- Bots as first-class principals: they log in, get mentioned, comment, receive notifications, and
  show up in audit trails exactly like humans. Most collaborators will be Claude sessions, not
  browser tabs — the API surface is the primary UI for bots.
- Comments anchored to blocks, with threads, mentions, and resolve state.
- Notifications: in-app, email digest, and webhook (webhooks are how bots get woken up).
- S3-backed sync for shared workspaces, with the backend vending short-lived scoped credentials so
  clients and bots never hold long-lived AWS keys.

## Non-Goals (for now)

- Real-time co-editing / CRDTs. The UI is read-only display; writes come through the API or sync.
  Conflict handling is versioned last-writer-wins with conflict copies, not operational transforms.
- Self-serve billing, quotas, or a hosted multi-tenant SaaS control plane.
- Cross-org sharing (a workspace belongs to exactly one org or one user).

---

## 1. Where We Are: Limitations to Overcome

Each of these is grounded in current code; together they define the work.

| # | Limitation | Where it lives |
|---|-----------|----------------|
| L1 | Workspace access is owner-only; `WorkspacePermission` exists but is never checked | `api/routes/workspaces.py::get_workspace_by_slug` filters `Workspace.owner_id == current_user.id`; permissions table only read for listing/cleanup |
| L2 | WebSocket endpoint is completely unauthenticated | `api/routes/ws.py::notebook_websocket(websocket, notebook_id)` — no token, no permission check |
| L3 | Local filesystem is the source of truth; a single watcher process syncs disk → DB | `core/watcher.py`, lifespan in `main.py`. Assumes one machine, one writer |
| L4 | System DB is SQLite | Fine for one user; write contention and no row locking under concurrent org traffic |
| L5 | Per-notebook SQLite DBs live inside the notebook directory (`.codex/notebook.db`) | Can't be shared across machines; syncing a live SQLite file via S3 corrupts it |
| L6 | Git history is per-notebook with a process-local lock | `core/git_manager.py` + `git_lock_manager` — locks don't span processes or machines |
| L7 | S3 exists only as a binary offload, configured by server env vars, credentials held by the server only | `core/s3_storage.py`: single global bucket, `.s3ref` pointer files, presigned GETs |
| L8 | Agents are configs, not identities | `db/models/system.py::Agent` has scopes/capabilities/rate limits, but a bot has no `user_id`, can't own a comment, can't be mentioned, can't be granted workspace permission |
| L9 | No comments, no notifications, no event log | Nothing in models or routes |
| L10 | Slugs are unique per owner (`uq_workspaces_owner_slug`); URLs have no org segment | Slug collisions and ambiguous routing once workspaces are shared |
| L11 | `SECRET_KEY` defaults to a hardcoded string; JWTs live 30 min with no refresh; PATs have optional workspace/notebook scoping but coarse string scopes | `api/auth.py` |
| L12 | Plugin secrets and integration artifacts are per-workspace, implicitly per-owner | `PluginSecret`, `OAuthConnection` are user-scoped; shared workspaces need to decide whose Google token a calendar block uses |

Assets we already have and should build on rather than replace:

- **Stable block identity**: `Block.block_id` is a ULID stable across renames — the perfect anchor
  for comments.
- **ARQ + Redis worker** (`worker/`): the natural home for notification fanout, sync jobs, and bot
  task dispatch.
- **Task queue** (`Task` model + `/tasks/` routes): already how agent work is requested.
- **Agent scope guard and audit log** (`AgentSession`, `AgentActionLog`): keep as the *authorization
  and audit* layer for bots; bolt identity on top.
- **WebSocket broadcast** (`core/websocket.py`): keep the event shape, add auth and channel scoping.

---

## 2. Identity: Principals, Orgs, Membership

### 2.1 Principals — humans and bots in one table

Everything social (comments, mentions, notifications, permissions, audit) needs a single foreign key
for "who". Splitting humans and bots into separate tables doubles every join. So:

```python
class User(SQLModel, table=True):          # rename conceptually to "principal"; keep table name
    ...existing fields...
    kind: str = Field(default="human")     # "human" | "bot"
    display_name: str | None = None
    avatar_url: str | None = None
    bot_owner_org_id: int | None = Field(default=None, foreign_key="organizations.id")
```

- Bots have no password (`hashed_password` empty, login disabled); they authenticate exclusively
  with PATs (and later OIDC workload identity). `is_active` works unchanged for offboarding.
- The existing `Agent` model becomes the *brain config* attached to a bot principal:
  `Agent.principal_id: int = Field(foreign_key="users.id")`. A bot principal may have zero agents
  (a pure webhook bot, e.g. a Claude Code session driven from outside) or one (a hosted agent Codex
  runs itself via the existing engine).
- Everything that renders a user (comment author, audit row, mention chip) renders a bot the same
  way, with a badge.

**Why this matters**: "nobody wants to work outside of Claude" — concretely, most write traffic will
be a Claude session holding a PAT. That session should be indistinguishable from a teammate: it
appears in the member list, its comments thread normally, its permissions are granted and revoked
like anyone's, and its actions land in the same audit trail. No parallel "integration" system.

### 2.2 Organizations

```python
class Organization(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    slug: str = Field(unique=True, index=True)
    created_at / updated_at ...

class OrgMembership(SQLModel, table=True):
    org_id: int = Field(foreign_key="organizations.id", index=True)
    principal_id: int = Field(foreign_key="users.id", index=True)
    role: str = Field(default="member")   # "owner" | "admin" | "member" | "guest"
    # unique (org_id, principal_id)
```

- `Workspace` gains `org_id: int | None`. `NULL` = personal workspace (today's behavior, unchanged).
- Uniqueness moves to `uq_workspaces_org_slug` for org workspaces; personal keeps owner-scoped
  uniqueness. URLs become `/orgs/{org_slug}/workspaces/{ws_slug}/...`; existing personal routes stay.
- Bots are org members like anyone else, typically with role `member` and per-workspace grants.
  `guest` exists so an external human or bot can be added to one workspace without seeing the org.

### 2.3 Permission resolution

One resolver, used by every route, the WebSocket handshake, and search:

```
effective_level(principal, workspace):
    if workspace.owner_id == principal.id:            -> admin
    if workspace.org_id:
        role = org_role(principal, workspace.org_id)
        if role in ("owner", "admin"):                -> admin
        if role == "member":                          -> workspace default (configurable, default "read")
    grant = WorkspacePermission(workspace, principal) -> grant.permission_level
    else                                              -> none
```

Permission levels become `read < comment < write < admin` (adding `comment` to the existing
`read/write/admin` strings — a reviewer or triage bot can discuss without editing content).

This is **the L1 fix**: `get_workspace_by_slug` and `helpers.get_notebook_path_nested` stop
filtering by `owner_id` and instead resolve + assert a minimum level. For bots, the *identity*
grant (can this principal touch this workspace at all?) composes with the existing *agent scope
guard* (which paths/operations within it) — identity is coarse, scope is fine, audit logs both.

---

## 3. Sync: S3 as Source of Truth for Shared Workspaces

### 3.1 The problem

The watcher/filesystem model (L3) is the deepest single-user assumption. Two humans and a bot
editing one workspace means three working copies on three machines plus the server. A shared POSIX
filesystem is operationally miserable; a bucket is not. **Decision: multi-user workspaces require
S3 sync.** Personal workspaces keep the current local model untouched.

### 3.2 Layout and roles

```
s3://{bucket}/orgs/{org_id}/workspaces/{ws_id}/
    notebooks/{nb_id}/
        content/...            # the file tree, versioned (bucket versioning ON)
    manifest/                  # sync journal checkpoints (see 3.4)
```

- **S3 = canonical content.** Every object PUT/DELETE is the write of record.
- **Server working copy = cache + indexer.** The server maintains a materialized copy per shared
  notebook, applies remote changes to it, and reuses the existing watcher/metadata pipeline
  (`core/metadata.py`, block extraction, search indexing) unchanged on top of it. The per-notebook
  SQLite DB (L5) becomes a **derived index that is never synced** — each replica (server, future
  offline client) rebuilds/updates its own from S3 state. This sidesteps SQLite-over-S3 corruption
  entirely.
- **Clients (humans' local checkouts, bots' sandboxes)** sync directly against S3 with credentials
  from the token vendor (3.3), then notify the server (`POST .../sync/push-complete`) — or rely on
  bucket notifications where configured.

### 3.3 The backend as token authority

Clients never hold long-lived AWS keys; the backend does (as today, L7), and vends scoped,
short-lived credentials:

```
POST /api/v1/workspaces/{ws}/sync/credentials
  -> 403 unless effective_level >= read (write access requires >= write)
  -> STS AssumeRole with an inline session policy scoping to
     arn:aws:s3:::{bucket}/orgs/{org}/workspaces/{ws}/*
     (s3:GetObject[Version], ListBucket with prefix condition; + PutObject/DeleteObject iff write)
  -> { access_key_id, secret_access_key, session_token, expiration (~1h), bucket, prefix }
```

- Works identically for humans (session JWT) and bots (PAT). A bot's PAT that is
  workspace-scoped (already supported by `PersonalAccessToken.workspace_id`) can only vend
  credentials for that workspace.
- For S3-compatible stores without STS (MinIO supports it; some don't), fall back to
  presigned-URL batches: `POST .../sync/presign` with a list of keys/ops. Same authz, worse
  ergonomics, keep it as the compatibility path.
- Revocation = stop issuing; sessions die within the hour. Permission changes take effect on next
  refresh, which is acceptable for v1.

### 3.4 Change model and conflicts

- **Bucket versioning ON** — every version of every file is retained; this supersedes the local-git
  history role for shared notebooks (see 3.5).
- A `sync_journal` table in the system DB records every observed change
  (`ws_id, nb_id, path, s3_version_id, actor_principal_id, op, ts`) — populated from client
  push-complete calls and/or S3 event notifications (EventBridge → SQS → ARQ worker). This journal
  drives the WebSocket fanout, notifications, and client incremental pulls
  (`GET .../sync/changes?since=cursor`).
- **Conflicts**: compare-and-swap via `If-Match`-style semantics — client sends the base
  `s3_version_id` it last saw (recorded in journal); if HEAD shows a newer version, the write still
  lands (versioning keeps both) but the journal marks a conflict and the loser is surfaced as a
  conflict notification + a `name (conflict YYYY-MM-DD).md` copy. Deterministic, no locks, and both
  versions are always recoverable. CRDTs stay out of scope.

### 3.5 What happens to git (L6)

For shared notebooks, per-notebook git as the concurrency/history mechanism doesn't survive
multi-writer (the lock manager is process-local, and merging generated commits across replicas is
pain with no payoff). S3 versioning + the sync journal provide history and attribution. Keep git
for personal/local notebooks; for shared ones, either disable it or keep a single server-side
commit loop as an *export* (nice for `git log` archaeology), explicitly downstream of S3, never
authoritative. `Block.last_commit_hash` gains a sibling `s3_version_id` (already present) as the
primary version pointer.

---

## 4. Comments

Comments are social metadata, not content: they must not appear in the file tree, must survive file
renames, and must be queryable across notebooks. They live in the **system DB**, anchored to the
stable block ULID:

```python
class Comment(SQLModel, table=True):
    id: int | None
    workspace_id: int = FK(workspaces.id, index=True)
    notebook_id: int = FK(notebooks.id, index=True)
    block_id: str = Field(index=True)                # Block.block_id ULID; survives renames/moves
    thread_id: int | None = FK(comments.id)          # NULL = thread root
    author_id: int = FK(users.id)                    # human or bot, indistinguishable
    body: str                                        # markdown
    resolved_at: datetime | None
    resolved_by_id: int | None = FK(users.id)
    created_at / updated_at / deleted_at
```

- Routes: `GET/POST /workspaces/{ws}/notebooks/{nb}/blocks/{block_id}/comments`,
  `PATCH/DELETE /comments/{id}`, `POST /comments/{id}/resolve`. `comment` permission level gates
  writes; `read` gates reads.
- **Mentions**: parse `@handle` against workspace-visible principals at post time; store rows in a
  `CommentMention` link table (don't re-parse on read). Mentioning a bot is the primary
  human→bot invocation gesture: it emits a notification, and for bots with a configured agent it
  can auto-enqueue a `Task` (existing queue) with the comment as context — "@reviewbot take a look"
  just works, and the bot replies in-thread like a person.
- If a block is deleted, comments orphan gracefully (block_id no longer resolves; show thread in a
  workspace-level "orphaned discussions" view rather than cascading deletes).
- Frontend: HomeView/BlockView gets a per-block comment affordance and thread panel; this is the
  first genuinely interactive (non-read-only) UI surface, so it warrants its own small design pass.

## 5. Notifications

One event pipeline feeding three delivery channels:

```python
class Event(SQLModel, table=True):        # append-only outbox
    id, workspace_id, actor_id, kind, subject (JSON), created_at
    # kinds: comment.created, comment.mention, comment.resolved, permission.granted,
    #        sync.conflict, sync.batch (rolled-up file changes), task.completed, member.joined

class Notification(SQLModel, table=True): # per-recipient fanout
    id, event_id, recipient_id, read_at, emailed_at, delivered_webhook_at, created_at
```

- Routes write an `Event` in the same transaction as the action; an ARQ job fans out to
  `Notification` rows per recipient (mentioned principals, thread participants, workspace watchers
  — with a `WorkspaceWatch` opt-in/mute table).
- **In-app**: `GET /notifications` + unread badge; pushed live over the (now authenticated)
  WebSocket on a per-principal channel.
- **Email**: digest job batches unread notifications (per-user cadence setting). Needs an SMTP/SES
  config — first email dependency in the codebase; also unlocks real password-reset delivery (the
  `PasswordResetToken` machinery already exists).
- **Webhook — the bot channel**: a bot principal can register a webhook URL + secret; fanout POSTs
  signed event payloads. This is how an external Claude session gets woken: mention →
  webhook → session pulls context via API with its PAT → replies via comment API. For hosted
  agents, the same fanout enqueues the ARQ task directly instead of an HTTP hop.

## 6. WebSocket hardening (L2)

- Handshake requires a token (query param or first-message auth), resolves the principal, and only
  then subscribes; subscription requests are checked against `effective_level >= read`.
- Channels become `workspace:{id}` and `principal:{id}` (notifications) rather than bare
  `notebook_id`. The `FileChangeEvent` shape in `core/websocket.py` is kept and gains
  `actor_principal_id` so UIs can show "who just changed this".

---

## 7. Infrastructure changes

- **L4 — Postgres for the system DB.** Orgs, comments, events, notifications, and the sync journal
  are all hot multi-writer tables; SQLite's single-writer lock will be the first thing to fall over.
  SQLModel/SQLAlchemy makes this mostly an Alembic + config change; keep SQLite supported for
  single-user installs (the feature gate: shared workspaces and orgs require Postgres + S3 + Redis).
  Per-notebook SQLite stays (it's a derived, per-replica index — see 3.2).
- **L11 — auth hygiene.** Refuse to boot in multi-user mode with the default `SECRET_KEY`; add
  refresh tokens (30-min access tokens make PATs the de-facto auth, which is backwards for humans);
  formalize PAT scopes (`workspace:read`, `workspace:write`, `comments:write`, `sync:credentials`)
  now that tokens can act across trust boundaries.
- **L12 — shared-workspace integration identity.** A calendar block in a shared workspace must not
  silently use whichever member's `OAuthConnection` happens to exist. Rule: integrations bind to an
  explicit connection at the workspace level (`PluginConfig` gains `oauth_connection_id`), and the
  UI names whose connection powers a block. Bots may own OAuth connections too (service accounts).
- **Deployment shape**: API (N replicas, stateless once content is in S3) + ARQ workers + Redis +
  Postgres + S3. The watcher remains only for personal/local workspaces.

---

## 8. Phasing

Each phase ships alone and is useful alone.

1. **Enforced sharing (no new infra).** Permission resolver + `comment` level; wire
   `WorkspacePermission` into every route; WebSocket auth (L1, L2, L11 secret check). Personal
   workspaces, invited collaborators via the existing table. *Multi-user on one server.*
2. **Comments + notifications (in-app only).** Comment/Mention/Event/Notification models, ARQ
   fanout, principal WebSocket channel. Mentioning humans works end-to-end.
3. **Bots as principals.** `User.kind`, `Agent.principal_id`, bot PAT issuance, mention→Task
   enqueue for hosted agents, webhook delivery for external ones. *A Claude session becomes a
   teammate.*
4. **Orgs.** Organization/OrgMembership, `Workspace.org_id`, org routes/URLs, role-based defaults.
   Postgres becomes required for this phase.
5. **S3 sync.** Token vendor, sync journal, change feed, conflict copies, server working-copy
   indexer; shared workspaces flip source-of-truth to S3. *Multi-machine, many writers.*
6. **Email + polish.** Digests, orphaned-discussion view, git export loop, admin audit UI.

Phases 1–3 deliberately precede orgs and S3: enforced permissions, comments, and bot identity are
where the daily-use value is, and none of it depends on the storage migration.

## 9. Open Questions

- **Bucket topology**: one bucket with prefix isolation (assumed above) vs. bucket-per-org.
  Prefix + STS session policies is simpler and fine until a compliance requirement says otherwise.
- **Offline/local client for shared workspaces**: do humans get a local sync daemon (Dropbox-style)
  in v1, or is the web UI + bot API enough until demand appears?
- **Mention semantics for bots**: does every mention auto-enqueue a task, or only with an explicit
  verb ("@bot do X")? Leaning: auto-enqueue, let the bot triage — cheap with rate limits already on
  `Agent`.
- **Notebook-level permissions**: v1 grants at workspace level only. Is per-notebook sharing needed
  (the `PersonalAccessToken.notebook_id` scope hints at appetite)?
- **Realtime presence** (who's viewing this page): trivial over the authenticated WebSocket, but
  worth deciding whether it's wanted before building channel bookkeeping around it.
