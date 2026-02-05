#!/usr/bin/env bash
#
# Integration tests for Codex running in Docker.
# Expects BACKEND_URL and FRONTEND_URL environment variables.
#
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://localhost:8765}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:8065}"

PASSED=0
FAILED=0
TOTAL=0

# --- helpers ---

pass_test() {
  PASSED=$((PASSED + 1))
  TOTAL=$((TOTAL + 1))
  echo "  PASS: $1"
}

fail_test() {
  FAILED=$((FAILED + 1))
  TOTAL=$((TOTAL + 1))
  echo "  FAIL: $1"
  if [ -n "${2:-}" ]; then
    echo "        $2"
  fi
}

assert_status() {
  local description="$1"
  local expected="$2"
  local actual="$3"
  if [ "$actual" -eq "$expected" ]; then
    pass_test "$description"
  else
    fail_test "$description" "expected HTTP $expected, got $actual"
  fi
}

assert_json_field() {
  local description="$1"
  local json="$2"
  local field="$3"
  local expected="$4"
  local actual
  actual=$(echo "$json" | python3 -c "import sys,json; print(json.load(sys.stdin)$field)" 2>/dev/null || echo "__PARSE_ERROR__")
  if [ "$actual" = "$expected" ]; then
    pass_test "$description"
  else
    fail_test "$description" "expected '$expected', got '$actual'"
  fi
}

assert_json_field_exists() {
  local description="$1"
  local json="$2"
  local field="$3"
  local actual
  actual=$(echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print('exists' if $field is not None else 'missing')" 2>/dev/null || echo "__PARSE_ERROR__")
  if [ "$actual" = "exists" ]; then
    pass_test "$description"
  else
    fail_test "$description" "field not found in response"
  fi
}

# Generate unique test user credentials per run
TIMESTAMP=$(date +%s)
TEST_USER="integration_${TIMESTAMP}"
TEST_PASS="testpass_${TIMESTAMP}"
TEST_EMAIL="${TEST_USER}@test.codex.local"
AUTH_TOKEN=""

# --- Backend Health Tests ---

echo ""
echo "=== Backend Health Tests ==="

RESP=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/health")
assert_status "GET /health returns 200" 200 "$RESP"

BODY=$(curl -s "${BACKEND_URL}/health")
assert_json_field "Health response has status=healthy" "$BODY" "['status']" "healthy"

RESP=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/")
assert_status "GET / returns 200" 200 "$RESP"

BODY=$(curl -s "${BACKEND_URL}/")
assert_json_field "Root response has message" "$BODY" "['message']" "Codex API"

RESP=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/docs")
assert_status "GET /docs (OpenAPI) returns 200" 200 "$RESP"

# --- Frontend Tests ---

echo ""
echo "=== Frontend Tests ==="

RESP=$(curl -s -o /dev/null -w "%{http_code}" "${FRONTEND_URL}/")
assert_status "GET frontend / returns 200" 200 "$RESP"

BODY=$(curl -s "${FRONTEND_URL}/")
if echo "$BODY" | grep -q '<div id="app">' 2>/dev/null; then
  pass_test "Frontend serves Vue app HTML"
else
  fail_test "Frontend serves Vue app HTML" "Missing <div id=\"app\">"
fi

RESP=$(curl -s -o /dev/null -w "%{http_code}" "${FRONTEND_URL}/assets/" || echo "000")
# Static assets directory should exist (may return 403 for directory listing)
if [ "$RESP" -ne "000" ]; then
  pass_test "Frontend serves static assets path"
else
  fail_test "Frontend serves static assets path" "No response"
fi

# Frontend proxies API requests to backend
BODY=$(curl -s "${FRONTEND_URL}/api/v1/users/me")
# Should get 401 since we're not authenticated - proves the proxy works
RESP=$(curl -s -o /dev/null -w "%{http_code}" "${FRONTEND_URL}/api/v1/users/me")
if [ "$RESP" -eq 401 ] || [ "$RESP" -eq 403 ]; then
  pass_test "Frontend proxies /api requests to backend"
else
  fail_test "Frontend proxies /api requests to backend" "expected 401 or 403, got $RESP"
fi

# --- User Registration & Authentication ---

echo ""
echo "=== User Registration & Authentication ==="

BODY=$(curl -s -w "\n%{http_code}" -X POST "${BACKEND_URL}/api/v1/users/register" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${TEST_USER}\",\"password\":\"${TEST_PASS}\",\"email\":\"${TEST_EMAIL}\"}")
HTTP_CODE=$(echo "$BODY" | tail -1)
RESP_BODY=$(echo "$BODY" | sed '$d')
assert_status "POST /api/v1/users/register creates user" 200 "$HTTP_CODE"
assert_json_field "Registration returns username" "$RESP_BODY" "['username']" "$TEST_USER"

BODY=$(curl -s -w "\n%{http_code}" -X POST "${BACKEND_URL}/api/v1/users/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${TEST_USER}&password=${TEST_PASS}")
HTTP_CODE=$(echo "$BODY" | tail -1)
RESP_BODY=$(echo "$BODY" | sed '$d')
assert_status "POST /api/v1/users/token returns token" 200 "$HTTP_CODE"

AUTH_TOKEN=$(echo "$RESP_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")
if [ -n "$AUTH_TOKEN" ]; then
  pass_test "Login returns valid access_token"
else
  fail_test "Login returns valid access_token" "Could not extract token"
fi

AUTH_HEADER="Authorization: Bearer ${AUTH_TOKEN}"

# Verify authenticated user info
BODY=$(curl -s -w "\n%{http_code}" -H "$AUTH_HEADER" "${BACKEND_URL}/api/v1/users/me")
HTTP_CODE=$(echo "$BODY" | tail -1)
RESP_BODY=$(echo "$BODY" | sed '$d')
assert_status "GET /api/v1/users/me returns 200" 200 "$HTTP_CODE"
assert_json_field "User profile returns correct username" "$RESP_BODY" "['username']" "$TEST_USER"

# --- Workspace CRUD ---

echo ""
echo "=== Workspace CRUD ==="

WORKSPACE_NAME="integration-test-ws-${TIMESTAMP}"
BODY=$(curl -s -w "\n%{http_code}" -X POST "${BACKEND_URL}/api/v1/workspaces/" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"${WORKSPACE_NAME}\"}")
HTTP_CODE=$(echo "$BODY" | tail -1)
RESP_BODY=$(echo "$BODY" | sed '$d')
assert_status "POST /api/v1/workspaces/ creates workspace" 200 "$HTTP_CODE"

WORKSPACE_ID=$(echo "$RESP_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")
if [ -n "$WORKSPACE_ID" ]; then
  pass_test "Workspace creation returns ID"
else
  fail_test "Workspace creation returns ID" "Could not extract workspace ID"
fi

# List workspaces
BODY=$(curl -s -w "\n%{http_code}" -H "$AUTH_HEADER" "${BACKEND_URL}/api/v1/workspaces/")
HTTP_CODE=$(echo "$BODY" | tail -1)
RESP_BODY=$(echo "$BODY" | sed '$d')
assert_status "GET /api/v1/workspaces/ returns 200" 200 "$HTTP_CODE"

WS_COUNT=$(echo "$RESP_BODY" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
if [ "$WS_COUNT" -ge 1 ]; then
  pass_test "Workspace list contains at least 1 workspace"
else
  fail_test "Workspace list contains at least 1 workspace" "got $WS_COUNT"
fi

# Get single workspace
BODY=$(curl -s -w "\n%{http_code}" -H "$AUTH_HEADER" "${BACKEND_URL}/api/v1/workspaces/${WORKSPACE_ID}")
HTTP_CODE=$(echo "$BODY" | tail -1)
RESP_BODY=$(echo "$BODY" | sed '$d')
assert_status "GET /api/v1/workspaces/{id} returns 200" 200 "$HTTP_CODE"
assert_json_field "Workspace has correct name" "$RESP_BODY" "['name']" "$WORKSPACE_NAME"

# --- Notebook CRUD ---

echo ""
echo "=== Notebook CRUD ==="

NOTEBOOK_NAME="integration-test-nb-${TIMESTAMP}"
BODY=$(curl -s -w "\n%{http_code}" -X POST "${BACKEND_URL}/api/v1/workspaces/${WORKSPACE_ID}/notebooks/" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"${NOTEBOOK_NAME}\"}")
HTTP_CODE=$(echo "$BODY" | tail -1)
RESP_BODY=$(echo "$BODY" | sed '$d')
assert_status "POST .../notebooks/ creates notebook" 200 "$HTTP_CODE"

NOTEBOOK_ID=$(echo "$RESP_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")
if [ -n "$NOTEBOOK_ID" ]; then
  pass_test "Notebook creation returns ID"
else
  fail_test "Notebook creation returns ID" "Could not extract notebook ID"
fi

# List notebooks
BODY=$(curl -s -w "\n%{http_code}" -H "$AUTH_HEADER" \
  "${BACKEND_URL}/api/v1/workspaces/${WORKSPACE_ID}/notebooks/")
HTTP_CODE=$(echo "$BODY" | tail -1)
RESP_BODY=$(echo "$BODY" | sed '$d')
assert_status "GET .../notebooks/ returns 200" 200 "$HTTP_CODE"

NB_COUNT=$(echo "$RESP_BODY" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
if [ "$NB_COUNT" -ge 1 ]; then
  pass_test "Notebook list contains at least 1 notebook"
else
  fail_test "Notebook list contains at least 1 notebook" "got $NB_COUNT"
fi

# --- File Operations ---

echo ""
echo "=== File Operations ==="

# Create a file in the notebook
FILE_CONTENT="---\ntitle: Integration Test File\ntags: [test, integration]\n---\n\n# Hello from integration tests\n\nThis file was created by the Docker integration test suite."
BODY=$(curl -s -w "\n%{http_code}" -X POST \
  "${BACKEND_URL}/api/v1/workspaces/${WORKSPACE_ID}/notebooks/${NOTEBOOK_ID}/files/?path=test-file.md" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: text/markdown" \
  -d "$FILE_CONTENT")
HTTP_CODE=$(echo "$BODY" | tail -1)
RESP_BODY=$(echo "$BODY" | sed '$d')
assert_status "POST .../files/ creates file" 200 "$HTTP_CODE"

# List files
BODY=$(curl -s -w "\n%{http_code}" -H "$AUTH_HEADER" \
  "${BACKEND_URL}/api/v1/workspaces/${WORKSPACE_ID}/notebooks/${NOTEBOOK_ID}/files/")
HTTP_CODE=$(echo "$BODY" | tail -1)
RESP_BODY=$(echo "$BODY" | sed '$d')
assert_status "GET .../files/ returns 200" 200 "$HTTP_CODE"

# --- Search ---

echo ""
echo "=== Search ==="

# Give the watcher a moment to index
sleep 2

BODY=$(curl -s -w "\n%{http_code}" -H "$AUTH_HEADER" \
  "${BACKEND_URL}/api/v1/workspaces/${WORKSPACE_ID}/search/?q=integration")
HTTP_CODE=$(echo "$BODY" | tail -1)
assert_status "GET .../search/?q=integration returns 200" 200 "$HTTP_CODE"

# --- Task Queue ---

echo ""
echo "=== Task Queue ==="

RESP=$(curl -s -o /dev/null -w "%{http_code}" -H "$AUTH_HEADER" \
  "${BACKEND_URL}/api/v1/tasks/")
assert_status "GET /api/v1/tasks/ returns 200" 200 "$RESP"

# --- Query API ---

echo ""
echo "=== Query API ==="

RESP=$(curl -s -o /dev/null -w "%{http_code}" -H "$AUTH_HEADER" \
  -X POST "${BACKEND_URL}/api/v1/query/" \
  -H "Content-Type: application/json" \
  -d "{\"workspace_id\":\"${WORKSPACE_ID}\"}")
# Query endpoint might return 200 or 422 depending on required params
if [ "$RESP" -eq 200 ] || [ "$RESP" -eq 422 ]; then
  pass_test "POST /api/v1/query/ responds (status $RESP)"
else
  fail_test "POST /api/v1/query/ responds" "expected 200 or 422, got $RESP"
fi

# --- Cross-Origin / CORS Headers ---

echo ""
echo "=== CORS Headers ==="

CORS_HEADER=$(curl -s -I -X OPTIONS "${BACKEND_URL}/api/v1/users/me" \
  -H "Origin: http://example.com" \
  -H "Access-Control-Request-Method: GET" 2>/dev/null | grep -i "access-control-allow-origin" || echo "")
if [ -n "$CORS_HEADER" ]; then
  pass_test "Backend returns CORS headers"
else
  fail_test "Backend returns CORS headers" "No Access-Control-Allow-Origin header"
fi

# --- Summary ---

echo ""
echo "==========================================="
echo " Integration Test Results"
echo "==========================================="
echo " Passed: ${PASSED}"
echo " Failed: ${FAILED}"
echo " Total:  ${TOTAL}"
echo "==========================================="

if [ "$FAILED" -gt 0 ]; then
  echo ""
  echo "INTEGRATION TESTS FAILED"
  exit 1
else
  echo ""
  echo "ALL INTEGRATION TESTS PASSED"
  exit 0
fi
