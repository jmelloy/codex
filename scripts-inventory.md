# Script Inventory: photosafe & clue

Survey date: 2026-05-05  
Repos: `jmelloy/photosafe`, `jmelloy/clue`  
Purpose: Read-only survey to support standardization planning.

---

## `jmelloy/photosafe`

### Shell Scripts

| Filename | Path | Language | Purpose |
|---|---|---|---|
| `build.sh` | `build.sh` | Shell | Builds Docker images with GIT_SHA env var via `docker compose build`. |
| `run_tests.sh` | `backend/run_tests.sh` | Shell | Starts test database container, waits for health, then runs pytest. |

### Python Scripts — `dump/` directory

| Filename | Path | Language | Purpose |
|---|---|---|---|
| `extract_dump.py` | `dump/extract_dump.py` | Python | Extracts JSON objects from data streams and organizes files into date-based directories. |
| `convert_to_xmp.py` | `dump/convert_to_xmp.py` | Python | Converts JSON photo metadata into XMP sidecar files with Adobe-standard XML. |
| `extract_civit.py` | `dump/extract_civit.py` | Python | Queries CivitAI API to fetch AI-generated image data with rate limiting. |
| `convert_to_markdown.py` | `dump/convert_to_markdown.py` | Python | Converts image directory YAML frontmatter into markdown documentation files. |
| `invoke.py` | `dump/invoke.py` | Python | Converts Invoke AI SQLite databases into XMP sidecar files. |
| `moments.py` | `dump/moments.py` | Python | Uses MLX Vision (Pixtral) to generate moment descriptions and organize photos by month. |
| `process_leonardo.py` | `dump/process_leonardo.py` | Python | Extracts metadata from Leonardo.AI images and copies them to an Obsidian vault. |
| `process_comfyui.py` | `dump/process_comfyui.py` | Python | Extracts metadata from ComfyUI images and syncs them to an Obsidian vault. |
| `process_civitai.py` | `dump/process_civitai.py` | Python | Extracts metadata from CivitAI images and organizes them in an Obsidian vault. |
| `process_invoke.py` | `dump/process_invoke.py` | Python | Extracts metadata from Invoke AI images and copies them to an Obsidian vault. |
| `process_mage.py` | `dump/process_mage.py` | Python | Extracts metadata from Mage.space images and organizes them in an Obsidian vault. |
| `walk_obsidian.py` | `dump/walk_obsidian.py` | Python | Walks Obsidian vault, parses markdown frontmatter, and outputs image-to-metadata mappings. |
| `walk.py` | `dump/walk.py` | Python | Recursively finds images in `_images/` folders and extracts associated YAML frontmatter. |
| `rename.py` | `dump/rename.py` | Python | Renames and moves output files into date-based folder structure from extracted metadata. |
| `mage.py` | `dump/mage.py` | Python | API client library for Leonardo.AI with session management, HTTP wrappers, and rate limiting. |
| `leonardo.py` | `dump/leonardo.py` | Python | HTTP wrapper for Leonardo.AI API handling headers and JSON serialization. |

### Python Scripts — Backend

| Filename | Path | Language | Purpose |
|---|---|---|---|
| `env.py` | `backend/alembic/env.py` | Python | Alembic migration environment; sets DB URL from env and configures SQLAlchemy engine. |

### Configuration / Dependency Files

| Filename | Path | Language | Purpose |
|---|---|---|---|
| `pyproject.toml` | `backend/pyproject.toml` | TOML | Python project config: dependencies, build system, tool settings. |
| `requirements.txt` | `dump/requirements.txt` | Pip | Python dependencies for `dump/` processing scripts. |
| `requirements.txt` | `legacy/sync_photos_linux/requirements.txt` | Pip | Python dependencies for legacy Linux photo-sync tool. |

**No Makefile, Go magefiles, or SQL scripts found.**

---

## `jmelloy/clue`

### Shell Scripts

| Filename | Path | Language | Purpose |
|---|---|---|---|
| `deploy.sh` | `scripts/deploy.sh` | Shell | Builds Docker image, pushes to registry, deploys to Kubernetes with configurable namespace/registry. |
| `install_git_hooks.sh` | `scripts/install_git_hooks.sh` | Shell | Configures git to use hooks from `.githooks/` for local development. |
| `resize_thumbnails.sh` | `scripts/resize_thumbnails.sh` | Shell | Generates 320×320 thumbnails for all PNG/JPG images via ImageMagick. |
| `git_history_screenshots.sh` | `scripts/git_history_screenshots.sh` | Shell | Walks git history, rebuilds Docker containers at intervals, captures screenshots for visual changelog. |
| `pre-commit` | `.githooks/pre-commit` | Shell | Git pre-commit hook: regenerates image thumbnails and stages them before every commit. |

### Python Scripts

| Filename | Path | Language | Purpose |
|---|---|---|---|
| `dump_game.py` | `scripts/dump_game.py` | Python | Dumps and inspects Clue game state and logs from Redis, with filtering by game ID. |
| `clean_cards.py` | `scripts/clean_cards.py` | Python | Detects card frame borders in AI-generated images and crops them intelligently via OpenCV. |
| `mage_generate.py` | `scripts/mage_generate.py` | Python | Automates image generation on mage.space/advanced via Playwright; supports batch prompts. |
| `mage_download.py` | `scripts/mage_download.py` | Python | Downloads saved images from mage.space/creations with metadata sidecars, resumable. |
| `live_ws_test.py` | `scripts/live_ws_test.py` | Python | End-to-end integration test: verifies agent WebSocket communication against live Docker env. |
| `generate_cards.py` | `scripts/generate_cards.py` | Python | Generates a full 52-card deck in 4 visual styles using PIL with configurable dimensions. |
| `tournament.py` | `scripts/tournament.py` | Python | ELO-style tournament runner: plays N games with configurable agent compositions, outputs ratings. |

### JavaScript / Node.js Scripts

| Filename | Path | Language | Purpose |
|---|---|---|---|
| `take_screenshots.js` | `scripts/take_screenshots.js` | Node.js | Captures screenshots of various game states via Playwright headless Chromium. |
| `git_history_screenshot_worker.js` | `scripts/git_history_screenshot_worker.js` | Node.js | Worker called per-commit by `git_history_screenshots.sh`; creates games and captures screenshots. |

**No Makefile, Go magefiles, or SQL scripts found.**

---

## Cross-Repo Analysis

### Overlaps and Near-Duplicates

| Theme | photosafe | clue | Notes |
|---|---|---|---|
| **Mage.space integration** | `dump/mage.py`, `dump/process_mage.py` | `scripts/mage_generate.py`, `scripts/mage_download.py` | Both repos interact with mage.space but differently: photosafe has a library + post-processor; clue has Playwright-driven generation + download. Different approaches to the same platform. |
| **Metadata extraction / dump** | `dump/extract_dump.py`, `dump/walk.py`, `dump/walk_obsidian.py` | `scripts/dump_game.py` | Both have "dump" scripts but with no overlap in domain (photo metadata vs. Redis game state). Naming is coincidentally similar. |
| **Docker build + deploy** | `build.sh` (build only) | `scripts/deploy.sh` (build + push + k8s deploy) | photosafe only builds; clue has a full deploy pipeline. photosafe may be missing a deploy step or uses CI instead. |
| **Testing** | `backend/run_tests.sh` | `scripts/live_ws_test.py` | Both provide test-runner scripts but photosafe's is shell-based (pytest wrapper) while clue's is a Python integration test. |
| **Screenshot tooling** | none | `scripts/take_screenshots.js`, `scripts/git_history_screenshots.sh`, `scripts/git_history_screenshot_worker.js` | Unique to clue. |
| **AI image processing** | 5× `process_*.py` scripts | `scripts/clean_cards.py`, `scripts/generate_cards.py` | photosafe post-processes externally generated images; clue generates and cleans card images. |

### Naming Inconsistencies

- photosafe `dump/` scripts use flat naming (`process_mage.py`, `process_leonardo.py`) while clue consolidates all scripts under `scripts/` — consistent within each repo but different conventions across repos.
- photosafe `dump/mage.py` is a **library** (API client), not a script; naming it without a `_client` or `_api` suffix risks confusion with the `process_mage.py` script next to it.
- clue separates generation from download (`mage_generate.py` vs `mage_download.py`) while photosafe merges both concerns into the library (`mage.py`) — inconsistent approach to the same external service.
- `dump_game.py` (clue) uses `dump_` prefix to mean "inspect/export Redis state"; photosafe's `dump/` directory uses `dump` to mean "data transformation pipeline" — semantically different meanings for the same word.

### Summary Counts

| Metric | photosafe | clue |
|---|---|---|
| Total scripts | 20 | 14 |
| Shell | 2 | 5 |
| Python | 17 | 7 |
| JavaScript | 0 | 2 |
| Go magefiles | 0 | 0 |
| SQL | 0 | 0 |
| Makefile | 0 | 0 |
| Scripts directory | `dump/` (ad-hoc) | `scripts/` (organized) |
