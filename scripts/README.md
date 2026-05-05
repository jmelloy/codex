# Scripts

Utility scripts for managing and exporting AI-generated image metadata.

## Setup

```bash
pip install -r requirements.txt
```

Some scripts depend on local library modules (`lib/`) from the photosafe project.

## Scripts

| Script | Description |
|---|---|
| `register_test_user.sh` | Register test users via the Codex HTTP API |
| `extract_dump.py` | Parse a large Apple Photos dump JSON, extract individual records and organise them by date/GUID under `output/` |
| `convert_to_xmp.py` | Convert image metadata JSON files to XMP sidecar files (Dublin Core, EXIF, XMP, Photoshop namespaces) |
| `extract_civit.py` | Fetch generations from the Civitai API (requires `CIVITAI_API_TOKEN`), download images and create XMP sidecars |
| `convert_to_markdown.py` | Convert image metadata JSON to Obsidian-compatible Markdown with YAML frontmatter; uses Ollama (gemma3:4b) to extract character names from prompts |
| `invoke.py` | Read an Invoke AI SQLite database and generate JSON/XMP sidecar files for every image |
| `mage.py` | Scrape a Mage.space user gallery (requires browser session cookies), download images and create XMP sidecars |
| `leonardo.py` | Fetch a Leonardo.ai user's generated images via GraphQL API (requires auth token) and download them organised by date |
| `moments.py` | Analyse Apple Photos collections with MLX-VLM (pixtral-12b) and write `moment.yaml` summaries per day — macOS/Apple Silicon only |
| `rename.py` | Rename output directory entries by `cloud_guid`/`uuid` from `apple.json`, organised by date |
| `process_comfyui.py` | Walk a ComfyUI output directory, extract per-image metadata, copy to Obsidian vault, and write JSON sidecars |
| `process_mage.py` | Walk a Mage.space output directory, extract metadata via `lib.mage`, and copy images to Obsidian vault |
| `process_civitai.py` | Walk a Civitai output directory, extract metadata via `lib.civitai`, and copy images to Obsidian vault |
| `process_invoke.py` | Walk an Invoke AI output directory, extract metadata via `lib.invoke`, and copy images to Obsidian vault |
| `process_leonardo.py` | Walk a Leonardo.ai output directory, extract metadata via `lib.leonardo`, and copy images to Obsidian vault |
| `walk_obsidian.py` | Walk an Obsidian vault, locate images inside `_images/` folders, extract YAML frontmatter from sibling Markdown files, and optionally copy images with JSON metadata sidecars to a destination directory |
| `walk.py` | tkinter GUI image viewer for browsing generated images; supports filtering by prompt, copying selected images to a destination folder, and logging viewed images to avoid duplicates |
