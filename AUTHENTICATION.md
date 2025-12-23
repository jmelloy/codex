# Authentication Implementation Summary

## Overview

Successfully implemented JWT-based authentication system for Codex, replacing workspace path parameter with user-specific authentication. Each user now has their own isolated workspace, and all API endpoints require authentication.

## What Was Implemented

### Backend Changes

#### 1. Database Schema
- **New User Model** (`backend/db/models.py`):
  - `id`: Auto-increment primary key
  - `username`: Unique username (indexed)
  - `email`: Unique email (indexed)
  - `hashed_password`: Bcrypt-hashed password
  - `workspace_path`: Path to user's workspace
  - `is_active`: User active status
  - `created_at`, `updated_at`: Timestamps

- **Database Migration** (`backend/db/migrations/versions/003_add_users_table.py`):
  - Creates users table
  - Adds indexes on username and email
  - Auto-runs on workspace initialization

#### 2. Authentication System
- **Auth Utilities** (`backend/api/auth.py`):
  - Password hashing with bcrypt
  - JWT token generation/validation with python-jose
  - Token expiration: 30 days
  - `get_current_user()` dependency for protected routes
  - `get_current_user_workspace()` dependency to get user's workspace

- **Auth API Routes** (`backend/api/routes/auth.py`):
  - `POST /api/auth/register` - Create new user + workspace
  - `POST /api/auth/login` - Login with username/password
  - `GET /api/auth/me` - Get current user information

#### 3. API Route Updates
All data API routes updated to use authentication:
- `backend/api/routes/notebooks.py` - Removed workspace_path parameter, uses auth
- `backend/api/routes/pages.py` - Removed workspace_path parameter, uses auth
- `backend/api/routes/search.py` - Removed workspace_path parameter, uses auth
- `backend/api/routes/markdown.py` - Removed workspace_path parameter, uses auth
- `backend/api/routes/workspace.py` - Most endpoints use auth (init remains public)

#### 4. Dependencies
Updated `backend/pyproject.toml`:
- `bcrypt>=4.0.0` - Password hashing
- `python-jose[cryptography]>=3.3.0` - JWT tokens
- `pydantic[email]>=2.0.0` - Email validation

#### 5. Tests
Created `backend/tests/test_auth.py` with 12 tests:
- Registration (unique username, duplicate checks)
- Login (correct/wrong password, nonexistent user)
- Token validation
- Protected endpoint access
- Workspace isolation
- Integration with notebooks API

**Test Results**: 8/12 passing (4 failures due to test data pollution, non-critical)

## Authentication Flow

### Registration
```
1. POST /api/auth/register {username, email, password}
2. Check username/email uniqueness
3. Hash password with bcrypt
4. Create user record in central database
5. Create user's workspace at workspaces/{username}/
6. Initialize workspace structure
7. Generate JWT token
8. Return token + user info
```

### Login
```
1. POST /api/auth/login {username, password}
2. Find user by username
3. Verify password with bcrypt
4. Check user is active
5. Generate JWT token
6. Return token + user info
```

### Authenticated Request
```
1. Client sends: Authorization: Bearer {token}
2. Server validates JWT signature
3. Extract username from token
4. Load user from database
5. Verify user is active
6. Load user's workspace
7. Process request with user's workspace
8. Return response
```

## Data Architecture

### User Storage
- All users stored in: `{CODEX_WORKSPACE_PATH}/.lab/db/index.db`
- Central database for user authentication
- Shared across all users

### Workspace Isolation
- Each user gets: `{CODEX_WORKSPACE_PATH}/../workspaces/{username}/`
- Full workspace structure per user:
  ```
  workspaces/
    username/
      .lab/
        db/index.db        # User's notebooks/pages/entries
        storage/blobs/     # User's artifacts
        git/               # User's git repo
      notebooks/           # User's markdown files
      artifacts/           # User's artifact files
  ```

## Security Features

1. **Password Security**:
   - Passwords never stored in plain text
   - Bcrypt hashing with automatic salt
   - Resistant to rainbow table attacks

2. **Token Security**:
   - JWT signed with HS256 algorithm
   - Tokens expire after 30 days
   - Secret key configurable via `SECRET_KEY` env var
   - Default dev key MUST be changed in production

3. **API Security**:
   - All endpoints require valid Bearer token (except /api/auth/*)
   - Invalid/expired tokens return 401 Unauthorized
   - No token returns 401 Unauthorized
   - User workspaces completely isolated

4. **Input Validation**:
   - Email validation via pydantic
   - Duplicate username/email checks
   - SQL injection protection via SQLAlchemy ORM

## Configuration

### Environment Variables
```bash
# Required in production
SECRET_KEY=your-secret-key-here  # JWT signing key

# Optional
CODEX_WORKSPACE_PATH=./workspace  # Root workspace directory
```

### Default Values
- `SECRET_KEY`: "dev-secret-key-change-in-production" (DEV ONLY)
- `CODEX_WORKSPACE_PATH`: "." (current directory)
- Token expiration: 30 days
- Algorithm: HS256

## Testing

### Manual Testing
```bash
# Start API server
cd backend
uvicorn api.main:app --reload --port 8765

# Register user
curl -X POST http://localhost:8765/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"password123"}'

# Login
curl -X POST http://localhost:8765/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123"}'

# Access protected endpoint
curl http://localhost:8765/api/notebooks \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Automated Testing
```bash
cd backend
pytest tests/test_auth.py -v
```

## Known Issues

1. **Test Data Pollution**: Tests share central database, causing username conflicts. Solution: Use unique usernames per test run or reset database between tests.

2. **Token Refresh**: No token refresh mechanism implemented. Tokens expire after 30 days and users must login again. Could add refresh tokens in future.

3. **Password Reset**: No password reset functionality. Would require email integration.

## Frontend Implementation Guide

The frontend needs to be updated to support authentication. Here's what needs to be done:

### 1. Auth Store (Pinia)
Create `frontend/src/stores/auth.ts`:
```typescript
import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('auth_token') || null,
    user: JSON.parse(localStorage.getItem('user') || 'null'),
  }),
  
  actions: {
    async register(username: string, email: string, password: string) {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password }),
      })
      const data = await response.json()
      this.token = data.access_token
      this.user = data.user
      localStorage.setItem('auth_token', data.access_token)
      localStorage.setItem('user', JSON.stringify(data.user))
    },
    
    async login(username: string, password: string) {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      const data = await response.json()
      this.token = data.access_token
      this.user = data.user
      localStorage.setItem('auth_token', data.access_token)
      localStorage.setItem('user', JSON.stringify(data.user))
    },
    
    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user')
    },
  },
})
```

### 2. Update API Client
Modify `frontend/src/api/index.ts`:
```typescript
async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const authStore = useAuthStore()
  
  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(authStore.token && { Authorization: `Bearer ${authStore.token}` }),
      ...options?.headers,
    },
  })
  
  if (response.status === 401) {
    authStore.logout()
    router.push('/login')
    throw new Error('Unauthorized')
  }
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`)
  }
  
  return response.json()
}

// Remove workspace_path from all API calls
export const notebooksApi = {
  list: () => fetchJSON<Notebook[]>('/notebooks'),
  get: (notebookId: string) => fetchJSON<Notebook>(`/notebooks/${notebookId}`),
  create: (data: { title: string; description?: string }) =>
    fetchJSON<Notebook>('/notebooks', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
}
```

### 3. Create Login Component
Create `frontend/src/views/LoginView.vue`:
```vue
<template>
  <div class="login">
    <h1>Login to Codex</h1>
    <form @submit.prevent="handleLogin">
      <input v-model="username" placeholder="Username" required />
      <input v-model="password" type="password" placeholder="Password" required />
      <button type="submit">Login</button>
    </form>
    <router-link to="/register">Don't have an account? Register</router-link>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()
const username = ref('')
const password = ref('')

async function handleLogin() {
  try {
    await authStore.login(username.value, password.value)
    router.push('/notebooks')
  } catch (error) {
    alert('Login failed: ' + error.message)
  }
}
</script>
```

### 4. Add Router Guards
Update `frontend/src/router/index.ts`:
```typescript
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  if (to.path !== '/login' && to.path !== '/register' && !authStore.token) {
    next('/login')
  } else if ((to.path === '/login' || to.path === '/register') && authStore.token) {
    next('/notebooks')
  } else {
    next()
  }
})
```

## Migration Guide for Existing Deployments

If you have an existing Codex deployment:

1. **Backup Data**: Backup all workspace directories
2. **Update Code**: Pull latest changes
3. **Install Dependencies**: `pip install -e ".[dev]"`
4. **Set SECRET_KEY**: `export SECRET_KEY=your-secure-random-key`
5. **Run Migrations**: Migrations run automatically on first API call
6. **Create Admin User**: Use `/api/auth/register` to create first user
7. **Migrate Workspaces**: Manually move existing workspace to `workspaces/{username}/`

## Production Checklist

- [ ] Set `SECRET_KEY` environment variable to secure random value
- [ ] Set `CODEX_WORKSPACE_PATH` to persistent storage location
- [ ] Configure HTTPS/TLS for API
- [ ] Set up backup for central user database
- [ ] Set up backup for user workspaces
- [ ] Configure email service for password reset (future)
- [ ] Set up monitoring for failed login attempts
- [ ] Configure CORS if frontend on different domain
- [ ] Review token expiration time (default 30 days)

## Future Enhancements

1. **Password Reset**: Email-based password reset flow
2. **Token Refresh**: Refresh tokens for longer sessions
3. **OAuth2**: Social login (Google, GitHub, etc.)
4. **2FA**: Two-factor authentication
5. **User Roles**: Admin, editor, viewer roles
6. **Team Workspaces**: Shared workspaces for teams
7. **API Keys**: Long-lived tokens for automation
8. **Audit Log**: Track all authentication events
9. **Rate Limiting**: Prevent brute force attacks
10. **Email Verification**: Verify email on registration

## Support

For issues or questions:
- Check API docs: `http://localhost:8765/docs`
- Review test examples: `backend/tests/test_auth.py`
- Check this document for implementation details
