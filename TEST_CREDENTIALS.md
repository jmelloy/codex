# Test User Credentials

Test user accounts for development, testing, and screenshots.

## Creating Test Users

```bash
python -m codex.scripts.seed_test_data
```

## Test Accounts

### Demo User (Full Featured)

- **Username**: `demo` / **Password**: `demo123456`
- **Email**: `demo@example.com`
- **Purpose**: Main demo account with rich sample data for screenshots

### Test User (Simple)

- **Username**: `testuser` / **Password**: `testpass123`
- **Email**: `test@example.com`
- **Purpose**: Minimal test account for basic validation

### Scientist User (Research)

- **Username**: `scientist` / **Password**: `lab123456`
- **Email**: `scientist@example.com`
- **Purpose**: Scientific research demonstration with lab notebook content

## Usage

### Web Interface

1. Navigate to http://localhost:5173
2. Login with credentials above

### API Testing

```bash
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo&password=demo123456"
```

## Cleanup

```bash
python -m codex.scripts.seed_test_data clean
```

⚠️ **For development/testing only** - Do not use in production
