#!/usr/bin/env python3
"""
Seed script to populate test data for screenshots and testing.

Creates test users with sample workspaces, notebooks, and markdown files
via the HTTP API. The server must be running.

The 'clean' subcommand also uses the HTTP API (DELETE endpoints).

Usage:
    python -m codex.scripts.seed_test_data          # seed via API
    python -m codex.scripts.seed_test_data clean     # clean via API
"""

import sys

import httpx

from codex.scripts.user_manager import get_base_url, get_token, register_user

# Test user credentials (documented for easy reference)
TEST_USERS = [
    {
        "username": "demo",
        "email": "demo@example.com",
        "password": "demo123456",
        "workspaces": [
            {
                "name": "Machine Learning Lab",
                "notebooks": [
                    {
                        "name": "Neural Networks",
                        "description": "Experiments with deep learning models",
                        "files": [
                            {
                                "name": "transformer-experiments.md",
                                "content": """---
title: Transformer Model Experiments
tags: [deep-learning, transformers, nlp]
date: 2024-01-15
---

# Transformer Model Experiments

## Overview

Investigating the performance of various transformer architectures on text classification tasks.

## Setup

```python
import torch
from transformers import AutoModel, AutoTokenizer

model_name = "bert-base-uncased"
model = AutoModel.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)
```

## Experiments

### Experiment 1: Baseline Performance
- Model: BERT-base
- Dataset: IMDB reviews
- Accuracy: 92.3%

### Experiment 2: Fine-tuned Model
- Epochs: 3
- Learning rate: 2e-5
- Accuracy: 94.8%

## Conclusions

Fine-tuning significantly improved performance. Next steps: try larger models.
""",
                            },
                            {
                                "name": "cnn-architectures.md",
                                "content": """---
title: CNN Architecture Comparison
tags: [computer-vision, cnn, pytorch]
date: 2024-01-20
---

# CNN Architecture Comparison

Comparing different CNN architectures for image classification.

## Models Tested

1. ResNet-50
2. EfficientNet-B0
3. MobileNetV2

## Results

| Model | Accuracy | Parameters | Inference Time |
|-------|----------|------------|----------------|
| ResNet-50 | 95.2% | 25M | 45ms |
| EfficientNet-B0 | 96.1% | 5M | 28ms |
| MobileNetV2 | 93.8% | 3.5M | 18ms |

## Winner: EfficientNet-B0

Best balance of accuracy and efficiency.
""",
                            },
                        ],
                    },
                    {
                        "name": "Data Analysis",
                        "description": "Statistical analysis and visualization",
                        "files": [
                            {
                                "name": "exploratory-analysis.md",
                                "content": """---
title: Exploratory Data Analysis
tags: [data-science, statistics, visualization]
date: 2024-01-18
---

# Exploratory Data Analysis

## Dataset

Customer purchase behavior dataset with 50k samples.

## Key Findings

1. **Age Distribution**: Bimodal distribution with peaks at 25-35 and 45-55
2. **Purchase Patterns**: Strong correlation between income and purchase frequency
3. **Seasonal Trends**: 40% increase in purchases during Q4

## Visualizations

Created scatter plots, histograms, and correlation matrices.

## Next Steps

- Build predictive model
- Test feature importance
- Create customer segmentation
""",
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123",
        "workspaces": [
            {
                "name": "Test Workspace",
                "notebooks": [
                    {
                        "name": "Sample Notebook",
                        "description": "A simple test notebook",
                        "files": [
                            {
                                "name": "getting-started.md",
                                "content": """---
title: Getting Started
tags: [test, documentation]
date: 2024-01-10
---

# Getting Started

This is a test notebook for validation purposes.

## Features

- Markdown support
- Code blocks
- Tags and metadata

## Example Code

```javascript
console.log("Hello, Codex!");
```

That's it!
""",
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "username": "scientist",
        "email": "scientist@example.com",
        "password": "lab123456",
        "workspaces": [
            {
                "name": "Research Lab",
                "notebooks": [
                    {
                        "name": "Chemistry Experiments",
                        "description": "Chemical reaction studies",
                        "files": [
                            {
                                "name": "synthesis-protocols.md",
                                "content": """---
title: Organic Synthesis Protocols
tags: [chemistry, synthesis, protocols]
date: 2024-01-12
---

# Organic Synthesis Protocols

## Protocol 1: Esterification Reaction

### Materials
- Acetic acid (5 mL)
- Ethanol (10 mL)
- Concentrated H\u2082SO\u2084 (1 mL, catalyst)

### Procedure
1. Mix acetic acid and ethanol in round-bottom flask
2. Add catalyst dropwise while stirring
3. Heat under reflux for 2 hours at 70\u00b0C
4. Cool and neutralize with NaHCO\u2083
5. Extract product with dichloromethane

### Results
- Yield: 78%
- Purity: 95% (by GC-MS)

## Safety Notes

Always work in fume hood. Wear appropriate PPE.
""",
                            },
                            {
                                "name": "spectroscopy-data.md",
                                "content": """---
title: Spectroscopy Analysis
tags: [spectroscopy, nmr, ir]
date: 2024-01-14
---

# Spectroscopy Analysis

## NMR Data

Sample: Ethyl acetate
Solvent: CDCl\u2083

### \u00b9H NMR
- \u03b4 1.26 (t, 3H, CH\u2083)
- \u03b4 2.04 (s, 3H, CH\u2083CO)
- \u03b4 4.12 (q, 2H, OCH\u2082)

### \u00b9\u00b3C NMR
- \u03b4 14.2 (CH\u2083)
- \u03b4 20.9 (CH\u2083CO)
- \u03b4 60.3 (OCH\u2082)
- \u03b4 171.0 (C=O)

## IR Data

Key peaks:
- 1740 cm\u207b\u00b9 (C=O stretch)
- 1240 cm\u207b\u00b9 (C-O stretch)

## Conclusion

Structure confirmed as ethyl acetate.
""",
                            },
                        ],
                    },
                    {
                        "name": "Biology Lab",
                        "description": "Cell culture and microscopy",
                        "files": [
                            {
                                "name": "cell-culture-log.md",
                                "content": """---
title: Cell Culture Log
tags: [biology, cell-culture, hela]
date: 2024-01-16
---

# Cell Culture Log

## HeLa Cell Line Maintenance

### Week 1 (Jan 8-14)

**Day 1**: Thawed frozen stock
- Initial density: 1x10\u2076 cells/mL
- Viability: 92%

**Day 3**: First passage
- Confluency: 80%
- Split ratio: 1:3
- New density: 3x10\u2075 cells/mL

**Day 6**: Second passage
- Confluency: 85%
- Split ratio: 1:4
- Morphology: Normal epithelial appearance

### Observations

Cells showing healthy growth and expected morphology. No contamination detected.

### Next Steps

- Prepare cells for transfection experiment
- Test new culture medium formulation
""",
                            },
                        ],
                    },
                ],
            },
        ],
    },
]


def _log(msg: str) -> None:
    """Print informational message to stderr."""
    print(msg, file=sys.stderr)


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _find_by_name(items: list[dict], name: str) -> dict | None:
    """Find an item in a list of dicts by its 'name' key."""
    for item in items:
        if item.get("name") == name:
            return item
    return None


def seed_data() -> None:
    """Create test users, workspaces, notebooks, and files via the HTTP API."""
    base_url = get_base_url()

    # Health check
    try:
        r = httpx.get(f"{base_url}/health")
        r.raise_for_status()
    except httpx.ConnectError:
        _log(f"Cannot connect to {base_url}. Is the server running?")
        sys.exit(1)

    _log("Starting test data seeding...")

    for user_data in TEST_USERS:
        username = user_data["username"]

        # Register user (idempotent: 400 means already exists)
        try:
            register_user(base_url, username, user_data["email"], user_data["password"])
            _log(f"  Created user: {username}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                _log(f"  User '{username}' already exists, continuing...")
            else:
                _log(f"  Registration failed for {username}: {e.response.text}")
                continue

        # Get token
        try:
            token = get_token(base_url, username, user_data["password"])
        except httpx.HTTPStatusError as e:
            _log(f"  Cannot authenticate as {username}: {e.response.text}")
            continue

        headers = _auth_headers(token)

        # List existing workspaces for idempotency
        existing_workspaces = httpx.get(f"{base_url}/api/v1/workspaces/", headers=headers).json()

        for ws_data in user_data["workspaces"]:
            ws_name = ws_data["name"]

            # Check if workspace already exists
            existing_ws = _find_by_name(existing_workspaces, ws_name)
            if existing_ws:
                _log(f"    Workspace '{ws_name}' already exists, reusing...")
                ws_id = existing_ws["id"]
            else:
                r = httpx.post(
                    f"{base_url}/api/v1/workspaces/",
                    headers=headers,
                    json={"name": ws_name},
                )
                if not r.is_success:
                    _log(f"    Failed to create workspace '{ws_name}': {r.text}")
                    continue
                ws = r.json()
                ws_id = ws["id"]
                _log(f"    Created workspace: {ws_name}")

            # List existing notebooks in this workspace
            existing_notebooks = httpx.get(
                f"{base_url}/api/v1/workspaces/{ws_id}/notebooks/",
                headers=headers,
            ).json()

            for nb_data in ws_data["notebooks"]:
                nb_name = nb_data["name"]

                existing_nb = _find_by_name(existing_notebooks, nb_name)
                if existing_nb:
                    _log(f"      Notebook '{nb_name}' already exists, reusing...")
                    nb_slug = existing_nb["slug"]
                else:
                    r = httpx.post(
                        f"{base_url}/api/v1/workspaces/{ws_id}/notebooks/",
                        headers=headers,
                        json={"name": nb_name, "description": nb_data.get("description")},
                    )
                    if not r.is_success:
                        _log(f"      Failed to create notebook '{nb_name}': {r.text}")
                        continue
                    nb = r.json()
                    nb_slug = nb["slug"]
                    _log(f"      Created notebook: {nb_name}")

                # Create files
                for file_data in nb_data.get("files", []):
                    r = httpx.post(
                        f"{base_url}/api/v1/workspaces/{ws_id}/notebooks/{nb_slug}/files/",
                        headers=headers,
                        json={"path": file_data["name"], "content": file_data["content"]},
                    )
                    if r.is_success:
                        _log(f"        Created file: {file_data['name']}")
                    else:
                        _log(f"        File '{file_data['name']}': {r.status_code} (may already exist)")

    _log("\nTest data seeding complete!")
    _log("\nTest User Credentials:")
    _log("=" * 50)
    for user_data in TEST_USERS:
        _log(f"Username: {user_data['username']}")
        _log(f"Password: {user_data['password']}")
        _log(f"Email: {user_data['email']}")
        _log("-" * 50)


def clean_test_data() -> None:
    """Remove all test data (users, workspaces, notebooks) via the HTTP API.

    For each test user: authenticates, deletes all workspaces (which cascades
    to notebooks and files), then deletes the user account.
    The server must be running.
    """
    base_url = get_base_url()

    # Health check
    try:
        r = httpx.get(f"{base_url}/health")
        r.raise_for_status()
    except httpx.ConnectError:
        _log(f"Cannot connect to {base_url}. Is the server running?")
        sys.exit(1)

    _log("Starting test data cleanup...")

    for user_data in TEST_USERS:
        username = user_data["username"]

        # Authenticate
        try:
            token = get_token(base_url, username, user_data["password"])
        except httpx.HTTPStatusError:
            _log(f"  User '{username}' not found or bad password, skipping...")
            continue

        headers = _auth_headers(token)

        # List and delete all workspaces (cascades to notebooks, files, etc.)
        try:
            workspaces = httpx.get(f"{base_url}/api/v1/workspaces/", headers=headers).json()
        except Exception as e:
            _log(f"  Failed to list workspaces for {username}: {e}")
            continue

        for ws in workspaces:
            ws_id = ws["id"]
            ws_name = ws.get("name", ws_id)
            r = httpx.delete(f"{base_url}/api/v1/workspaces/{ws_id}", headers=headers)
            if r.is_success:
                _log(f"  Deleted workspace: {ws_name}")
            else:
                _log(f"  Failed to delete workspace '{ws_name}': {r.status_code} {r.text}")

        # Delete the user account
        r = httpx.delete(f"{base_url}/api/v1/users/me", headers=headers)
        if r.is_success:
            _log(f"Deleted user: {username}")
        else:
            _log(f"Failed to delete user '{username}': {r.status_code} {r.text}")

    _log("\nTest data cleanup complete!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        clean_test_data()
    else:
        seed_data()
