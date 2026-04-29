# diffusion-viewer

A photo browser and asset management tool for AI-generated images (Stable Diffusion, ComfyUI, Midjourney, DALL·E, etc.).

Built with **FastAPI** (Python) + **Vue 3** (Vite + Tailwind CSS).

---

## Features

- 🖼️ **Gallery view** — responsive grid organised by date, with thumbnails
- 🔍 **Detail view** — full-size image, metadata panel, prompt/sidecar JSON viewer, prev/next navigation
- 👍👎 **Ratings** — thumbs-up / thumbs-down (thumbs-down hides from view) + 1–5 star scale
- 🔎 **Search** — full-text across filename, prompt, description, sidecar data
- 🏷️ **Tagging** — add/remove tags per image or bulk-tag a selection
- 🤖 **Auto-tagging** — TF-IDF on prompts/descriptions extracts meaningful keywords automatically on scan
- 📅 **Date organisation** — reads creation date from sidecar (overrides filesystem mtime)
- 📄 **Sidecar support** — reads `<image>.json` sidecars in A1111, ComfyUI, and generic formats

---

## Project structure

```
diffusion-viewer/
├── backend/                 # FastAPI Python backend
│   ├── main.py              # App entry point, CORS, static thumbnails
│   ├── database.py          # SQLAlchemy / SQLite setup
│   ├── models.py            # Image, Tag, image_tags ORM models
│   ├── schemas.py           # Pydantic v2 request/response schemas
│   ├── requirements.txt
│   ├── routers/
│   │   ├── images.py        # /api/images endpoints
│   │   └── tags.py          # /api/tags endpoints
│   └── utils/
│       ├── scanner.py       # Directory walker + sidecar parser
│       └── tfidf.py         # TF-IDF auto-tagger
└── frontend/                # Vue 3 + Vite + Tailwind dark-theme SPA
    ├── src/
    │   ├── App.vue           # Nav bar + scan-directory modal
    │   ├── router/index.js   # / → Gallery, /image/:id → Detail
    │   ├── stores/images.js  # Pinia store (state + API calls)
    │   ├── views/
    │   │   ├── GalleryView.vue
    │   │   └── DetailView.vue
    │   └── components/
    │       ├── ImageCard.vue
    │       ├── RatingWidget.vue
    │       ├── TagManager.vue
    │       └── SearchBar.vue
    └── vite.config.js       # /api proxy → localhost:8000
```

---

## Getting started

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
# API available at http://localhost:8000
# Swagger UI at http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# App at http://localhost:5173
```

### Production build

```bash
cd frontend
npm run build        # outputs to frontend/dist/
# Serve dist/ via nginx / any static host, proxy /api to uvicorn
```

---

## Usage

1. Start backend (`uvicorn main:app --reload`)
2. Start frontend (`npm run dev`)
3. Open **http://localhost:5173**
4. Click **📂 Scan Directory** and enter the path to your images folder
5. The scanner will:
   - Index all `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif` files
   - Read `<image>.json` sidecar files for prompt, description, model, date
   - Generate 400×400 JPEG thumbnails
   - Auto-tag images using TF-IDF on prompts/descriptions

### Sidecar format

Any of these JSON structures are supported:

```json
// Generic
{ "prompt": "...", "description": "...", "model": "...", "date": "2024-01-15T10:30:00" }

// A1111 / Stable Diffusion
{ "parameters": "beautiful landscape\nNegative prompt: blur\nSteps: 20, Model: v1-5" }

// ComfyUI
{ "prompt": { "6": { "inputs": { "text": "beautiful landscape" }, "class_type": "CLIPTextEncode" } } }
```

---

## API reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/images` | List images (filters: `q`, `tags`, `min_rating`, `show_hidden`, `date_from`, `date_to`, `sort_by`, `sort_dir`, `page`, `limit`) |
| `GET` | `/api/images/{id}` | Image detail |
| `GET` | `/api/images/{id}/file` | Serve original file |
| `GET` | `/api/images/{id}/thumbnail` | Serve 400px thumbnail |
| `PUT` | `/api/images/{id}/rating` | Update rating (`-1`=thumbs-down/hide, `0`=unrated, `1`=thumbs-up, `2-6`=stars) |
| `POST` | `/api/images/{id}/tags` | Add tags `{"tag_names": ["tag1","tag2"]}` |
| `DELETE` | `/api/images/{id}/tags/{name}` | Remove tag |
| `POST` | `/api/images/scan` | Scan directory `{"directory": "/path"}` |
| `POST` | `/api/images/bulk-tag` | Bulk tag `{"image_ids": [1,2], "tag_names": ["tag"]}` |
| `DELETE` | `/api/images/{id}` | Hide image (soft delete) |
| `GET` | `/api/tags` | List all tags with image counts |
| `DELETE` | `/api/tags/{id}` | Delete tag |
