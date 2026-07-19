# Codex as a Native Mac App — Design Document

**Author:** Claude
**Date:** 2026-07-19
**Status:** 🚧 Proposed (Draft)
**Reviewers:** TBD

## Overview

This document describes how Codex — currently a Dockerized FastAPI + Vue web application — would work as a first-class macOS application. The goal is a local-first journal that launches from the Dock, stores notebooks as ordinary folders the user can see in Finder, works fully offline, and integrates with macOS system services (Spotlight, Quick Look, Share sheet, notifications), while optionally syncing with a remote Codex server.

## Background

Codex's existing architecture is unusually well-suited to becoming a desktop app:

- **Content is already files.** Notebooks are directories of Markdown/`.cdx`/asset files; metadata lives in a per-notebook SQLite database at `.codex/notebook.db`. There is no proprietary blob store to migrate — a notebook *is* a folder.
- **SQLite everywhere.** Both the system database (`codex_system.db`) and notebook databases are SQLite with Alembic migrations. SQLite is native to macOS; no database server is required.
- **The watcher already uses FSEvents.** `backend/codex/core/watcher.py` uses `watchdog`, which uses FSEvents on macOS. The sync-files-to-index model translates directly.
- **The server is optional in spirit.** FastAPI serves a JSON API plus the built frontend as static files. The API surface (`/api/v1/`) is a clean seam between UI and engine.

The pieces that assume a server environment and need rethinking:

- **Auth**: JWT login, user registration, password reset — unnecessary friction for a single-user local app.
- **ARQ/Redis worker** (`backend/codex/worker/`): background jobs assume a Redis broker.
- **Docker/Kubernetes deployment**: irrelevant locally.
- **S3 storage** (`core/s3_storage.py`): optional today, stays optional.

## Goals

1. **Local-first**: full functionality with no network — create, browse, search, and organize notebooks stored on the local disk.
2. **Files stay visible**: notebooks live in user-chosen locations (e.g. `~/Documents/Codex/`); editing files with any external editor is reflected in the app, as the watcher does today.
3. **Native mac citizenship**: Dock icon, menu bar, keyboard shortcuts, Spotlight search of notebook content, Quick Look previews, drag-and-drop import, `codex://` deep links, system notifications for task/agent completion.
4. **Zero-setup**: no Docker, no Python install, no login screen. Download, open, use.
5. **Reuse, don't rewrite**: keep the Python engine and Vue UI; the Mac app is a new shell, not a new product.
6. **Optional server sync**: the app can attach to a remote Codex server for shared workspaces (the current web deployment remains supported).

## Non-Goals

1. A ground-up SwiftUI rewrite of the UI (considered and rejected below).
2. iOS/iPadOS companion app (future work; this design keeps the door open).
3. Real-time multi-user collaboration on a single notebook.
4. Mac App Store distribution in v1 (sandbox constraints conflict with the embedded server; see Distribution).

---

## Architecture Choice

Three options were considered:

| | A. Electron + embedded backend | B. Tauri/Swift-WebView + embedded backend | C. Native SwiftUI rewrite |
|---|---|---|---|
| UI reuse | Full (Vue SPA as-is) | Full (Vue SPA as-is) | None — rewrite everything |
| Engine reuse | Full (Python sidecar) | Full (Python sidecar) | Partial — reimplement watcher, metadata, migrations in Swift |
| App size | ~150 MB+ (Chromium) | ~15–40 MB + Python runtime | Smallest |
| Mac-native feel | Weak | Good (native menus, WKWebView) | Best |
| Team cost | Low | Low–Medium | Very high |
| Risk | Low | Low–Medium | High |

**Recommendation: Option B — a thin native shell (Tauri v2, or a small Swift/AppKit app hosting WKWebView) around the existing Vue frontend, with the Python backend embedded as a bundled sidecar process.** Tauri is preferred over a hand-rolled Swift shell because it ships the sidecar-process, auto-update, deep-link, tray/menu-bar, and notification plumbing out of the box, while still using the system WebView (WKWebView) so the app feels and sizes like a Mac app rather than a bundled browser.

Option C is rejected for v1: the block tree, MarkdownViewer custom blocks, dynamic views (`.cdx`), plugin-loaded Vue components, and themes represent years of UI surface that would all need Swift equivalents — and the plugin system's frontend contract is "a compiled Vue component," which a native UI cannot load.

### High-Level Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                       Codex.app bundle                          │
│                                                                 │
│  ┌───────────────────────────┐   ┌──────────────────────────┐   │
│  │  Native shell (Tauri)     │   │  Embedded engine          │   │
│  │  - WKWebView → Vue SPA    │   │  (Python sidecar)         │   │
│  │  - Menu bar / Dock menu   │   │  - FastAPI on             │   │
│  │  - Global hotkey capture  │◄─►│    127.0.0.1:<random>     │   │
│  │  - codex:// deep links    │   │  - FSEvents watcher       │   │
│  │  - Notifications          │   │  - In-process job queue   │   │
│  │  - Sparkle auto-update    │   │    (replaces ARQ/Redis)   │   │
│  │  - Spotlight/QuickLook    │   │  - Plugin executor        │   │
│  │    extensions             │   │  - Agent engine           │   │
│  └───────────────────────────┘   └──────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
                │                              │
                ▼                              ▼
   macOS services (Spotlight,      ~/Library/Application Support/Codex/
   Keychain, Notification Center)    codex_system.db, logs, plugin cache
                                   ~/Documents/Codex/<notebook>/
                                     content files + .codex/notebook.db
```

The Vue SPA is served by the embedded engine exactly as in the production Docker image today (static files from the backend), so frontend/backend versions can never skew.

---

## The Embedded Engine

### Packaging the Python backend

Bundle CPython 3.12+ and the `codex` package into the app using **PyInstaller** (or Briefcase) producing a single `codex-engine` binary inside `Codex.app/Contents/Resources/`. The shell spawns it on launch with:

- A random localhost port, passed back to the shell via stdout handshake (avoids port conflicts with a user's dev servers — including a Docker Codex on 8765).
- A per-launch bearer token shared between shell and engine, sent as a header by the WebView. This prevents other local processes from driving the user's engine — important because the engine has filesystem write access and agent credentials.
- `CODEX_MODE=desktop` to activate the desktop configuration profile described below.

The engine binary must be signed and notarized along with the app (hardened runtime with the `com.apple.security.cs.allow-unsigned-executable-memory` entitlement if needed by any wheel; audit native wheels — `watchdog`, `pydantic-core`, SQLite extensions — for signing).

### Desktop configuration profile (`CODEX_MODE=desktop`)

| Server behavior | Desktop behavior |
|---|---|
| JWT login, registration, password reset | **Single implicit local user**, auto-created on first launch. Auth middleware short-circuits to this user; login/register/reset routes and views are disabled. Personal access tokens remain for CLI/agent access. |
| ARQ + Redis background worker | **In-process asyncio task queue.** The worker functions in `codex/worker/` are already async; a thin `LocalQueue` adapter satisfies the same enqueue interface `main.py` uses, so `app.state.arq_pool` is swapped without touching call sites. Redis is never bundled. |
| Plugin secrets / agent credentials in DB | Stored via **macOS Keychain** (through a small `security`-CLI or `keyring` adapter) with DB fallback for portability. |
| Data under `/data` volume | System DB, logs, plugin cache under `~/Library/Application Support/Codex/`. Notebooks under user-chosen folders (default `~/Documents/Codex/`). |
| CORS open to frontend origin | CORS disabled; only same-origin WebView + token-bearing requests accepted, bound to `127.0.0.1`. |
| S3 storage optional | Unchanged (off by default). |

### File watching

`NotebookWatcher` already registers one watchdog Observer per notebook and syncs changes into `.codex/notebook.db` — this is the mechanism that makes "edit in any app, see it in Codex" work, and it carries over unchanged. Two Mac-specific notes:

1. **FSEvents observer accumulation**: the test-suite note in CLAUDE.md (accumulated FSEvents observers segfault) hints at fragility. The desktop app runs for weeks at a time, so watchers must be provably torn down when a notebook is closed/removed; add a lifecycle test that opens/closes 100 notebooks under FSEvents.
2. **iCloud Drive / Desktop & Documents sync**: files in iCloud-managed folders may be dataless (evicted) placeholders. The watcher and indexer must treat `NSFileProviderIdentifier`-style placeholder files as "present but not readable yet" rather than deleting index entries, and must not force-download entire notebooks just to index them. v1: detect iCloud placeholder files (`.icloud` naming / zero-size + extended attributes) and index lazily on materialization.

### WebSockets

The frontend's WebSocket channel (`api/routes/ws.py`, `core/websocket.py`) works unchanged against `ws://127.0.0.1:<port>` and remains the push path for watcher-driven UI refresh and agent/task progress — no polling needed in the shell.

---

## macOS Integration Features

These are the reasons to build a Mac app at all, in priority order.

### P0 — launch blockers

1. **App lifecycle**: engine starts with the app, stops on quit; crash of either side is detected and the engine restarted (shell supervises the sidecar). Closing the window keeps the app (and watchers, and scheduled agent tasks) running in the background — standard Mac document-app behavior.
2. **Native menus & shortcuts**: File/Edit/View/Window menus mapped to SPA routes and actions (⌘N new note, ⌘⇧F workspace search, ⌘, settings). The Vue app exposes a small `window.codexShell` command bus the shell invokes.
3. **Open/import via Finder**: register the app as a handler for `.md` and `.cdx` and for notebook folders; drag a folder onto the Dock icon to register it as a notebook (the "notebook registration" flow that exists in the API today).
4. **`codex://` URL scheme**: `codex://workspace/<ws>/notebook/<nb>/block/<id>` deep links for use in other apps, agents, and notifications. This also becomes the target of Spotlight results.
5. **Signed, notarized DMG with Sparkle auto-update.**

### P1 — the mac-native payoff

6. **Spotlight (Core Spotlight)**: a shell-side indexer mirrors the notebook search index into `CSSearchableItem`s (title, tags, snippet, `codex://` URL). Codex already maintains `SearchIndex` per notebook; the shell subscribes to index-change events over the WebSocket channel and upserts into Spotlight. Full-text stays in Codex; Spotlight gets titles/tags/summaries to keep the system index lean.
7. **Quick Look extension** for `.cdx` files: render frontmatter + Markdown body statically (no query execution) so pressing Space in Finder shows something meaningful.
8. **Menu-bar quick capture**: global hotkey opens a small always-on-top capture window (title + Markdown body + target notebook picker) that POSTs to the blocks API. This is the single highest-leverage feature for a journal app — capture without context-switching.
9. **Notifications**: task completion, agent run finished/needs-confirmation, calendar events (`google_calendar.py` integration) surfaced via `UNUserNotificationCenter`, with actions deep-linking back into the app.
10. **Share extension**: "Share → Codex" from Safari/Finder creates a block with the shared URL/file; pairs with the existing OpenGraph plugin for link unfurling.

### P2 — later

11. **Services menu** ("New Codex Note from Selection"), **Shortcuts.app actions** (create note, run search, run agent task — thin wrappers over the local API secured by a PAT), **stage-manager/multi-window** (one window per workspace), **printing/PDF export** of the rendered block view.

---

## Sync with a Remote Server

Local-first does not mean local-only. Three mechanisms, all opt-in:

1. **Remote workspace attach (v1)**: the app can add a remote Codex server as an additional workspace source — the SPA simply points those workspaces' API calls at the remote base URL with a stored PAT (Keychain). Local and remote workspaces coexist in the sidebar. No offline editing of remote workspaces in v1; they behave like the web app does today.
2. **Git-based notebook sync for text (v1.x)**: `core/git_manager.py` and `git_lock_manager.py` already exist. Because a notebook is a folder of files plus a rebuildable SQLite index, the *text* content of a notebook syncs cleanly as a git repo with `.codex/` gitignored — each machine rebuilds its own index. The app adds UI for "publish notebook to git remote" and background pull/push with conflict surfacing (conflicted files flagged in the block tree, resolved in an external editor).

3. **S3 pointer sync for binaries (v1.x, required alongside git sync)**: git alone does **not** carry images or other binaries — `GitManager` writes a `.gitignore` excluding them and its `commit()` filters binary files out of the index. The existing answer is `core/s3_storage.py`: binaries upload to a versioned S3-compatible bucket (AWS, MinIO, R2 via `CODEX_S3_ENDPOINT_URL`), and a small `.s3ref` JSON pointer (bucket, key, version_id, sha256) is kept on disk and *always* committed, so git history records every binary version without the bytes — effectively a built-in git-LFS. The watcher already performs the upload-and-pointer flow when S3 is configured, falling back to local-only storage when it isn't.

   Desktop implications:
   - **Multi-machine sync therefore has two legs**: git remote for text + pointers, S3 bucket for binary bytes. The "publish notebook" UI must configure both together and refuse to advertise a notebook as synced if S3 is unconfigured — otherwise every image would silently stay on one machine.
   - The app stores S3 credentials in the **Keychain** and lets the user point at any S3-compatible endpoint (a self-hosted MinIO next to a self-hosted Codex server is the natural pairing).
   - On a machine pulling a notebook, the app materializes binaries lazily: a `.s3ref` without its sibling file renders via presigned URL (already supported by the blocks API) and downloads on demand, keeping clones small.
   - Single-machine local-only use needs none of this; binaries just live on disk as today.

Explicitly rejected for now: CRDT/operational-transform sync, and committing binaries directly to git or git-LFS (the `.s3ref` mechanism already exists and supports lazy fetch + versioned storage). The unit of storage is a file; git-level conflict handling is acceptable for a single-author journal and is enormously cheaper.

---

## Distribution

- **Channel**: Developer-ID signed + notarized DMG, Sparkle 2 for updates. Homebrew cask as a secondary channel.
- **App Store**: deferred. The App Sandbox is hostile to (a) spawning a long-lived Python sidecar, (b) watching arbitrary user-chosen folders without per-launch security-scoped bookmark ceremony, and (c) Sparkle. Revisit only if there's demand; would require adopting security-scoped bookmarks for notebook roots regardless of sandboxing, which is worth doing anyway for future-proofing.
- **Updates & migrations**: app update may carry Alembic migrations for both DB families. On first launch after update, the engine runs `alembic upgrade head` for the system DB and lazily migrates each notebook DB on open (already the pattern for per-notebook DBs). Never auto-migrate a notebook that a *newer* app version has touched — refuse with a clear error instead (protects shared/git-synced notebooks from silent downgrade corruption).

## Phasing

| Phase | Scope | Exit criteria |
|---|---|---|
| **1. Engine-in-a-box** | PyInstaller build of backend, `CODEX_MODE=desktop` (implicit user, LocalQueue, App Support paths), Tauri shell loading the SPA, sidecar supervision, signed DMG | Fresh Mac: download DMG → create notebook → edit a file in VS Code → change appears in app. No Docker, no login. |
| **2. Mac citizenship** | Menus/shortcuts, file associations, `codex://`, quick capture, notifications, Sparkle | Daily-drivable as primary journal |
| **3. System search & share** | Spotlight indexing, Quick Look, Share extension, Keychain-backed secrets | Notebook content findable from Spotlight |
| **4. Sync** | Remote workspace attach; git + S3 notebook sync UI (text via git remote, binaries via `.s3ref` pointers) | Same notebook — including images — usable on two Macs |

## Risks

1. **PyInstaller + notarization friction** (native wheels, hardened runtime). Mitigation: build the packaging pipeline in Phase 1 week 1; it gates everything.
2. **FSEvents watcher longevity** — long-running observer leaks/segfaults (already hinted at in tests). Mitigation: watcher lifecycle soak test in CI on a macOS runner.
3. **iCloud Drive dataless files** breaking indexing or, worse, the watcher interpreting eviction as deletion. Mitigation: placeholder detection before any destructive index update; default notebook location outside iCloud with an explicit opt-in.
4. **Engine startup latency** (Python cold start + migrations) making the app feel slow. Mitigation: shell shows the window immediately with a lightweight loading state; keep engine resident in background after window close.
5. **Two runtimes forever** (Python + WebView) — carries ongoing size/complexity cost. Accepted consciously; revisit a native engine only if an iOS app forces the question.

## Open Questions

1. Do agents run while the app is "closed" (background) by default, or only while a window is open? (Proposal: background, with a menu-bar indicator, but off until Phase 2.)
2. Should the desktop app expose its local API on a fixed port for power users' scripts, or PAT-over-random-port only?
3. Minimum macOS version — 13 (Ventura) covers WKWebView features needed by the SPA and Tauri v2; confirm against the frontend's browserslist.

## References

- [Plugin System](./plugin-system.md) — frontend plugin contract (compiled Vue components) that constrains the shell choice
- [AI Agent Integration](./ai-agent-integration.md) — agent engine that must run inside the sidecar
- [Dynamic Views](./dynamic-views.md) — `.cdx` format relevant to Quick Look
- `backend/codex/core/watcher.py` — FSEvents-backed notebook sync
- `backend/codex/core/git_manager.py` — basis for git notebook sync
