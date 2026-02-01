#!/bin/bash
# Script to run plugin Docker integration tests
#
# Usage:
#   ./scripts/run_plugin_docker_tests.sh           # Run all tests
#   ./scripts/run_plugin_docker_tests.sh -k theme  # Run only theme tests
#   ./scripts/run_plugin_docker_tests.sh --keep    # Keep container running after tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.test.yml"
DATA_DIR="$PROJECT_ROOT/data-test"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
KEEP_RUNNING=false
PYTEST_ARGS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --keep)
            KEEP_RUNNING=true
            shift
            ;;
        *)
            PYTEST_ARGS="$PYTEST_ARGS $1"
            shift
            ;;
    esac
done

echo -e "${YELLOW}=== Plugin Docker Integration Tests ===${NC}"

# Clean up any existing test data
echo -e "${YELLOW}Cleaning up previous test data...${NC}"
rm -rf "$DATA_DIR"
mkdir -p "$DATA_DIR"

# Build and start the test container
echo -e "${YELLOW}Building and starting test container...${NC}"
cd "$PROJECT_ROOT"
docker compose -f "$COMPOSE_FILE" build
docker compose -f "$COMPOSE_FILE" up -d

# Wait for the backend to be healthy
echo -e "${YELLOW}Waiting for backend to be healthy...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8766/health > /dev/null 2>&1; then
        echo -e "${GREEN}Backend is healthy!${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Waiting... (attempt $RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}Backend failed to become healthy${NC}"
    echo "Container logs:"
    docker compose -f "$COMPOSE_FILE" logs backend-test
    docker compose -f "$COMPOSE_FILE" down
    exit 1
fi

# Run the tests
echo -e "${YELLOW}Running integration tests...${NC}"
cd "$PROJECT_ROOT/backend"

# Set the test URL environment variable
export CODEX_TEST_URL="http://localhost:8766"

# Run pytest
TEST_EXIT_CODE=0
python -m pytest tests/integration/test_plugin_docker.py -v $PYTEST_ARGS || TEST_EXIT_CODE=$?

# Cleanup
if [ "$KEEP_RUNNING" = false ]; then
    echo -e "${YELLOW}Stopping test container...${NC}"
    cd "$PROJECT_ROOT"
    docker compose -f "$COMPOSE_FILE" down
    rm -rf "$DATA_DIR"
else
    echo -e "${YELLOW}Container still running. Stop with:${NC}"
    echo "  docker compose -f docker-compose.test.yml down"
fi

# Report results
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}=== All tests passed! ===${NC}"
else
    echo -e "${RED}=== Some tests failed ===${NC}"
fi

exit $TEST_EXIT_CODE
