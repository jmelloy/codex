# Test Data for Codex

This directory contains scripts and documentation for managing test data in Codex.

## Test User Credentials

The following test users are created by the `seed_test_data.py` script:

### Demo User (Full Featured)
- **Username**: `demo`
- **Password**: `demo123456`
- **Email**: `demo@example.com`
- **Workspaces**: Machine Learning Lab
  - Neural Networks notebook with transformer and CNN experiments
  - Data Analysis notebook with exploratory analysis

### Test User (Simple)
- **Username**: `testuser`
- **Password**: `testpass123`
- **Email**: `test@example.com`
- **Workspaces**: Test Workspace
  - Sample Notebook with getting started guide

### Scientist User (Research Focused)
- **Username**: `scientist`
- **Password**: `lab123456`
- **Email**: `scientist@example.com`
- **Workspaces**: Research Lab
  - Chemistry Experiments with synthesis protocols
  - Biology Lab with cell culture logs

## Usage

### Seed Test Data

Run this command to create test users and sample data:

```bash
python -m backend.scripts.seed_test_data
```

This will:
1. Create the test users listed above
2. Create workspaces for each user
3. Create notebooks with sample content
4. Initialize Git repositories for each notebook
5. Print the credentials for easy reference

### Clean Test Data

To remove all test users and their data:

```bash
python -m backend.scripts.seed_test_data clean
```

This will:
1. Delete all test users from the database
2. Remove workspace directories and all files
3. Clean up any associated data

## Use Cases

### Taking Screenshots

Use the demo user to take screenshots of the application with realistic data:

```bash
# Start the backend
uvicorn backend.api.main:app --reload --port 8000

# In another terminal, start frontend
cd frontend
npm run dev

# Navigate to http://localhost:5173
# Login with demo/demo123456
# Take screenshots of various pages
```

### Testing Authentication Flow

Use the testuser account for basic authentication testing:

```python
import requests

response = requests.post(
    "http://localhost:8000/token",
    data={"username": "testuser", "password": "testpass123"}
)
token = response.json()["access_token"]
```

### Integration Testing

The test users provide a consistent baseline for integration tests:

```python
# Test that notebooks are properly created
response = requests.get(
    "http://localhost:8000/workspaces/1/notebooks",
    headers={"Authorization": f"Bearer {token}"}
)
assert len(response.json()) > 0
```

## Notes

- Test data is **idempotent**: Running the seed script multiple times will skip existing users
- Credentials are intentionally simple for testing purposes
- **Do not use these credentials in production**
- The seed script creates realistic markdown content for better screenshots
- All notebooks include Git initialization with initial commits

## Updating Test Data

To modify the test data structure:

1. Edit `seed_test_data.py`
2. Update the `TEST_USERS` dictionary
3. Run the clean command to remove old data
4. Run the seed command to create new data

## Directory Structure

After seeding, the data directory will contain:

```
data/workspaces/
├── demo-machine-learning-lab/
│   ├── neural-networks/
│   │   ├── .git/
│   │   ├── .codex/
│   │   ├── transformer-experiments.md
│   │   └── cnn-architectures.md
│   └── data-analysis/
│       ├── .git/
│       ├── .codex/
│       └── exploratory-analysis.md
├── testuser-test-workspace/
│   └── sample-notebook/
│       ├── .git/
│       ├── .codex/
│       └── getting-started.md
└── scientist-research-lab/
    ├── chemistry-experiments/
    │   ├── .git/
    │   ├── .codex/
    │   ├── synthesis-protocols.md
    │   └── spectroscopy-data.md
    └── biology-lab/
        ├── .git/
        ├── .codex/
        └── cell-culture-log.md
```
