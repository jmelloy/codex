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
5. **Keep the UI, port the engine**: the Vue SPA ships as-is inside a native shell; the ~14K-line Python engine is ported to Rust and runs in-process (rationale below). The product is unchanged.
6. **Optional server sync**: the app can attach to a remote Codex server for shared workspaces (the current web deployment remains supported).

## Non-Goals

1. A ground-up SwiftUI rewrite of the UI (considered and rejected below).
2. iOS/iPadOS companion app (future work; this design keeps the door open).
3. Real-time multi-user collaboration on a single notebook.
4. Mac App Store distribution in v1 (sandbox constraints conflict with the embedded server; see Distribution).

---

## Architecture Choice

Two decisions, more independent than the first draft treated them: what renders the **UI** (the shell) and what runs the **engine**.

### Shell: Tauri v2 hosting the existing Vue SPA

| | Electron | Tauri v2 (WKWebView) | Native SwiftUI rewrite |
|---|---|---|---|
| UI reuse | Full (Vue SPA as-is) | Full (Vue SPA as-is) | None — rewrite everything |
| App size | ~150 MB+ (Chromium) | ~15–40 MB | Smallest |
| Mac-native feel | Weak | Good (native menus, system WebView) | Best |
| Team cost | Low | Low | Very high |

**Recommendation: Tauri v2.** It ships auto-update, deep-link, tray/menu-bar, and notification plumbing out of the box, uses the system WKWebView so the app feels and sizes like a Mac app rather than a bundled browser, and — decisive for the engine choice below — the host process is Rust, so an engine written in Rust needs no separate process at all.

A native rewrite of the *UI* is rejected for v1 on surface breadth: the block/page tree, MarkdownViewer's fenced custom blocks (api, database, weather, GitHub, link-preview), the agent chat UI, settings, and themes would all need Swift equivalents before reaching parity, for no v1 user benefit.

One earlier argument against a native UI has weakened, and it's worth recording: the plugin system has been pared back to **CSS themes + backend integration proxies**. There is no third-party frontend-component ecosystem to host — every custom block component is compiled into the SPA bundle (`frontend/src/components/blocks/`), and the runtime "load compiled Vue component from `/api/v1/plugins/assets/`" path in `pluginLoader.ts` is vestigial: no build script produces `plugins.json`, the manifest endpoint returns an empty plugin list, and the `.vue` sources still sitting in `backend/plugins/*/components/` are never compiled or served. So the set of block types is closed and small, which means a native client (macOS or iOS) is *feasible* in a way it wasn't when plugins could ship arbitrary Vue components — it's rejected for v1 purely on cost, not possibility. This materially improves the story for a future iOS companion app.

### Engine: port to Rust, in-process (revised from Python sidecar)

The first draft embedded the Python backend as a PyInstaller sidecar process. Two things changed the recommendation: sidecar suspicion is well-founded (see below), and the engine is small enough to port — measured, not guessed:

| Component | LOC | Rust replacement |
|---|---|---|
| Blocks core + routes (`core/blocks.py`, `routes/blocks.py`) | ~2,650 | serde_yaml frontmatter + std fs; the logic is YAML + file ops, no framework magic |
| Watcher (`core/watcher.py`) | ~1,360 | `notify` crate (FSEvents-backed, like watchdog) |
| Other API routes (workspaces, notebooks, search, tasks…) | ~4,900 | axum handlers or Tauri commands |
| Plugin registry/executor (integration proxies) | ~1,230 | `reqwest` proxy |
| Agents (engine, provider, scope, tools) | ~915 | direct Anthropic/OpenAI HTTP calls (drops LiteLLM) |
| Metadata, md-import, link resolver, custom blocks | ~1,020 | serde_yaml, pulldown-cmark |
| Git (`git_manager`, `git_lock_manager`) | ~465 | `git2` (libgit2 bindings, first-class) |
| Vectorizer (`core/vectorizer.py`) | ~485 | `reqwest` + the same `sqlite-vec` loadable extension |
| S3 (`core/s3_storage.py`) | ~270 | `aws-sdk-s3` / `object_store` |
| DB models + websocket + misc | ~1,100 | `rusqlite`/`sqlx`, tauri events |
| **Total app code** | **~15,700** | |
| − server-only code desktop deletes (JWT auth, users/oauth/tokens routes, ARQ worker) | ~−1,500 | not ported |

Roughly **13–14K lines of straightforward code to port** — HTTP, SQLite, files, git. There is no ML runtime, no numerics, nothing Python-specific: embeddings are HTTP calls to an API stored via `sqlite-vec` (a C extension loadable from any language). This is a bounded engineering project measured in months, not the "years" the UI would be.

**Why not the Python sidecar** (the suspicions are valid):

- **Packaging fragility**: PyInstaller output with native wheels must survive codesigning, hardened runtime, and notarization — a chronically brittle pipeline that breaks on dependency bumps.
- **Process management**: spawn, health-check, restart, port handshake, orphan cleanup on crash — a permanent tax on every launch path.
- **Attack surface**: a localhost TCP port serving an API with filesystem access and agent credentials, defended by a per-launch token. In-process, this entire class of concern disappears.
- **Size and startup**: ~100 MB+ of Python runtime and a cold interpreter start on every launch.

**Why Rust and not Swift for the engine**: the deciding factor is that Tauri's host process *is* Rust. A Rust engine is a crate linked into the app — no second process, no IPC, no port. A Swift engine would either run as a sidecar next to Tauri (recreating exactly the process-management problem being escaped, with the runtime swapped) or require dropping Tauri for a hand-built Swift/WKWebView shell, hand-rolling the updater/deep-link/tray plumbing Tauri provides. Beyond that: Rust's git story (`git2`) is solid where Swift's is stale (SwiftGit2); the same engine crate can later be wrapped in axum to replace the Python server deployment — one engine backing both web and desktop; and both Tauri v2 and the Rust crate compile for iOS, which pairs with the "closed block-type set makes a native/lighter client feasible" observation above. Swift everywhere is the right call only if the shell goes fully native too — a much bigger bet that still forks the engine from the server permanently.

**Fallback**: if the port stalls, the PyInstaller sidecar remains viable as originally designed — the shell/engine seam (SPA ↔ HTTP API) is identical either way, so the fallback does not change the frontend.

### High-Level Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                  Codex.app — single process                     │
│                                                                 │
│  ┌───────────────────────────┐   ┌──────────────────────────┐   │
│  │  Tauri shell (Rust)       │   │  Engine crate (Rust,      │   │
│  │  - WKWebView → Vue SPA    │   │  in-process)              │   │
│  │  - codex:// custom        │──►│  - API handlers           │   │
│  │    protocol → engine      │   │    (ex-FastAPI routes)    │   │
│  │  - Menu bar / Dock menu   │   │  - FSEvents watcher       │   │
│  │  - Global hotkey capture  │   │    (notify crate)         │   │
│  │  - Notifications          │   │  - Job queue (tokio)      │   │
│  │  - Tauri updater          │   │  - Integration proxies    │   │
│  │  - Spotlight/QuickLook    │   │  - Agent engine           │   │
│  │    extensions             │   │  - git2 / S3 / sqlite-vec │   │
│  └───────────────────────────┘   └──────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
                │                              │
                ▼                              ▼
   macOS services (Spotlight,      ~/Library/Application Support/Codex/
   Keychain, Notification Center)    codex_system.db, logs, plugin cache
                                   ~/Documents/Codex/<notebook>/
                                     content files + .codex/notebook.db
```

The Vue SPA and its API ship in the same binary, so frontend/engine versions can never skew — the property the Docker image has today, kept without a server.

---

## The Engine

### In-process embedding

The engine is a Rust library crate (`codex-engine`) linked into the Tauri app. The SPA's `/api/v1/` fetches are served through a **Tauri custom protocol handler** that dispatches directly to engine functions — no TCP socket is opened, so there is no port to collide with a user's dev servers (or a Docker Codex on 8765), no per-launch auth token ceremony, and no localhost API that other processes on the machine could probe. The frontend keeps its existing service layer (`services/api.ts` base URL becomes the custom-protocol origin); the engine holds filesystem access and agent credentials entirely inside the app's own process.

The WebSocket push channel (watcher-driven refresh, agent/task progress) doesn't fit a custom protocol; it is bridged instead — see WebSockets below.

An optional **local HTTP mode** (off by default, enabled in settings) binds the same handlers to a loopback port authenticated by a personal access token, for power users' scripts and CLI/agent access — opt-in exposure rather than a structural requirement.

### Desktop behavior profile

| Server behavior | Desktop behavior |
|---|---|
| JWT login, registration, password reset | **Single implicit local user**, auto-created on first launch. Login/register/reset routes and views don't exist in the desktop engine. Personal access tokens remain, used only by the opt-in local HTTP mode. |
| ARQ + Redis background worker | **In-process tokio task queue.** The worker jobs (import, vectorization) become async Rust tasks; Redis is never bundled. |
| Plugin secrets / agent credentials in DB | Stored in the **macOS Keychain** (`security-framework` crate) with DB fallback for portability. |
| Data under `/data` volume | System DB, logs, plugin cache under `~/Library/Application Support/Codex/`. Notebooks under user-chosen folders (default `~/Documents/Codex/`). |
| API on a network socket, CORS configured | No socket at all — custom-protocol dispatch inside the process (CORS is moot). Optional loopback port only when local HTTP mode is enabled. |
| S3 storage optional | Unchanged (off by default). |

### Compatibility with the Python server

The web/Kubernetes deployment stays on the Python backend, so the two engines must agree on every on-disk format: the notebook folder layout, frontmatter and page-metadata conventions, `.s3ref` pointer files, git `.gitignore` conventions, and the `notebook.db` schema (the sync features in this doc move notebooks between desktop and server). That contract is currently implicit in the Python code. The port makes it explicit:

- Write a short **notebook format spec** (formats + schema version) that both implementations cite.
- Build a **shared golden corpus** — real notebooks with edge-case frontmatter, nested pages, binaries, pointers — and run both engines' indexers over it in CI, diffing the resulting `notebook.db` contents. This is also the port's primary correctness harness.
- Version the notebook schema (already implied by per-notebook Alembic); either engine refuses notebooks stamped by a newer schema.

The endgame that dissolves the fork: wrap the same `codex-engine` crate in axum and replace the Python server with it. That is explicitly out of scope for the Mac app but should be treated as the likely follow-on — it means porting decisions favor "engine as a pure library with thin transport adapters" over Tauri-specific coupling.

### File watching

The port keeps the current design — one watcher per notebook syncing file changes into `.codex/notebook.db` — with the `notify` crate replacing watchdog on the same underlying FSEvents API. This is the mechanism that makes "edit in any app, see it in Codex" work. Two Mac-specific notes:

1. **FSEvents observer accumulation**: the test-suite note in CLAUDE.md (accumulated FSEvents observers segfault under watchdog) hints at how fragile long-lived observers can be. The desktop app runs for weeks at a time, so the ported watcher must provably tear down when a notebook is closed/removed; add a soak test that opens/closes 100 notebooks under FSEvents.
2. **iCloud Drive / Desktop & Documents sync**: files in iCloud-managed folders may be dataless (evicted) placeholders. The watcher and indexer must treat `NSFileProviderIdentifier`-style placeholder files as "present but not readable yet" rather than deleting index entries, and must not force-download entire notebooks just to index them. v1: detect iCloud placeholder files (`.icloud` naming / zero-size + extended attributes) and index lazily on materialization.

### Plugins in the desktop app

The plugin system today is effectively two things, and both port trivially:

- **Themes** are CSS files (`backend/plugins/<theme>/styles/main.css`) served by `/api/v1/plugins/assets/` — they work unchanged inside the WebView.
- **Integrations** (GitHub, OpenGraph, weather) are backend-side API proxies with manifest-declared config; their block components are compiled into the SPA. Secrets move to the Keychain per the desktop profile above.

The desktop build should **drop the vestigial runtime component-loading path** (dynamic `import()` of plugin JS from the assets endpoint) rather than carry it: it currently has nothing to load, and removing it lets the WebView run under a strict CSP with no runtime-fetched executable code — a meaningful hardening win for an app whose engine holds filesystem access and agent credentials. If loadable frontend plugins ever return, they should return behind a deliberate design (signed bundles), not this leftover mechanism.

### Push events (replacing WebSockets)

The frontend's WebSocket channel (`core/websocket.py`) is the push path for watcher-driven UI refresh and agent/task progress. WebSockets can't ride a custom protocol, and opening a port just for them would forfeit the no-socket posture — so in the desktop build the engine emits the same event payloads through **Tauri's event system**, and a small adapter in the frontend's WebSocket service subscribes to those events and re-dispatches them to existing consumers. The event *payloads* are part of the server-compatibility contract; only the transport differs. (When the app attaches remote workspaces, real WebSockets to that server are used as today.)

---

## macOS Integration Features

These are the reasons to build a Mac app at all, in priority order.

### P0 — launch blockers

1. **App lifecycle**: the engine lives in the app process — nothing to spawn or supervise. Closing the window keeps the app (and watchers, and scheduled agent tasks) running in the background — standard Mac document-app behavior.
2. **Native menus & shortcuts**: File/Edit/View/Window menus mapped to SPA routes and actions (⌘N new note, ⌘⇧F workspace search, ⌘, settings). The Vue app exposes a small `window.codexShell` command bus the shell invokes.
3. **Open/import via Finder**: register the app as a handler for `.md` files and notebook folders; drag a folder onto the Dock icon to register it as a notebook (the "notebook registration" flow that exists in the API today).
4. **`codex://` URL scheme**: `codex://workspace/<ws>/notebook/<nb>/block/<id>` deep links for use in other apps, agents, and notifications. This also becomes the target of Spotlight results.
5. **Signed, notarized DMG with Tauri's updater plugin.**

### P1 — the mac-native payoff

6. **Spotlight (Core Spotlight)**: a shell-side indexer mirrors the notebook search index into `CSSearchableItem`s (title, tags, snippet, `codex://` URL). Codex already maintains `SearchIndex` per notebook; the shell subscribes to index-change events over the WebSocket channel and upserts into Spotlight. Full-text stays in Codex; Spotlight gets titles/tags/summaries to keep the system index lean.
7. **Quick Look extension** for Codex notebook pages: render frontmatter metadata + Markdown body statically, with fenced custom blocks (```` ```weather ````, ```` ```github-issues ```` …) shown as labeled placeholders rather than executed, so pressing Space in Finder shows something meaningful instead of raw YAML.
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

- **Channel**: Developer-ID signed + notarized DMG, Tauri updater for updates. Homebrew cask as a secondary channel. A single-binary Rust app makes signing/notarization routine — no bundled interpreter or native-wheel zoo to shepherd through the hardened runtime.
- **App Store**: deferred, but notably more plausible than the sidecar design — a single-process app is sandbox-friendly; the remaining work is security-scoped bookmarks for user-chosen notebook folders (worth adopting anyway) and swapping the updater for App Store delivery. Revisit on demand.
- **Updates & migrations**: app update may carry schema migrations for both DB families. The desktop engine applies migrations equivalent to the server's Alembic history — same resulting schemas, same version stamps, tracked in the shared format spec. System DB migrates on first launch after update; each notebook DB migrates lazily on open (already the pattern). Never auto-migrate a notebook stamped by a *newer* schema version — refuse with a clear error instead (protects shared/git-synced notebooks from silent downgrade corruption).

## Phasing

| Phase | Scope | Exit criteria |
|---|---|---|
| **1. Engine core + shell** | Rust port of the core loop (blocks/metadata, watcher, search, notebook DB) validated against the golden corpus; Tauri shell serving the SPA via custom protocol; desktop profile (implicit user, App Support paths); signed DMG | Fresh Mac: download DMG → create notebook → edit a file in VS Code → change appears in app. No Docker, no login. |
| **2. Mac citizenship + engine completeness** | Menus/shortcuts, file associations, `codex://`, quick capture, notifications, Tauri updater; port the trailing engine pieces (integrations, agents, calendar, git manager) | Daily-drivable as primary journal |
| **3. System search & share** | Spotlight indexing, Quick Look, Share extension, Keychain-backed secrets | Notebook content findable from Spotlight |
| **4. Sync** | Remote workspace attach; git + S3 notebook sync UI (text via git remote, binaries via `.s3ref` pointers) | Same notebook — including images — usable on two Macs |

## Risks

1. **Port fidelity** — subtle behavior drift from the Python implementation (frontmatter edge cases, path normalization, ordering rules) could mis-index or corrupt notebooks that later sync to a server. Mitigation: the shared golden corpus diffed in CI (see Compatibility); port and validate the indexer against real notebooks before any shell work.
2. **Port underestimation / Rust capacity** — ~13–14K LOC is months of focused work and commits the team to owning Rust. Mitigation: the fallback (PyInstaller sidecar, the first draft of this doc) uses the identical SPA↔API seam, so a stall changes the engine plan without changing the frontend or the shell.
3. **FSEvents watcher longevity** — long-running observer leaks (the watchdog segfault note in the test suite shows this is easy to get wrong). Mitigation: watcher lifecycle soak test in CI on a macOS runner.
4. **iCloud Drive dataless files** breaking indexing or, worse, the watcher interpreting eviction as deletion. Mitigation: placeholder detection before any destructive index update; default notebook location outside iCloud with an explicit opt-in.
5. **Two engines during the fork window** — until the server adopts the shared crate, every format/schema change lands twice (Python and Rust). Mitigation: the format spec + schema versioning make drift loud instead of silent; bias roadmap toward wrapping `codex-engine` in axum and retiring the Python server.

## Open Questions

1. Do agents run while the app is "closed" (background) by default, or only while a window is open? (Proposal: background, with a menu-bar indicator, but off until Phase 2.)
2. When (not whether) does the Python server get replaced by an axum wrapper around `codex-engine` — after desktop v1 stabilizes, or developed in parallel? Until then, who owns keeping the two implementations in sync when formats change?
3. Minimum macOS version — 13 (Ventura) covers WKWebView features needed by the SPA and Tauri v2; confirm against the frontend's browserslist.

## References

- [AI Agent Integration](./ai-agent-integration.md) — agent engine to be ported into `codex-engine`
- `backend/codex/plugins/` + `frontend/src/services/pluginLoader.ts` — current (reduced) plugin system: CSS themes, integration proxies, SPA-bundled block components
- `backend/codex/core/watcher.py` — FSEvents-backed notebook sync
- `backend/codex/core/git_manager.py` — basis for git notebook sync
- `backend/codex/core/s3_storage.py` — `.s3ref` pointer mechanism for binary sync

(The former Plugin System and Dynamic Views design docs have been removed from the repo along with most of the features they described; this doc reflects the code as of 2026-07.)
