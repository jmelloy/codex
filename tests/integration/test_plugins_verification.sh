#!/usr/bin/env bash
#
# Plugin verification tests for Codex running in Docker.
# Verifies that plugins are discovered, loadable, and accessible via the API.
# Expects BACKEND_URL environment variable.
#
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://localhost:8765}"

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

# --- setup: register a test user and get auth token ---

TIMESTAMP=$(date +%s)
TEST_USER="plugintest_${TIMESTAMP}"
TEST_PASS="pluginpass_${TIMESTAMP}"
TEST_EMAIL="${TEST_USER}@test.codex.local"

echo ""
echo "=== Setup: Create test user ==="

curl -s -X POST "${BACKEND_URL}/api/v1/users/register" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${TEST_USER}\",\"password\":\"${TEST_PASS}\",\"email\":\"${TEST_EMAIL}\"}" > /dev/null

TOKEN_RESP=$(curl -s -X POST "${BACKEND_URL}/api/v1/users/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${TEST_USER}&password=${TEST_PASS}")

AUTH_TOKEN=$(echo "$TOKEN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")

if [ -z "$AUTH_TOKEN" ]; then
  echo "FATAL: Could not authenticate test user"
  exit 1
fi

AUTH_HEADER="Authorization: Bearer ${AUTH_TOKEN}"
echo "  Authenticated as ${TEST_USER}"

# --- Plugin Manifest Validation (filesystem level via docker exec) ---

echo ""
echo "=== Plugin Manifest Validation ==="

# Check that the plugins directory is mounted and contains plugins
PLUGIN_COUNT=$(docker compose exec -T backend sh -c 'ls -d /app/plugins/*/ 2>/dev/null | wc -l' || echo "0")
PLUGIN_COUNT=$(echo "$PLUGIN_COUNT" | tr -d '[:space:]')

if [ "$PLUGIN_COUNT" -ge 5 ]; then
  pass_test "Plugins directory contains $PLUGIN_COUNT plugins (expected >= 5)"
else
  fail_test "Plugins directory contains enough plugins" "found $PLUGIN_COUNT, expected >= 5"
fi

# Verify specific expected plugins exist in the filesystem
EXPECTED_PLUGINS="core cream gallery corkboard tasks weather-api github opengraph"
for plugin_name in $EXPECTED_PLUGINS; do
  EXISTS=$(docker compose exec -T backend sh -c "test -d /app/plugins/${plugin_name} && echo yes || echo no" || echo "no")
  EXISTS=$(echo "$EXISTS" | tr -d '[:space:]')
  if [ "$EXISTS" = "yes" ]; then
    pass_test "Plugin directory exists: $plugin_name"
  else
    fail_test "Plugin directory exists: $plugin_name" "directory not found"
  fi
done

# Verify each expected plugin has a manifest.yml
for plugin_name in $EXPECTED_PLUGINS; do
  HAS_MANIFEST=$(docker compose exec -T backend sh -c "test -f /app/plugins/${plugin_name}/manifest.yml && echo yes || echo no" || echo "no")
  HAS_MANIFEST=$(echo "$HAS_MANIFEST" | tr -d '[:space:]')
  if [ "$HAS_MANIFEST" = "yes" ]; then
    pass_test "Plugin has manifest.yml: $plugin_name"
  else
    fail_test "Plugin has manifest.yml: $plugin_name" "manifest.yml not found"
  fi
done

# Validate manifest YAML structure for each plugin
for plugin_name in $EXPECTED_PLUGINS; do
  MANIFEST_VALID=$(docker compose exec -T backend python3 -c "
import yaml, sys
try:
    with open('/app/plugins/${plugin_name}/manifest.yml') as f:
        m = yaml.safe_load(f)
    required = ['id', 'name', 'version', 'type']
    missing = [k for k in required if k not in m]
    if missing:
        print(f'missing fields: {missing}')
    elif m['type'] not in ('view', 'theme', 'integration'):
        print(f'invalid type: {m[\"type\"]}')
    else:
        print('valid')
except Exception as e:
    print(f'error: {e}')
" 2>/dev/null || echo "error: exec failed")
  MANIFEST_VALID=$(echo "$MANIFEST_VALID" | tr -d '[:space:]')
  if [ "$MANIFEST_VALID" = "valid" ]; then
    pass_test "Plugin manifest is valid YAML: $plugin_name"
  else
    fail_test "Plugin manifest is valid YAML: $plugin_name" "$MANIFEST_VALID"
  fi
done

# --- Plugin Loader Verification ---

echo ""
echo "=== Plugin Loader Verification ==="

# Verify plugin loader initialized by checking backend logs
LOADER_LOG=$(docker compose logs backend 2>/dev/null | grep -c "Loading plugins from directory" || echo "0")
if [ "$LOADER_LOG" -ge 1 ]; then
  pass_test "Backend logs show plugin loader initialized"
else
  fail_test "Backend logs show plugin loader initialized" "log message not found"
fi

LOADED_LOG=$(docker compose logs backend 2>/dev/null | grep -c "Loaded plugins from" || echo "0")
if [ "$LOADED_LOG" -ge 1 ]; then
  pass_test "Backend logs show plugins loaded successfully"
else
  fail_test "Backend logs show plugins loaded successfully" "log message not found"
fi

# --- Plugin Registration API ---

echo ""
echo "=== Plugin Registration API ==="

# Register a test plugin
REG_RESP=$(curl -s -w "\n%{http_code}" -X POST "${BACKEND_URL}/api/v1/plugins/register" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test-plugin-ci",
    "name": "CI Test Plugin",
    "version": "1.0.0",
    "type": "view",
    "manifest": {"id": "test-plugin-ci", "name": "CI Test Plugin", "version": "1.0.0", "type": "view"}
  }')
REG_HTTP=$(echo "$REG_RESP" | tail -1)
REG_BODY=$(echo "$REG_RESP" | sed '$d')

if [ "$REG_HTTP" -eq 200 ]; then
  pass_test "POST /api/v1/plugins/register succeeds"
else
  fail_test "POST /api/v1/plugins/register succeeds" "HTTP $REG_HTTP"
fi

REG_STATUS=$(echo "$REG_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('registered', False))" 2>/dev/null || echo "False")
if [ "$REG_STATUS" = "True" ]; then
  pass_test "Plugin registration returns registered=true"
else
  fail_test "Plugin registration returns registered=true" "got $REG_STATUS"
fi

# Register batch of plugins
BATCH_RESP=$(curl -s -w "\n%{http_code}" -X POST "${BACKEND_URL}/api/v1/plugins/register-batch" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "plugins": [
      {"id": "batch-theme-ci", "name": "CI Batch Theme", "version": "1.0.0", "type": "theme", "manifest": {"id": "batch-theme-ci", "name": "CI Batch Theme", "version": "1.0.0", "type": "theme"}},
      {"id": "batch-integration-ci", "name": "CI Batch Integration", "version": "2.0.0", "type": "integration", "manifest": {"id": "batch-integration-ci", "name": "CI Batch Integration", "version": "2.0.0", "type": "integration"}}
    ]
  }')
BATCH_HTTP=$(echo "$BATCH_RESP" | tail -1)
BATCH_BODY=$(echo "$BATCH_RESP" | sed '$d')

if [ "$BATCH_HTTP" -eq 200 ]; then
  pass_test "POST /api/v1/plugins/register-batch succeeds"
else
  fail_test "POST /api/v1/plugins/register-batch succeeds" "HTTP $BATCH_HTTP"
fi

BATCH_REGISTERED=$(echo "$BATCH_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('registered', 0))" 2>/dev/null || echo "0")
if [ "$BATCH_REGISTERED" -eq 2 ]; then
  pass_test "Batch registration registered 2 plugins"
else
  fail_test "Batch registration registered 2 plugins" "registered $BATCH_REGISTERED"
fi

# --- Plugin Listing API ---

echo ""
echo "=== Plugin Listing API ==="

LIST_RESP=$(curl -s -w "\n%{http_code}" -H "$AUTH_HEADER" "${BACKEND_URL}/api/v1/plugins")
LIST_HTTP=$(echo "$LIST_RESP" | tail -1)
LIST_BODY=$(echo "$LIST_RESP" | sed '$d')

if [ "$LIST_HTTP" -eq 200 ]; then
  pass_test "GET /api/v1/plugins returns 200"
else
  fail_test "GET /api/v1/plugins returns 200" "HTTP $LIST_HTTP"
fi

PLUGIN_LIST_COUNT=$(echo "$LIST_BODY" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
if [ "$PLUGIN_LIST_COUNT" -ge 3 ]; then
  pass_test "Plugin list contains $PLUGIN_LIST_COUNT plugins (>= 3 expected)"
else
  fail_test "Plugin list contains enough plugins" "found $PLUGIN_LIST_COUNT, expected >= 3"
fi

# Filter by type
for ptype in view theme integration; do
  TYPE_RESP=$(curl -s -w "\n%{http_code}" -H "$AUTH_HEADER" "${BACKEND_URL}/api/v1/plugins?plugin_type=${ptype}")
  TYPE_HTTP=$(echo "$TYPE_RESP" | tail -1)
  TYPE_BODY=$(echo "$TYPE_RESP" | sed '$d')

  if [ "$TYPE_HTTP" -eq 200 ]; then
    TYPE_COUNT=$(echo "$TYPE_BODY" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
    if [ "$TYPE_COUNT" -ge 1 ]; then
      pass_test "GET /api/v1/plugins?plugin_type=$ptype returns $TYPE_COUNT plugin(s)"
    else
      fail_test "GET /api/v1/plugins?plugin_type=$ptype returns plugins" "found 0"
    fi
  else
    fail_test "GET /api/v1/plugins?plugin_type=$ptype returns 200" "HTTP $TYPE_HTTP"
  fi
done

# Get specific plugin by ID
SINGLE_RESP=$(curl -s -w "\n%{http_code}" -H "$AUTH_HEADER" "${BACKEND_URL}/api/v1/plugins/test-plugin-ci")
SINGLE_HTTP=$(echo "$SINGLE_RESP" | tail -1)
SINGLE_BODY=$(echo "$SINGLE_RESP" | sed '$d')

if [ "$SINGLE_HTTP" -eq 200 ]; then
  pass_test "GET /api/v1/plugins/test-plugin-ci returns 200"
else
  fail_test "GET /api/v1/plugins/test-plugin-ci returns 200" "HTTP $SINGLE_HTTP"
fi

PLUGIN_NAME=$(echo "$SINGLE_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('name',''))" 2>/dev/null || echo "")
if [ "$PLUGIN_NAME" = "CI Test Plugin" ]; then
  pass_test "Plugin detail returns correct name"
else
  fail_test "Plugin detail returns correct name" "got '$PLUGIN_NAME'"
fi

# Non-existent plugin returns 404
MISSING_RESP=$(curl -s -o /dev/null -w "%{http_code}" -H "$AUTH_HEADER" "${BACKEND_URL}/api/v1/plugins/does-not-exist")
if [ "$MISSING_RESP" -eq 404 ]; then
  pass_test "GET /api/v1/plugins/does-not-exist returns 404"
else
  fail_test "GET /api/v1/plugins/does-not-exist returns 404" "HTTP $MISSING_RESP"
fi

# --- Plugin Validation ---

echo ""
echo "=== Plugin Validation ==="

# Invalid plugin ID should fail
INVALID_RESP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BACKEND_URL}/api/v1/plugins/register" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"id": "INVALID_ID!", "name": "Bad Plugin", "version": "1.0.0", "type": "view", "manifest": {}}')
if [ "$INVALID_RESP" -eq 400 ]; then
  pass_test "Invalid plugin ID rejected with 400"
else
  fail_test "Invalid plugin ID rejected with 400" "HTTP $INVALID_RESP"
fi

# Invalid version format should fail
INVALID_VER_RESP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BACKEND_URL}/api/v1/plugins/register" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"id": "valid-id", "name": "Bad Version", "version": "not-semver", "type": "view", "manifest": {}}')
if [ "$INVALID_VER_RESP" -eq 400 ]; then
  pass_test "Invalid version format rejected with 400"
else
  fail_test "Invalid version format rejected with 400" "HTTP $INVALID_VER_RESP"
fi

# Invalid plugin type should fail
INVALID_TYPE_RESP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BACKEND_URL}/api/v1/plugins/register" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"id": "valid-id", "name": "Bad Type", "version": "1.0.0", "type": "invalid", "manifest": {}}')
if [ "$INVALID_TYPE_RESP" -eq 400 ]; then
  pass_test "Invalid plugin type rejected with 400"
else
  fail_test "Invalid plugin type rejected with 400" "HTTP $INVALID_TYPE_RESP"
fi

# --- Plugin Unregister ---

echo ""
echo "=== Plugin Unregister ==="

DEL_RESP=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
  -H "$AUTH_HEADER" \
  "${BACKEND_URL}/api/v1/plugins/test-plugin-ci")
if [ "$DEL_RESP" -eq 200 ]; then
  pass_test "DELETE /api/v1/plugins/test-plugin-ci returns 200"
else
  fail_test "DELETE /api/v1/plugins/test-plugin-ci returns 200" "HTTP $DEL_RESP"
fi

# Verify it's gone
GONE_RESP=$(curl -s -o /dev/null -w "%{http_code}" -H "$AUTH_HEADER" "${BACKEND_URL}/api/v1/plugins/test-plugin-ci")
if [ "$GONE_RESP" -eq 404 ]; then
  pass_test "Unregistered plugin returns 404"
else
  fail_test "Unregistered plugin returns 404" "HTTP $GONE_RESP"
fi

# --- Integration Plugin API ---

echo ""
echo "=== Integration Plugin API ==="

# Register the weather-api integration (simulating what the frontend does)
curl -s -X POST "${BACKEND_URL}/api/v1/plugins/register" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "weather-api",
    "name": "Weather API Integration",
    "version": "1.0.0",
    "type": "integration",
    "manifest": {
      "id": "weather-api",
      "name": "Weather API Integration",
      "version": "1.0.0",
      "type": "integration",
      "integration": {
        "api_type": "rest",
        "base_url": "https://api.openweathermap.org",
        "auth_method": "api_key",
        "test_endpoint": "geocode"
      },
      "endpoints": [
        {"id": "geocode", "name": "Geocode Location", "method": "GET", "path": "/geo/1.0/direct"}
      ],
      "blocks": [
        {"id": "weather", "name": "Weather Block"}
      ]
    }
  }' > /dev/null

# List integrations
INT_RESP=$(curl -s -w "\n%{http_code}" -H "$AUTH_HEADER" "${BACKEND_URL}/api/v1/plugins/integrations")
INT_HTTP=$(echo "$INT_RESP" | tail -1)
INT_BODY=$(echo "$INT_RESP" | sed '$d')

if [ "$INT_HTTP" -eq 200 ]; then
  pass_test "GET /api/v1/plugins/integrations returns 200"
else
  fail_test "GET /api/v1/plugins/integrations returns 200" "HTTP $INT_HTTP"
fi

INT_COUNT=$(echo "$INT_BODY" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
if [ "$INT_COUNT" -ge 1 ]; then
  pass_test "Integration list contains $INT_COUNT integration(s)"
else
  fail_test "Integration list contains integrations" "found $INT_COUNT"
fi

# Get specific integration
INT_DETAIL_RESP=$(curl -s -w "\n%{http_code}" -H "$AUTH_HEADER" "${BACKEND_URL}/api/v1/plugins/integrations/weather-api")
INT_DETAIL_HTTP=$(echo "$INT_DETAIL_RESP" | tail -1)
INT_DETAIL_BODY=$(echo "$INT_DETAIL_RESP" | sed '$d')

if [ "$INT_DETAIL_HTTP" -eq 200 ]; then
  pass_test "GET /api/v1/plugins/integrations/weather-api returns 200"
  API_TYPE=$(echo "$INT_DETAIL_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('api_type',''))" 2>/dev/null || echo "")
  if [ "$API_TYPE" = "rest" ]; then
    pass_test "Weather integration has api_type=rest"
  else
    fail_test "Weather integration has api_type=rest" "got '$API_TYPE'"
  fi
else
  fail_test "GET /api/v1/plugins/integrations/weather-api returns 200" "HTTP $INT_DETAIL_HTTP"
fi

# Get integration blocks
BLOCKS_RESP=$(curl -s -w "\n%{http_code}" -H "$AUTH_HEADER" "${BACKEND_URL}/api/v1/plugins/integrations/weather-api/blocks")
BLOCKS_HTTP=$(echo "$BLOCKS_RESP" | tail -1)
BLOCKS_BODY=$(echo "$BLOCKS_RESP" | sed '$d')

if [ "$BLOCKS_HTTP" -eq 200 ]; then
  pass_test "GET .../weather-api/blocks returns 200"
  BLOCK_COUNT=$(echo "$BLOCKS_BODY" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('blocks',[])))" 2>/dev/null || echo "0")
  if [ "$BLOCK_COUNT" -ge 1 ]; then
    pass_test "Weather integration has $BLOCK_COUNT block type(s)"
  else
    fail_test "Weather integration has block types" "found $BLOCK_COUNT"
  fi
else
  fail_test "GET .../weather-api/blocks returns 200" "HTTP $BLOCKS_HTTP"
fi

# --- Plugin Type Counts ---

echo ""
echo "=== Plugin Type Distribution ==="

# Count plugins by type in the container filesystem
for ptype in view theme integration; do
  FS_COUNT=$(docker compose exec -T backend python3 -c "
import yaml, os
count = 0
plugins_dir = '/app/plugins'
for name in os.listdir(plugins_dir):
    manifest_path = os.path.join(plugins_dir, name, 'manifest.yml')
    if os.path.isfile(manifest_path):
        with open(manifest_path) as f:
            m = yaml.safe_load(f)
        if m.get('type') == '${ptype}':
            count += 1
print(count)
" 2>/dev/null || echo "0")
  FS_COUNT=$(echo "$FS_COUNT" | tr -d '[:space:]')
  if [ "$FS_COUNT" -ge 1 ]; then
    pass_test "Filesystem has $FS_COUNT '${ptype}' plugin(s)"
  else
    fail_test "Filesystem has '${ptype}' plugins" "found $FS_COUNT"
  fi
done

# --- Cleanup ---

echo ""
echo "=== Cleanup ==="

# Delete test plugins
for pid in batch-theme-ci batch-integration-ci weather-api; do
  curl -s -o /dev/null -X DELETE -H "$AUTH_HEADER" "${BACKEND_URL}/api/v1/plugins/${pid}"
done
pass_test "Cleaned up test plugins"

# --- Summary ---

echo ""
echo "==========================================="
echo " Plugin Verification Results"
echo "==========================================="
echo " Passed: ${PASSED}"
echo " Failed: ${FAILED}"
echo " Total:  ${TOTAL}"
echo "==========================================="

if [ "$FAILED" -gt 0 ]; then
  echo ""
  echo "PLUGIN VERIFICATION FAILED"
  exit 1
else
  echo ""
  echo "ALL PLUGIN VERIFICATION TESTS PASSED"
  exit 0
fi
