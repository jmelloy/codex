# Test User Credentials

This document lists the test user accounts available in the Codex system for testing, screenshots, and demonstrations.

## How to Create Test Users

Run the seed script to create test users with sample data:

```bash
python -m backend.scripts.seed_test_data
```

This creates 3 test users with workspaces, notebooks, and markdown files containing realistic content.

## Test User Accounts

### 1. Demo User (Full Featured)

**Purpose**: Main demonstration account with rich sample data for screenshots and demos.

- **Username**: `demo`
- **Password**: `demo123456`
- **Email**: `demo@example.com`

**Workspaces**:
- **Machine Learning Lab**
  - Neural Networks notebook
    - `transformer-experiments.md` - Transformer model experiments with code examples
    - `cnn-architectures.md` - CNN architecture comparison with results table
  - Data Analysis notebook
    - `exploratory-analysis.md` - EDA with statistical findings

**Use Cases**:
- Taking product screenshots
- Demo presentations
- Feature validation with realistic data
- UI/UX testing

---

### 2. Test User (Simple)

**Purpose**: Minimal test account for basic validation and testing.

- **Username**: `testuser`
- **Password**: `testpass123`
- **Email**: `test@example.com`

**Workspaces**:
- **Test Workspace**
  - Sample Notebook
    - `getting-started.md` - Basic getting started guide

**Use Cases**:
- Quick authentication testing
- Basic functionality validation
- Integration testing baseline
- Minimal data scenario testing

---

### 3. Scientist User (Research Focused)

**Purpose**: Scientific research demonstration with lab notebook content.

- **Username**: `scientist`
- **Password**: `lab123456`
- **Email**: `scientist@example.com`

**Workspaces**:
- **Research Lab**
  - Chemistry Experiments notebook
    - `synthesis-protocols.md` - Organic synthesis protocols with procedures
    - `spectroscopy-data.md` - NMR and IR spectroscopy analysis
  - Biology Lab notebook
    - `cell-culture-log.md` - HeLa cell culture maintenance log

**Use Cases**:
- Scientific research use case demos
- Lab notebook workflow demonstrations
- Domain-specific content validation

---

## Using Test Accounts

### Web Interface

1. Navigate to http://localhost:5173 (or your deployed URL)
2. Click "Login"
3. Enter username and password from the list above
4. Explore workspaces and notebooks

### API Testing

```bash
# Get access token
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo&password=demo123456"

# Use token to access protected endpoints
curl -X GET http://localhost:8000/api/v1/workspaces/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Automated Testing

```python
import requests

# Login
response = requests.post(
    "http://localhost:8000/token",
    data={"username": "testuser", "password": "testpass123"}
)
token = response.json()["access_token"]

# Get user info
user_response = requests.get(
    "http://localhost:8000/users/me",
    headers={"Authorization": f"Bearer {token}"}
)
print(user_response.json())
```

---

## Cleaning Test Data

To remove all test users and their data:

```bash
python -m backend.scripts.seed_test_data clean
```

This will:
- Delete all test user accounts from the database
- Remove all workspace directories and files
- Clean up associated data

**Note**: This is safe to run - it only removes the specific test users listed in this document.

---

## Important Notes

- ⚠️ **Do not use these credentials in production environments**
- Test data is idempotent - re-running the seed script will skip existing users
- Passwords are intentionally simple for testing purposes
- All notebooks include Git initialization with initial commits
- Markdown files include frontmatter metadata (title, tags, date)
- Content is realistic to provide better context for screenshots and demos

---

## Adding More Test Users

To add additional test users, edit `backend/scripts/seed_test_data.py` and add entries to the `TEST_USERS` list:

```python
{
    "username": "newuser",
    "email": "newuser@example.com",
    "password": "password123",
    "workspaces": [
        {
            "name": "My Workspace",
            "notebooks": [
                {
                    "name": "My Notebook",
                    "description": "Description here",
                    "files": [
                        {
                            "name": "example.md",
                            "content": "..."
                        }
                    ]
                }
            ]
        }
    ]
}
```

Then run the seed script to create the new user.

---

## Security Considerations

- Test users are for **development and testing only**
- Never commit real credentials to version control
- In production, use strong passwords and proper authentication
- Consider using environment variables for test credentials in CI/CD
- The seed script stores passwords using the same PBKDF2 hashing as production users
