#!/usr/bin/env python3
"""
Seed script to populate test data for screenshots and testing.

Creates test users with sample workspaces, notebooks, and markdown files.
This makes it easy to test the application and take screenshots past the login page.

Usage:
    python -m codex.scripts.seed_test_data
"""

import asyncio
import os
from pathlib import Path
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_password_hash
from codex.db.database import get_system_session, init_system_db, init_notebook_db, DATA_DIRECTORY
from codex.db.models import User, Workspace, Notebook
from codex.core.git_manager import GitManager


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
- Concentrated H₂SO₄ (1 mL, catalyst)

### Procedure
1. Mix acetic acid and ethanol in round-bottom flask
2. Add catalyst dropwise while stirring
3. Heat under reflux for 2 hours at 70°C
4. Cool and neutralize with NaHCO₃
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
Solvent: CDCl₃

### ¹H NMR
- δ 1.26 (t, 3H, CH₃)
- δ 2.04 (s, 3H, CH₃CO)
- δ 4.12 (q, 2H, OCH₂)

### ¹³C NMR
- δ 14.2 (CH₃)
- δ 20.9 (CH₃CO)
- δ 60.3 (OCH₂)
- δ 171.0 (C=O)

## IR Data

Key peaks:
- 1740 cm⁻¹ (C=O stretch)
- 1240 cm⁻¹ (C-O stretch)

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
- Initial density: 1x10⁶ cells/mL
- Viability: 92%

**Day 3**: First passage
- Confluency: 80%
- Split ratio: 1:3
- New density: 3x10⁵ cells/mL

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


def slugify(name: str) -> str:
    """Convert a name to a filesystem-safe slug."""
    import re

    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug or "item"


async def create_markdown_file(notebook_path: Path, filename: str, content: str):
    """Create a markdown file in the notebook."""
    file_path = notebook_path / filename
    file_path.write_text(content)


async def seed_data():
    """Create test users, workspaces, notebooks, and files."""
    print("🌱 Starting test data seeding...")

    # Initialize the system database
    await init_system_db()

    async for session in get_system_session():
        try:
            for user_data in TEST_USERS:
                # Check if user already exists
                result = await session.execute(select(User).where(User.username == user_data["username"]))
                existing_user = result.scalar_one_or_none()

                if existing_user:
                    print(f"⏭️  User '{user_data['username']}' already exists, skipping...")
                    continue

                # Create user
                hashed_password = get_password_hash(user_data["password"])
                user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    hashed_password=hashed_password,
                    is_active=True,
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
                print(f"✅ Created user: {user.username} (password: {user_data['password']})")

                # Create workspaces for this user
                for workspace_data in user_data["workspaces"]:
                    workspace_slug = slugify(workspace_data["name"])
                    base_path = Path(DATA_DIRECTORY) / "workspaces"
                    workspace_path = base_path / f"{user.username}-{workspace_slug}"

                    # Create workspace directory
                    workspace_path.mkdir(parents=True, exist_ok=True)

                    workspace = Workspace(
                        name=workspace_data["name"], path=str(workspace_path), owner_id=user.id, theme_setting="cream"
                    )
                    session.add(workspace)
                    await session.commit()
                    await session.refresh(workspace)
                    print(f"  📁 Created workspace: {workspace.name}")

                    # Create notebooks in this workspace
                    for notebook_data in workspace_data["notebooks"]:
                        notebook_slug = slugify(notebook_data["name"])
                        notebook_path = workspace_path / notebook_slug

                        # Create notebook directory
                        notebook_path.mkdir(parents=True, exist_ok=True)

                        # Initialize notebook database
                        init_notebook_db(str(notebook_path))

                        # Initialize Git repository
                        git_manager = GitManager(str(notebook_path))

                        # Create notebook record
                        notebook = Notebook(
                            workspace_id=workspace.id,
                            name=notebook_data["name"],
                            path=notebook_slug,
                            description=notebook_data.get("description"),
                        )
                        session.add(notebook)
                        await session.commit()
                        await session.refresh(notebook)
                        print(f"    📓 Created notebook: {notebook.name}")

                        # Create markdown files
                        for file_data in notebook_data.get("files", []):
                            await create_markdown_file(notebook_path, file_data["name"], file_data["content"])
                            print(f"      📄 Created file: {file_data['name']}")

                        # Git commit the files
                        try:
                            git_manager.commit_all("Initial notebook setup with sample data")
                        except Exception as e:
                            print(f"      ⚠️  Git commit failed (this is okay): {e}")

            print("\n🎉 Test data seeding complete!")
            print("\n📋 Test User Credentials:")
            print("=" * 50)
            for user_data in TEST_USERS:
                print(f"Username: {user_data['username']}")
                print(f"Password: {user_data['password']}")
                print(f"Email: {user_data['email']}")
                print("-" * 50)

        except Exception as e:
            print(f"❌ Error during seeding: {e}")
            raise
        finally:
            break  # Exit the async generator after one iteration


async def clean_test_data():
    """Remove all test data (users, workspaces, notebooks)."""
    print("🧹 Cleaning test data...")

    await init_system_db()

    async for session in get_system_session():
        try:
            # Delete test users (cascading deletes will handle workspaces)
            for user_data in TEST_USERS:
                result = await session.execute(select(User).where(User.username == user_data["username"]))
                user = result.scalar_one_or_none()

                if user:
                    # Get user's workspaces to delete directories
                    result = await session.execute(select(Workspace).where(Workspace.owner_id == user.id))
                    workspaces = result.scalars().all()

                    for workspace in workspaces:
                        workspace_path = Path(workspace.path)
                        if workspace_path.exists():
                            import shutil

                            shutil.rmtree(workspace_path)
                            print(f"  🗑️  Deleted workspace directory: {workspace_path}")

                    # Delete user (cascading will delete workspaces and notebooks)
                    await session.delete(user)
                    print(f"✅ Deleted user: {user.username}")

            await session.commit()
            print("\n🎉 Test data cleanup complete!")

        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            raise
        finally:
            break


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        asyncio.run(clean_test_data())
    else:
        asyncio.run(seed_data())
