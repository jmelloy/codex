# Codex - Digital Laboratory Journal Architecture

**Status**: Draft  
**Author**: Engineering Team  
**Created**: 2024-11-27  
**Last Updated**: 2024-11-27

## Implementation Status

### ✅ Completed Features

| Feature | Status | Notes |
|---------|--------|-------|
| **Core Classes** | ✅ Complete | Workspace, Notebook, Page, Entry implemented |
| **SQLite Database** | ✅ Complete | SQLAlchemy ORM with full schema |
| **Git Integration** | ✅ Complete | Version control for structure via GitPython |
| **CLI** | ✅ Complete | Full command-line interface (init, notebook, page, entry, search, lineage, serve) |
| **REST API** | ✅ Complete | FastAPI endpoints for all entities |
| **Content-Addressable Storage** | ✅ Complete | SHA256 hashing, blob storage, thumbnails |
| **Lineage Tracking** | ✅ Complete | Parent-child relationships, ancestors/descendants |
| **Entry Variations** | ✅ Complete | Create variations with input overrides |
| **Tagging System** | ✅ Complete | Tags for notebooks, pages, and entries |
| **Integration Registry** | ✅ Complete | Plugin system for entry types |
| **Custom Integration** | ✅ Complete | Manual entry type |
| **API Call Integration** | ✅ Complete | HTTP request tracking |

### 🚧 Partial / Planned Features

| Feature | Status | Notes |
|---------|--------|-------|
| **WebSocket Execution** | 🚧 Planned | Directory structure exists, implementation pending |
| **Full-Text Search (FTS)** | 🚧 Planned | Basic search works, FTS5 not yet implemented |
| **Smart Archival** | 🚧 Planned | Settings exist, policies not enforced |

### ❌ Not Yet Implemented

| Feature | Status | Notes |
|---------|--------|-------|
| **Frontend (Vue.js)** | ❌ Not Started | Web UI not yet developed |
| **ComfyUI Integration** | ❌ Not Started | Workflow execution pending |
| **Database Query Integration** | ❌ Not Started | SQL/query execution pending |
| **Jupyter Integration** | ❌ Not Started | Notebook cell execution pending |
| **AI-Powered Insights** | ❌ Not Started | Summarization, pattern detection pending |
| **Export/Import** | ❌ Not Started | Notebook export functionality pending |

---

## Abstract

Codex is a hierarchical digital laboratory journal system organizing work into Notebooks → Pages → Entries. It tracks computational experiments, creative iterations, and technical investigations with full provenance, reproducibility, and AI-assisted insights. Think: Jupyter meets Obsidian meets Git, designed for engineers and creators who need to document explorations that generate artifacts.

## 1. Motivation

### Problems Being Solved

1. **Lost Experimental Context**: "What was I trying when this worked?"
2. **Scattered Artifacts**: Images, API responses, query results live in random folders
3. **Non-Reproducible Work**: Can't recreate successful experiments from 3 months ago
4. **No Narrative Thread**: Individual experiments lack the story of how you got there
5. **Storage Bloat**: Every iteration saved at full fidelity forever

### Core Metaphor: The Laboratory Notebook

Physical lab notebooks have a proven structure:
- **Notebook**: A bound volume for a project or research area
- **Page**: A day's work or a focused investigation session
- **Entry**: Individual experiments, observations, or results

We digitize this with modern affordances: version control, content-addressable storage, AI assistance, and cross-references.

## 2. Conceptual Model

### Hierarchy

```
Workspace (root directory)
├── Notebook: "AI Art Production"
│   ├── Page: "2024-11-27 - Landscape Generation"
│   │   ├── Entry: "Initial SDXL test with sunset prompt"
│   │   │   ├── Inputs: workflow.json, prompt, seed
│   │   │   └── Outputs: image-001.png, metadata.json
│   │   ├── Entry: "Higher CFG experiment"
│   │   └── Entry: "Final render for client"
│   └── Page: "2024-11-28 - Portrait Refinement"
│
└── Notebook: "API Integration Testing"
    ├── Page: "Stripe Payment Flow"
    │   ├── Entry: "Create customer API call"
    │   └── Entry: "Payment intent with metadata"
    └── Page: "Error Investigation"
```

### Entity Definitions

**Notebook**
- A collection of related work (project, investigation area, creative series)
- Has metadata: title, description, tags, created date
- Contains Pages in chronological or logical order
- Can reference other Notebooks

**Page**
- A focused work session or investigation thread
- Typically represents a day's work or a specific sub-topic
- Contains Entries (the actual experiments/observations)
- Has narrative context: goals, hypotheses, conclusions
- Can be dated or conceptual ("Background Research", "Final Renders")

**Entry**
- A single executable unit: an experiment, API call, image generation, query
- Has inputs (parameters, code, prompts) and outputs (artifacts, results, logs)
- Immutable once created (edits create new entries with lineage)
- Can derive from parent entries (variations, refinements)
- Stores full provenance for reproducibility

## 3. Data Model

### Directory Structure

```
/workspace-root/
  .lab/                                 # Hidden metadata directory
    config.json                         # Workspace config
    db/
      index.db                          # SQLite index
    git/                                # Git repo for structure
      notebooks/
        notebook-123/
          meta.json
          pages/
            page-456/
              meta.json
              entries/
                entry-789.json
    storage/                            # Content-addressable blobs
      blobs/
        ab/cd/abcd1234...
      thumbnails/
      
  notebooks/                            # User-facing structure
    ai-art-production/
      README.md                         # Notebook overview
      2024-11-27-landscape-generation/
        README.md                       # Page narrative
        entries/
          001-initial-test.md           # Entry notes
          001-initial-test.link         # Symlink to .lab
      2024-11-28-portrait-refinement/
        
  artifacts/                            # Materialized artifacts
    images/
      landscape-final.png -> .lab/storage/...
    data/
      api-response.json -> .lab/storage/...
```

### Core Schemas

#### Notebook

```json
{
  "id": "nb-abc123",
  "type": "notebook",
  "title": "AI Art Production",
  "description": "Exploring landscape and portrait generation for client work",
  "created_at": "2024-11-20T10:00:00Z",
  "updated_at": "2024-11-27T16:30:00Z",
  
  "metadata": {
    "tags": ["client-work", "sdxl", "landscapes"],
    "color": "#4F46E5",
    "icon": "🎨"
  },
  
  "pages": [
    "page-456",
    "page-457"
  ],
  
  "settings": {
    "default_entry_type": "comfyui_workflow",
    "auto_archive_days": 90,
    "archive_strategy": "thumbnail"
  }
}
```

#### Page

```json
{
  "id": "page-456",
  "notebook_id": "nb-abc123",
  "type": "page",
  "title": "Landscape Generation Experiments",
  "date": "2024-11-27",
  "created_at": "2024-11-27T09:00:00Z",
  "updated_at": "2024-11-27T16:30:00Z",
  
  "narrative": {
    "goals": "Generate high-quality sunset landscapes for client portfolio",
    "hypothesis": "Higher CFG values will give more detailed clouds",
    "observations": "CFG 7.5 worked well, 10.0 was too sharp",
    "conclusions": "Settled on CFG 8.0 with 35 steps for production",
    "next_steps": "Try different time-of-day prompts"
  },
  
  "entries": [
    "entry-789",
    "entry-790",
    "entry-791"
  ],
  
  "metadata": {
    "tags": ["experiments", "client-review"],
    "status": "completed"
  }
}
```

#### Entry

```json
{
  "id": "entry-789",
  "page_id": "page-456",
  "type": "entry",
  "entry_type": "comfyui_workflow",
  "title": "Initial SDXL sunset test",
  "created_at": "2024-11-27T10:30:00Z",
  "status": "completed",
  
  "lineage": {
    "parent_id": null,
    "children_ids": ["entry-790"],
    "derived_from": null,
    "variation_of": null
  },
  
  "inputs": {
    "type": "comfyui",
    "workflow_file": "workflow-v2.json",
    "workflow_hash": "sha256:abcd...",
    "parameters": {
      "prompt": "a serene lake at sunset, golden hour, photorealistic",
      "negative_prompt": "cartoon, low quality",
      "model": "sdxl_v1.0",
      "seed": 42,
      "steps": 30,
      "cfg": 7.5,
      "width": 1024,
      "height": 1024
    }
  },
  
  "execution": {
    "started_at": "2024-11-27T10:30:15Z",
    "completed_at": "2024-11-27T10:30:27Z",
    "duration_seconds": 12.4,
    "status": "success",
    "exit_code": 0
  },
  
  "outputs": {
    "artifacts": [
      {
        "id": "art-001",
        "type": "image/png",
        "hash": "sha256:efgh...",
        "size_bytes": 2048576,
        "path": "storage/blobs/ef/gh/efgh...",
        "thumbnail_path": "storage/thumbnails/ef/gh/efgh...thumb.jpg",
        "metadata": {
          "width": 1024,
          "height": 1024,
          "format": "PNG"
        }
      }
    ],
    "logs": {
      "stdout": "storage/blobs/.../stdout.log",
      "stderr": null
    },
    "metadata": {
      "comfyui_prompt_id": "12345"
    }
  },
  
  "metrics": {
    "cost": {
      "compute_seconds": 12.4,
      "estimated_usd": 0.002
    }
  },
  
  "metadata": {
    "tags": ["initial-test", "sunset"],
    "notes": "First attempt, looks promising but sky could use more detail",
    "rating": 3,
    "archived": false
  }
}
```

### SQLite Schema

```sql
-- Notebooks
CREATE TABLE notebooks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    settings JSON,
    metadata JSON
);

CREATE INDEX idx_notebooks_created ON notebooks(created_at DESC);

-- Pages
CREATE TABLE pages (
    id TEXT PRIMARY KEY,
    notebook_id TEXT NOT NULL,
    title TEXT NOT NULL,
    date DATE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    narrative JSON,
    metadata JSON,
    
    FOREIGN KEY (notebook_id) REFERENCES notebooks(id) ON DELETE CASCADE
);

CREATE INDEX idx_pages_notebook ON pages(notebook_id);
CREATE INDEX idx_pages_date ON pages(date DESC);

-- Entries
CREATE TABLE entries (
    id TEXT PRIMARY KEY,
    page_id TEXT NOT NULL,
    entry_type TEXT NOT NULL,
    title TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    status TEXT NOT NULL,
    
    parent_id TEXT,
    
    inputs JSON NOT NULL,
    outputs JSON,
    execution JSON,
    metrics JSON,
    metadata JSON,
    
    FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES entries(id)
);

CREATE INDEX idx_entries_page ON entries(page_id);
CREATE INDEX idx_entries_parent ON entries(parent_id);
CREATE INDEX idx_entries_created ON entries(created_at DESC);
CREATE INDEX idx_entries_type ON entries(entry_type);

-- Full-text search
CREATE VIRTUAL TABLE entries_fts USING fts5(
    entry_id UNINDEXED,
    title,
    content,
    tags,
    notes,
    tokenize = 'porter'
);

-- Artifacts
CREATE TABLE artifacts (
    id TEXT PRIMARY KEY,
    entry_id TEXT NOT NULL,
    type TEXT NOT NULL,
    hash TEXT NOT NULL UNIQUE,
    size_bytes INTEGER NOT NULL,
    path TEXT NOT NULL,
    thumbnail_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    archived BOOLEAN DEFAULT FALSE,
    archive_strategy TEXT,
    original_size_bytes INTEGER,
    
    metadata JSON,
    
    FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE
);

CREATE INDEX idx_artifacts_entry ON artifacts(entry_id);
CREATE INDEX idx_artifacts_hash ON artifacts(hash);

-- Lineage graph
CREATE TABLE entry_lineage (
    parent_id TEXT NOT NULL,
    child_id TEXT NOT NULL,
    relationship_type TEXT DEFAULT 'derives_from',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (parent_id, child_id),
    FOREIGN KEY (parent_id) REFERENCES entries(id) ON DELETE CASCADE,
    FOREIGN KEY (child_id) REFERENCES entries(id) ON DELETE CASCADE
);

-- Tags
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    color TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE notebook_tags (
    notebook_id TEXT NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (notebook_id, tag_id),
    FOREIGN KEY (notebook_id) REFERENCES notebooks(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);

CREATE TABLE page_tags (
    page_id TEXT NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (page_id, tag_id),
    FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);

CREATE TABLE entry_tags (
    entry_id TEXT NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (entry_id, tag_id),
    FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);
```

## 4. Backend Architecture (Python)

### 4.1 Technology Stack

- **FastAPI**: REST API server
- **SQLAlchemy**: ORM for SQLite
- **GitPython**: Version control for structure
- **Watchdog**: Filesystem monitoring
- **Pillow**: Image processing
- **Pydantic**: Validation
- **APScheduler**: Background jobs

### 4.2 Project Structure

```
codex/
  __init__.py
  
  api/
    __init__.py
    main.py                    # FastAPI app
    routes/
      notebooks.py
      pages.py
      entries.py
      artifacts.py
      search.py
    websocket/
      execution.py             # Real-time execution updates
  
  core/
    __init__.py
    workspace.py              # Workspace management
    notebook.py               # Notebook operations
    page.py                   # Page operations
    entry.py                  # Entry CRUD and execution
    storage.py                # Content-addressable storage
    lineage.py                # Lineage tracking
    archive.py                # Archival policies
    git_manager.py            # Git operations
    
  integrations/
    __init__.py
    base.py
    comfyui.py
    api_call.py
    database.py
    jupyter.py
    custom.py
    
  db/
    __init__.py
    models.py                 # SQLAlchemy models
    operations.py
    
  cli/
    __init__.py
    main.py                   # Click CLI
    commands/
      init.py
      notebook.py
      page.py
      entry.py
      search.py
      archive.py
```

### 4.3 Core Classes

#### Workspace

```python
from pathlib import Path
from typing import Optional, List
import json

class Workspace:
    """Root workspace containing notebooks"""
    
    def __init__(self, path: Path):
        self.path = path
        self.lab_path = path / ".lab"
        self.notebooks_path = path / "notebooks"
        self.artifacts_path = path / "artifacts"
        
    @classmethod
    def initialize(cls, path: Path, name: str) -> "Workspace":
        """Initialize a new workspace"""
        ws = cls(path)
        
        # Create directory structure
        ws.lab_path.mkdir(parents=True, exist_ok=True)
        (ws.lab_path / "db").mkdir(exist_ok=True)
        (ws.lab_path / "storage" / "blobs").mkdir(parents=True, exist_ok=True)
        (ws.lab_path / "storage" / "thumbnails").mkdir(parents=True, exist_ok=True)
        ws.notebooks_path.mkdir(parents=True, exist_ok=True)
        ws.artifacts_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize Git
        GitManager.initialize(ws.lab_path / "git")
        
        # Initialize database
        DatabaseManager.initialize(ws.lab_path / "db" / "index.db")
        
        # Create config
        config = {
            "name": name,
            "version": "1.0.0",
            "created_at": datetime.utcnow().isoformat()
        }
        
        with open(ws.lab_path / "config.json", 'w') as f:
            json.dump(config, f, indent=2)
            
        return ws
    
    def create_notebook(
        self,
        title: str,
        description: str = "",
        tags: List[str] = None
    ) -> "Notebook":
        """Create a new notebook"""
        return Notebook.create(self, title, description, tags or [])
    
    def list_notebooks(self) -> List["Notebook"]:
        """List all notebooks"""
        return DatabaseManager.list_notebooks(self)
```

#### Notebook

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import hashlib

@dataclass
class Notebook:
    """A notebook contains pages"""
    
    id: str
    workspace: Workspace
    title: str
    description: str
    created_at: datetime
    updated_at: datetime
    tags: List[str]
    settings: dict
    
    @classmethod
    def create(
        cls,
        workspace: Workspace,
        title: str,
        description: str = "",
        tags: List[str] = None
    ) -> "Notebook":
        """Create a new notebook"""
        
        notebook_id = f"nb-{hashlib.sha256(
            f'{datetime.utcnow().isoformat()}-{title}'.encode()
        ).hexdigest()[:12]}"
        
        notebook = cls(
            id=notebook_id,
            workspace=workspace,
            title=title,
            description=description,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tags=tags or [],
            settings={
                "default_entry_type": "custom",
                "auto_archive_days": 90,
                "archive_strategy": "compress"
            }
        )
        
        # Create in database
        DatabaseManager.insert_notebook(workspace, notebook)
        
        # Create Git structure
        GitManager.create_notebook(workspace, notebook)
        
        # Create user-facing directory
        notebook_dir = workspace.notebooks_path / cls._slugify(title)
        notebook_dir.mkdir(exist_ok=True)
        
        # Create README
        with open(notebook_dir / "README.md", 'w') as f:
            f.write(f"# {title}\n\n{description}\n\nCreated: {notebook.created_at.isoformat()}\n")
        
        return notebook
    
    def create_page(
        self,
        title: str,
        date: Optional[datetime] = None,
        narrative: dict = None
    ) -> "Page":
        """Create a new page in this notebook"""
        return Page.create(self, title, date, narrative or {})
    
    def list_pages(self) -> List["Page"]:
        """List all pages in this notebook"""
        return DatabaseManager.list_pages(self.workspace, self.id)
    
    @staticmethod
    def _slugify(text: str) -> str:
        """Convert title to filesystem-safe slug"""
        import re
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text.strip('-')
```

#### Page

```python
@dataclass
class Page:
    """A page contains entries and narrative"""
    
    id: str
    notebook_id: str
    workspace: Workspace
    title: str
    date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    narrative: dict
    tags: List[str]
    
    @classmethod
    def create(
        cls,
        notebook: Notebook,
        title: str,
        date: Optional[datetime] = None,
        narrative: dict = None
    ) -> "Page":
        """Create a new page"""
        
        page_id = f"page-{hashlib.sha256(
            f'{datetime.utcnow().isoformat()}-{title}'.encode()
        ).hexdigest()[:12]}"
        
        page = cls(
            id=page_id,
            notebook_id=notebook.id,
            workspace=notebook.workspace,
            title=title,
            date=date or datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            narrative=narrative or {
                "goals": "",
                "hypothesis": "",
                "observations": "",
                "conclusions": "",
                "next_steps": ""
            },
            tags=[]
        )
        
        # Save to database
        DatabaseManager.insert_page(notebook.workspace, page)
        
        # Commit to Git
        GitManager.create_page(notebook.workspace, notebook, page)
        
        # Create user-facing directory
        date_str = page.date.strftime("%Y-%m-%d") if page.date else "undated"
        page_slug = Notebook._slugify(title)
        page_dir = notebook.workspace.notebooks_path / Notebook._slugify(notebook.title) / f"{date_str}-{page_slug}"
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "entries").mkdir(exist_ok=True)
        
        # Create README with narrative
        with open(page_dir / "README.md", 'w') as f:
            f.write(f"# {title}\n\n")
            f.write(f"**Date**: {date_str}\n\n")
            f.write(f"## Goals\n{page.narrative.get('goals', '')}\n\n")
            f.write(f"## Hypothesis\n{page.narrative.get('hypothesis', '')}\n\n")
            f.write(f"## Observations\n\n")
            f.write(f"## Conclusions\n\n")
            f.write(f"## Next Steps\n\n")
        
        return page
    
    def create_entry(
        self,
        entry_type: str,
        title: str,
        inputs: dict,
        parent_id: Optional[str] = None,
        tags: List[str] = None
    ) -> "Entry":
        """Create a new entry on this page"""
        return Entry.create(
            self,
            entry_type,
            title,
            inputs,
            parent_id,
            tags or []
        )
    
    def update_narrative(self, field: str, content: str):
        """Update narrative field"""
        self.narrative[field] = content
        self.updated_at = datetime.utcnow()
        DatabaseManager.update_page(self.workspace, self)
        GitManager.commit_page_update(self.workspace, self)
```

#### Entry

```python
@dataclass
class Entry:
    """An individual experiment/observation entry"""
    
    id: str
    page_id: str
    workspace: Workspace
    entry_type: str
    title: str
    created_at: datetime
    status: str
    
    parent_id: Optional[str]
    inputs: dict
    outputs: dict
    execution: dict
    metrics: dict
    metadata: dict
    
    @classmethod
    def create(
        cls,
        page: Page,
        entry_type: str,
        title: str,
        inputs: dict,
        parent_id: Optional[str] = None,
        tags: List[str] = None
    ) -> "Entry":
        """Create a new entry"""
        
        entry_id = f"entry-{hashlib.sha256(
            f'{datetime.utcnow().isoformat()}-{title}'.encode()
        ).hexdigest()[:12]}"
        
        entry = cls(
            id=entry_id,
            page_id=page.id,
            workspace=page.workspace,
            entry_type=entry_type,
            title=title,
            created_at=datetime.utcnow(),
            status="created",
            parent_id=parent_id,
            inputs=inputs,
            outputs={},
            execution={},
            metrics={},
            metadata={
                "tags": tags or [],
                "notes": "",
                "rating": None,
                "archived": False
            }
        )
        
        # Save to database
        DatabaseManager.insert_entry(page.workspace, entry)
        
        # Commit manifest to Git
        GitManager.commit_entry(page.workspace, entry)
        
        # Update lineage if has parent
        if parent_id:
            DatabaseManager.add_lineage_edge(
                page.workspace,
                parent_id,
                entry_id,
                "derives_from"
            )
        
        return entry
    
    async def execute(self, integration_class=None):
        """Execute this entry using its integration"""
        
        self.status = "running"
        self.execution["started_at"] = datetime.utcnow().isoformat()
        DatabaseManager.update_entry(self.workspace, self)
        
        try:
            # Get integration
            if integration_class is None:
                integration_class = IntegrationRegistry.get(self.entry_type)
            
            integration = integration_class(self.workspace)
            
            # Execute
            result = await integration.execute(self.inputs)
            
            # Store outputs
            self.outputs = result.get("outputs", {})
            self.execution["completed_at"] = datetime.utcnow().isoformat()
            self.execution["status"] = "success"
            self.status = "completed"
            
            # Store artifacts
            if "artifacts" in result:
                for artifact_data in result["artifacts"]:
                    self.add_artifact(
                        artifact_type=artifact_data["type"],
                        data=artifact_data["data"],
                        metadata=artifact_data.get("metadata", {})
                    )
            
        except Exception as e:
            self.execution["completed_at"] = datetime.utcnow().isoformat()
            self.execution["status"] = "error"
            self.execution["error"] = str(e)
            self.status = "failed"
            raise
        
        finally:
            DatabaseManager.update_entry(self.workspace, self)
            GitManager.commit_entry_update(self.workspace, self)
    
    def add_artifact(
        self,
        artifact_type: str,
        data: bytes,
        metadata: dict = None
    ) -> "Artifact":
        """Add artifact to this entry"""
        
        # Store in content-addressable storage
        artifact_hash = StorageManager.store(
            workspace=self.workspace,
            data=data,
            artifact_type=artifact_type
        )
        
        artifact = Artifact(
            id=f"art-{hashlib.sha256(artifact_hash.encode()).hexdigest()[:12]}",
            entry_id=self.id,
            type=artifact_type,
            hash=artifact_hash,
            size_bytes=len(data),
            metadata=metadata or {}
        )
        
        DatabaseManager.insert_artifact(self.workspace, artifact)
        
        return artifact
    
    def get_lineage(self, depth: int = 3) -> dict:
        """Get lineage graph for this entry"""
        ancestors = self._get_ancestors(depth)
        descendants = self._get_descendants(depth)
        
        return {
            "ancestors": ancestors,
            "descendants": descendants,
            "entry": self
        }
    
    def create_variation(
        self,
        title: str,
        input_overrides: dict,
        tags: List[str] = None
    ) -> "Entry":
        """Create a variation of this entry"""
        
        new_inputs = {**self.inputs, **input_overrides}
        
        # Get parent page
        page = DatabaseManager.get_page(self.workspace, self.page_id)
        
        variation = Entry.create(
            page=page,
            entry_type=self.entry_type,
            title=title,
            inputs=new_inputs,
            parent_id=self.id,
            tags=tags or self.metadata.get("tags", [])
        )
        
        # Add variation relationship
        DatabaseManager.add_lineage_edge(
            self.workspace,
            self.id,
            variation.id,
            "variation_of"
        )
        
        return variation
```

### 4.4 Integration System

```python
class IntegrationRegistry:
    """Registry for entry type integrations"""
    
    _integrations: Dict[str, Type[IntegrationBase]] = {}
    
    @classmethod
    def register(cls, entry_type: str):
        """Decorator to register integration"""
        def decorator(integration_class):
            cls._integrations[entry_type] = integration_class
            return integration_class
        return decorator
    
    @classmethod
    def get(cls, entry_type: str) -> Type[IntegrationBase]:
        """Get integration for entry type"""
        if entry_type not in cls._integrations:
            raise ValueError(f"No integration registered for: {entry_type}")
        return cls._integrations[entry_type]


class IntegrationBase:
    """Base integration class"""
    
    def __init__(self, workspace: Workspace):
        self.workspace = workspace
    
    async def execute(self, inputs: dict) -> dict:
        """Execute and return results"""
        raise NotImplementedError
    
    def validate_inputs(self, inputs: dict) -> bool:
        """Validate inputs"""
        return True


@IntegrationRegistry.register("comfyui_workflow")
class ComfyUIIntegration(IntegrationBase):
    """ComfyUI workflow execution"""
    
    async def execute(self, inputs: dict) -> dict:
        workflow = inputs["workflow"]
        parameters = inputs.get("parameters", {})
        
        client = ComfyUIClient("http://localhost:8188")
        prompt_id = client.queue_prompt(workflow, parameters)
        
        outputs = await client.wait_for_completion_async(prompt_id)
        
        artifacts = []
        for node_output in outputs.values():
            if "images" in node_output:
                for img_info in node_output["images"]:
                    image_data = client.download_image(
                        img_info["filename"],
                        img_info.get("subfolder", "")
                    )
                    artifacts.append({
                        "type": "image/png",
                        "data": image_data,
                        "metadata": {
                            "width": img_info.get("width"),
                            "height": img_info.get("height")
                        }
                    })
        
        return {
            "outputs": {
                "prompt_id": prompt_id,
                "raw_outputs": outputs
            },
            "artifacts": artifacts
        }


@IntegrationRegistry.register("api_call")
class APICallIntegration(IntegrationBase):
    """HTTP API call tracking"""
    
    async def execute(self, inputs: dict) -> dict:
        import aiohttp
        
        method = inputs.get("method", "GET")
        url = inputs["url"]
        headers = inputs.get("headers", {})
        body = inputs.get("body")
        
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, json=body) as response:
                response_text = await response.text()
                duration = time.time() - start_time
                
                return {
                    "outputs": {
                        "status_code": response.status,
                        "headers": dict(response.headers),
                        "body": response_text,
                        "duration_seconds": duration
                    },
                    "artifacts": [
                        {
                            "type": "application/json",
                            "data": response_text.encode(),
                            "metadata": {
                                "status_code": response.status,
                                "content_type": response.headers.get("Content-Type")
                            }
                        }
                    ]
                }


@IntegrationRegistry.register("database_query")
class DatabaseQueryIntegration(IntegrationBase):
    """Database query execution"""
    
    async def execute(self, inputs: dict) -> dict:
        import asyncpg
        
        connection_string = inputs["connection_string"]
        query = inputs["query"]
        parameters = inputs.get("parameters", [])
        
        start_time = time.time()
        
        conn = await asyncpg.connect(connection_string)
        try:
            rows = await conn.fetch(query, *parameters)
            duration = time.time() - start_time
            
            # Convert to JSON-serializable format
            results = [dict(row) for row in rows]
            
            return {
                "outputs": {
                    "row_count": len(rows),
                    "duration_seconds": duration,
                    "results": results[:100]  # Limit for preview
                },
                "artifacts": [
                    {
                        "type": "application/json",
                        "data": json.dumps(results).encode(),
                        "metadata": {
                            "row_count": len(rows)
                        }
                    }
                ]
            }
        finally:
            await conn.close()
```

## 5. API Endpoints (FastAPI)

```python
from fastapi import FastAPI, WebSocket, UploadFile, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Optional, List

app = FastAPI(title="Lab Notebook API")

# Notebooks
@app.post("/api/notebooks")
async def create_notebook(
    workspace_path: str,
    title: str,
    description: str = "",
    tags: List[str] = None
):
    """Create a new notebook"""
    ws = Workspace(Path(workspace_path))
    notebook = ws.create_notebook(title, description, tags)
    return notebook_to_dict(notebook)

@app.get("/api/notebooks")
async def list_notebooks(workspace_path: str):
    """List all notebooks in workspace"""
    ws = Workspace(Path(workspace_path))
    notebooks = ws.list_notebooks()
    return [notebook_to_dict(nb) for nb in notebooks]

@app.get("/api/notebooks/{notebook_id}")
async def get_notebook(workspace_path: str, notebook_id: str):
    """Get notebook details"""
    ws = Workspace(Path(workspace_path))
    notebook = DatabaseManager.get_notebook(ws, notebook_id)
    return notebook_to_dict(notebook)

# Pages
@app.post("/api/notebooks/{notebook_id}/pages")
async def create_page(
    workspace_path: str,
    notebook_id: str,
    title: str,
    date: Optional[str] = None,
    narrative: dict = None
):
    """Create a new page"""
    ws = Workspace(Path(workspace_path))
    notebook = DatabaseManager.get_notebook(ws, notebook_id)
    
    page_date = datetime.fromisoformat(date) if date else None
    page = notebook.create_page(title, page_date, narrative)
    
    return page_to_dict(page)

@app.get("/api/notebooks/{notebook_id}/pages")
async def list_pages(workspace_path: str, notebook_id: str):
    """List pages in notebook"""
    ws = Workspace(Path(workspace_path))
    pages = DatabaseManager.list_pages(ws, notebook_id)
    return [page_to_dict(p) for p in pages]

@app.patch("/api/pages/{page_id}/narrative")
async def update_narrative(
    workspace_path: str,
    page_id: str,
    field: str,
    content: str
):
    """Update page narrative field"""
    ws = Workspace(Path(workspace_path))
    page = DatabaseManager.get_page(ws, page_id)
    page.update_narrative(field, content)
    return page_to_dict(page)

# Entries
@app.post("/api/pages/{page_id}/entries")
async def create_entry(
    workspace_path: str,
    page_id: str,
    entry_type: str,
    title: str,
    inputs: dict,
    parent_id: Optional[str] = None,
    tags: List[str] = None,
    execute_immediately: bool = False
):
    """Create a new entry"""
    ws = Workspace(Path(workspace_path))
    page = DatabaseManager.get_page(ws, page_id)
    
    entry = page.create_entry(entry_type, title, inputs, parent_id, tags)
    
    if execute_immediately:
        await entry.execute()
    
    return entry_to_dict(entry)

@app.post("/api/entries/{entry_id}/execute")
async def execute_entry(workspace_path: str, entry_id: str):
    """Execute an entry"""
    ws = Workspace(Path(workspace_path))
    entry = DatabaseManager.get_entry(ws, entry_id)
    
    await entry.execute()
    
    return entry_to_dict(entry)

@app.post("/api/entries/{entry_id}/variations")
async def create_variation(
    workspace_path: str,
    entry_id: str,
    title: str,
    input_overrides: dict,
    tags: List[str] = None
):
    """Create a variation of an entry"""
    ws = Workspace(Path(workspace_path))
    entry = DatabaseManager.get_entry(ws, entry_id)
    
    variation = entry.create_variation(title, input_overrides, tags)
    
    return entry_to_dict(variation)

@app.get("/api/entries/{entry_id}/lineage")
async def get_entry_lineage(
    workspace_path: str,
    entry_id: str,
    depth: int = 3
):
    """Get entry lineage graph"""
    ws = Workspace(Path(workspace_path))
    entry = DatabaseManager.get_entry(ws, entry_id)
    
    lineage = entry.get_lineage(depth)
    
    return {
        "ancestors": [entry_to_dict(e) for e in lineage["ancestors"]],
        "descendants": [entry_to_dict(e) for e in lineage["descendants"]],
        "entry": entry_to_dict(lineage["entry"])
    }

# Artifacts
@app.post("/api/entries/{entry_id}/artifacts")
async def upload_artifact(
    workspace_path: str,
    entry_id: str,
    file: UploadFile,
    metadata: Optional[str] = None
):
    """Upload artifact to entry"""
    ws = Workspace(Path(workspace_path))
    entry = DatabaseManager.get_entry(ws, entry_id)
    
    data = await file.read()
    artifact_metadata = json.loads(metadata) if metadata else {}
    
    artifact = entry.add_artifact(
        artifact_type=file.content_type or "application/octet-stream",
        data=data,
        metadata=artifact_metadata
    )
    
    return artifact_to_dict(artifact)

@app.get("/api/artifacts/{artifact_hash}")
async def get_artifact(
    workspace_path: str,
    artifact_hash: str,
    thumbnail: bool = False
):
    """Retrieve artifact by hash"""
    ws = Workspace(Path(workspace_path))
    
    if thumbnail:
        data = StorageManager.get_thumbnail(ws, artifact_hash)
        media_type = "image/jpeg"
    else:
        data = StorageManager.retrieve(ws, artifact_hash)
        artifact = DatabaseManager.get_artifact_by_hash(ws, artifact_hash)
        media_type = artifact.type
    
    return StreamingResponse(
        io.BytesIO(data),
        media_type=media_type
    )

# Search
@app.post("/api/search")
async def search(
    workspace_path: str,
    query: Optional[str] = None,
    entry_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    notebook_id: Optional[str] = None,
    page_id: Optional[str] = None
):
    """Search entries"""
    ws = Workspace(Path(workspace_path))
    
    filters = {
        "query": query,
        "entry_type": entry_type,
        "tags": tags,
        "date_from": datetime.fromisoformat(date_from) if date_from else None,
        "date_to": datetime.fromisoformat(date_to) if date_to else None,
        "notebook_id": notebook_id,
        "page_id": page_id
    }
    
    results = DatabaseManager.search_entries(ws, filters)
    
    return {
        "results": [entry_to_dict(e) for e in results],
        "count": len(results)
    }

# WebSocket for real-time execution
@app.websocket("/ws/entries/{entry_id}/execute")
async def execute_entry_ws(websocket: WebSocket, workspace_path: str, entry_id: str):
    """Execute entry with real-time updates"""
    await websocket.accept()
    
    ws = Workspace(Path(workspace_path))
    entry = DatabaseManager.get_entry(ws, entry_id)
    
    try:
        # Send start notification
        await websocket.send_json({
            "type": "started",
            "entry_id": entry_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Execute with streaming updates
        # (Implementation would hook into integration to send progress)
        await entry.execute()
        
        # Send completion
        await websocket.send_json({
            "type": "completed",
            "entry_id": entry_id,
            "entry": entry_to_dict(entry),
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "entry_id": entry_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })
    finally:
        await websocket.close()
```

## 6. Frontend Architecture (Vue.js)

### 6.1 Project Structure

```
frontend/
  src/
    main.ts
    App.vue
    
    router/
      index.ts
      
    stores/
      workspace.ts
      notebooks.ts
      pages.ts
      entries.ts
      
    views/
      WorkspaceView.vue
      NotebookList.vue
      NotebookView.vue
      PageView.vue
      EntryView.vue
      SearchView.vue
      
    components/
      notebook/
        NotebookCard.vue
        NotebookSidebar.vue
      page/
        PageCard.vue
        PageNarrative.vue
        PageTimeline.vue
      entry/
        EntryCard.vue
        EntryForm.vue
        EntryDetail.vue
        ExecutionLog.vue
      artifact/
        ArtifactGallery.vue
        ArtifactViewer.vue
        ImageComparison.vue
      lineage/
        LineageGraph.vue
      common/
        TagInput.vue
        MarkdownEditor.vue
```

### 6.2 Key Components

#### Notebook View

```vue
<template>
  <div class="notebook-view">
    <div class="notebook-header">
      <h1>{{ notebook.title }}</h1>
      <p class="description">{{ notebook.description }}</p>
      <div class="tags">
        <span v-for="tag in notebook.tags" :key="tag" class="tag">
          {{ tag }}
        </span>
      </div>
    </div>
    
    <div class="notebook-content">
      <aside class="sidebar">
        <div class="actions">
          <button @click="createPage" class="primary">New Page</button>
        </div>
        
        <nav class="page-list">
          <h3>Pages</h3>
          <PageCard
            v-for="page in pages"
            :key="page.id"
            :page="page"
            :active="page.id === currentPageId"
            @click="selectPage(page.id)"
          />
        </nav>
      </aside>
      
      <main class="page-content">
        <PageView 
          v-if="currentPage"
          :page="currentPage"
          @update="refreshPage"
        />
        <div v-else class="empty-state">
          <p>Select a page or create a new one</p>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useNotebooksStore } from '@/stores/notebooks'
import { usePagesStore } from '@/stores/pages'

const route = useRoute()
const router = useRouter()
const notebooksStore = useNotebooksStore()
const pagesStore = usePagesStore()

const notebookId = computed(() => route.params.notebookId as string)
const currentPageId = computed(() => route.params.pageId as string)

const notebook = computed(() => notebooksStore.notebooks.get(notebookId.value))
const pages = computed(() => pagesStore.getPagesByNotebook(notebookId.value))
const currentPage = computed(() => 
  currentPageId.value ? pagesStore.pages.get(currentPageId.value) : null
)

onMounted(async () => {
  await notebooksStore.loadNotebook(notebookId.value)
  await pagesStore.loadPages(notebookId.value)
})

const selectPage = (pageId: string) => {
  router.push({
    name: 'page-view',
    params: { notebookId: notebookId.value, pageId }
  })
}

const createPage = () => {
  router.push({
    name: 'page-create',
    params: { notebookId: notebookId.value }
  })
}
</script>
```

#### Page View

```vue
<template>
  <div class="page-view">
    <header class="page-header">
      <div class="title-row">
        <h2>{{ page.title }}</h2>
        <span class="date">{{ formatDate(page.date) }}</span>
      </div>
      
      <div class="actions">
        <button @click="createEntry">New Entry</button>
        <button @click="editNarrative">Edit Narrative</button>
      </div>
    </header>
    
    <div class="narrative-section" v-if="!editingNarrative">
      <div v-for="field in narrativeFields" :key="field" class="narrative-field">
        <h3>{{ field }}</h3>
        <div v-if="page.narrative[field]" v-html="renderMarkdown(page.narrative[field])"></div>
        <p v-else class="empty">No {{ field.toLowerCase() }} yet</p>
      </div>
    </div>
    
    <div class="narrative-editor" v-else>
      <div v-for="field in narrativeFields" :key="field" class="field-editor">
        <label>{{ field }}</label>
        <MarkdownEditor 
          v-model="editedNarrative[field]"
          :placeholder="`Enter ${field.toLowerCase()}...`"
        />
      </div>
      <div class="editor-actions">
        <button @click="saveNarrative" class="primary">Save</button>
        <button @click="cancelEdit">Cancel</button>
      </div>
    </div>
    
    <div class="entries-section">
      <h3>Entries ({{ entries.length }})</h3>
      
      <div class="view-toggle">
        <button 
          :class="{ active: viewMode === 'timeline' }"
          @click="viewMode = 'timeline'"
        >
          Timeline
        </button>
        <button 
          :class="{ active: viewMode === 'grid' }"
          @click="viewMode = 'grid'"
        >
          Grid
        </button>
        <button 
          :class="{ active: viewMode === 'lineage' }"
          @click="viewMode = 'lineage'"
        >
          Lineage
        </button>
      </div>
      
      <component 
        :is="viewComponent"
        :entries="entries"
        @select="selectEntry"
        @execute="executeEntry"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { marked } from 'marked'
import { useEntriesStore } from '@/stores/entries'
import EntryTimeline from '@/components/entry/EntryTimeline.vue'
import EntryGrid from '@/components/entry/EntryGrid.vue'
import LineageGraph from '@/components/lineage/LineageGraph.vue'

const props = defineProps<{
  page: Page
}>()

const emit = defineEmits<{
  update: []
}>()

const entriesStore = useEntriesStore()

const entries = computed(() => entriesStore.getEntriesByPage(props.page.id))
const viewMode = ref<'timeline' | 'grid' | 'lineage'>('timeline')

const viewComponent = computed(() => {
  const components = {
    timeline: EntryTimeline,
    grid: EntryGrid,
    lineage: LineageGraph
  }
  return components[viewMode.value]
})

const narrativeFields = ['Goals', 'Hypothesis', 'Observations', 'Conclusions', 'Next Steps']
const editingNarrative = ref(false)
const editedNarrative = ref({})

const editNarrative = () => {
  editedNarrative.value = { ...props.page.narrative }
  editingNarrative.value = true
}

const saveNarrative = async () => {
  for (const [field, content] of Object.entries(editedNarrative.value)) {
    await api.updatePageNarrative(
      props.page.workspace.path,
      props.page.id,
      field.toLowerCase(),
      content as string
    )
  }
  editingNarrative.value = false
  emit('update')
}

const renderMarkdown = (text: string) => {
  return marked(text)
}

const createEntry = () => {
  // Navigate to entry creation
}

const selectEntry = (entryId: string) => {
  // Navigate to entry detail
}

const executeEntry = async (entryId: string) => {
  await entriesStore.executeEntry(entryId)
}
</script>
```

#### Entry Detail View

```vue
<template>
  <div class="entry-detail">
    <header class="entry-header">
      <div class="breadcrumb">
        <router-link :to="notebookLink">{{ notebook.title }}</router-link>
        <span>/</span>
        <router-link :to="pageLink">{{ page.title }}</router-link>
      </div>
      
      <h1>{{ entry.title }}</h1>
      
      <div class="meta">
        <span class="type-badge">{{ entry.entry_type }}</span>
        <span class="status" :class="entry.status">{{ entry.status }}</span>
        <span class="date">{{ formatDateTime(entry.created_at) }}</span>
      </div>
      
      <div class="actions">
        <button 
          v-if="entry.status === 'created'"
          @click="executeEntry"
          class="primary"
        >
          Execute
        </button>
        <button @click="createVariation">Create Variation</button>
        <button @click="viewLineage">View Lineage</button>
      </div>
    </header>
    
    <div class="entry-content">
      <section class="inputs-section">
        <h2>Inputs</h2>
        <pre class="code-block">{{ formatJSON(entry.inputs) }}</pre>
      </section>
      
      <section class="outputs-section" v-if="entry.outputs">
        <h2>Outputs</h2>
        <pre class="code-block">{{ formatJSON(entry.outputs) }}</pre>
      </section>
      
      <section class="artifacts-section" v-if="artifacts.length > 0">
        <h2>Artifacts ({{ artifacts.length }})</h2>
        <ArtifactGallery 
          :artifacts="artifacts"
          @select="viewArtifact"
        />
      </section>
      
      <section class="execution-section" v-if="entry.execution.started_at">
        <h2>Execution</h2>
        <div class="execution-info">
          <div class="info-row">
            <label>Started:</label>
            <span>{{ formatDateTime(entry.execution.started_at) }}</span>
          </div>
          <div class="info-row" v-if="entry.execution.completed_at">
            <label>Completed:</label>
            <span>{{ formatDateTime(entry.execution.completed_at) }}</span>
          </div>
          <div class="info-row" v-if="entry.execution.duration_seconds">
            <label>Duration:</label>
            <span>{{ entry.execution.duration_seconds }}s</span>
          </div>
          <div class="info-row" v-if="entry.execution.error">
            <label>Error:</label>
            <pre class="error-block">{{ entry.execution.error }}</pre>
          </div>
        </div>
      </section>
      
      <section class="notes-section">
        <h2>Notes</h2>
        <MarkdownEditor 
          v-model="entry.metadata.notes"
          @update="saveNotes"
          placeholder="Add notes about this entry..."
        />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useEntriesStore } from '@/stores/entries'

const route = useRoute()
const entriesStore = useEntriesStore()

const entryId = computed(() => route.params.entryId as string)
const entry = computed(() => entriesStore.entries.get(entryId.value))
const artifacts = computed(() => entriesStore.getArtifactsByEntry(entryId.value))

const executeEntry = async () => {
  await entriesStore.executeEntry(entryId.value)
}

const formatJSON = (obj: any) => {
  return JSON.stringify(obj, null, 2)
}
</script>
```

### 6.3 State Management

```typescript
// stores/entries.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Entry, Artifact } from '@/types'
import * as api from '@/api/entries'

export const useEntriesStore = defineStore('entries', () => {
  const entries = ref<Map<string, Entry>>(new Map())
  const artifacts = ref<Map<string, Artifact>>(new Map())
  
  const getEntriesByPage = (pageId: string) => {
    return Array.from(entries.value.values())
      .filter(e => e.page_id === pageId)
      .sort((a, b) => b.created_at.localeCompare(a.created_at))
  }
  
  const getArtifactsByEntry = (entryId: string) => {
    return Array.from(artifacts.value.values())
      .filter(a => a.entry_id === entryId)
  }
  
  async function loadEntry(entryId: string) {
    const entry = await api.getEntry(entryId)
    entries.value.set(entry.id, entry)
    
    // Load artifacts
    for (const artifact of entry.artifacts || []) {
      artifacts.value.set(artifact.id, artifact)
    }
    
    return entry
  }
  
  async function executeEntry(entryId: string) {
    // Create WebSocket connection for real-time updates
    const ws = new WebSocket(`ws://localhost:8765/ws/entries/${entryId}/execute`)
    
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data)
      
      if (message.type === 'completed') {
        entries.value.set(message.entry.id, message.entry)
      }
    }
    
    return new Promise((resolve, reject) => {
      ws.onerror = reject
      ws.onclose = resolve
    })
  }
  
  async function createVariation(
    entryId: string,
    title: string,
    inputOverrides: any
  ) {
    const variation = await api.createVariation(entryId, title, inputOverrides)
    entries.value.set(variation.id, variation)
    return variation
  }
  
  return {
    entries,
    artifacts,
    getEntriesByPage,
    getArtifactsByEntry,
    loadEntry,
    executeEntry,
    createVariation
  }
})
```

## 7. CLI Usage

```bash
# Initialize workspace
lab init ~/my-lab --name "My Laboratory"

# Create notebook
lab notebook create "AI Art Production" \
  --description "Exploring image generation" \
  --tags "sdxl,client-work"

# Create page
lab page create "2024-11-27 Landscape Experiments" \
  --notebook "AI Art Production" \
  --goal "Generate sunset landscapes"

# Create and execute entry
lab entry create comfyui \
  --page "2024-11-27 Landscape Experiments" \
  --title "Initial SDXL test" \
  --workflow workflow.json \
  --param prompt="a serene lake at sunset" \
  --param seed=42 \
  --execute

# Create variation
lab entry variation entry-abc123 \
  --title "Higher CFG test" \
  --override cfg=10.0

# Search entries
lab search --query "sunset" --type comfyui_workflow

# View lineage
lab lineage entry-abc123 --depth 5

# Export notebook
lab export notebook nb-abc123 --output notebook-export.zip

# Archive old artifacts
lab archive --older-than 90d --strategy thumbnail

# Start web UI
lab serve --port 8765
```

## 8. Python SDK Usage

```python
from codex import Workspace

# Initialize workspace
ws = Workspace.initialize(Path("~/my-lab"), "My Laboratory")

# Create notebook
notebook = ws.create_notebook(
    title="AI Art Production",
    description="Exploring image generation",
    tags=["sdxl", "client-work"]
)

# Create page
page = notebook.create_page(
    title="Landscape Experiments",
    date=datetime(2024, 11, 27),
    narrative={
        "goals": "Generate sunset landscapes",
        "hypothesis": "Higher CFG gives more detail"
    }
)

# Create entry
entry = page.create_entry(
    entry_type="comfyui_workflow",
    title="Initial SDXL test",
    inputs={
        "workflow_file": "workflow.json",
        "parameters": {
            "prompt": "a serene lake at sunset",
            "seed": 42,
            "cfg": 7.5
        }
    },
    tags=["initial-test"]
)

# Execute
await entry.execute()

# Create variation
variation = entry.create_variation(
    title="Higher CFG test",
    input_overrides={"parameters": {"cfg": 10.0}}
)

await variation.execute()

# Search
results = ws.search_entries(
    query="sunset",
    entry_type="comfyui_workflow",
    tags=["initial-test"]
)

# View lineage
lineage = entry.get_lineage(depth=3)
print(f"Ancestors: {len(lineage['ancestors'])}")
print(f"Descendants: {len(lineage['descendants'])}")
```

## 9. Key Features Summary

### Hierarchical Organization
- **Notebooks**: Project-level containers
- **Pages**: Session or topic-level grouping
- **Entries**: Individual experiments with full provenance

### Narrative Documentation
- Each page has structured narrative fields
- Markdown support for rich documentation
- Links thoughts to experimental results

### Lineage Tracking
- Parent-child relationships between entries
- Variation tracking
- Full DAG of experimental evolution

### Content-Addressable Storage
- Deduplication of artifacts
- Efficient storage with hashing
- Automatic thumbnail generation

### Smart Archival
- Configurable retention policies
- Compression strategies
- Keeps metadata while reducing storage

### Multi-Integration Support
- ComfyUI workflows
- API calls
- Database queries
- Custom integrations via plugin system

### Real-Time Execution
- WebSocket-based progress updates
- Streaming logs
- Live artifact generation

### AI-Powered Insights
- Summarization of pages/notebooks
- Pattern detection across entries
- Recommendation of next experiments

This architecture provides a robust foundation for a laboratory notebook system that scales from individual creative work to team-based engineering investigations.
