#!/bin/bash
# Register a test user via the Codex API
#
# Usage:
#   ./scripts/register_test_user.sh                    # Register default demo user
#   ./scripts/register_test_user.sh myuser pass123     # Register custom user
#   ./scripts/register_test_user.sh --login            # Register and login (get token)
#
# Requires: curl, jq (optional, for pretty output)

set -e

# Default values
API_URL="${CODEX_API_URL:-http://localhost:8765}"
DEFAULT_USERNAME="demo"
DEFAULT_PASSWORD="demo123456"
DEFAULT_EMAIL="demo@example.com"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_usage() {
    echo "Usage: $0 [OPTIONS] [username] [password] [email]"
    echo ""
    echo "Register a test user via the Codex API."
    echo ""
    echo "Options:"
    echo "  --login         Also login and display the access token"
    echo "  --api-url URL   Override the API URL (default: http://localhost:8765)"
    echo "  -h, --help      Show this help message"
    echo ""
    echo "Arguments:"
    echo "  username        Username for the new user (default: demo)"
    echo "  password        Password for the new user (default: demo123456)"
    echo "  email           Email for the new user (default: demo@example.com)"
    echo ""
    echo "Examples:"
    echo "  $0                           # Register 'demo' user"
    echo "  $0 testuser testpass123      # Register custom user"
    echo "  $0 --login demo demo123456   # Register and get access token"
    echo ""
    echo "Environment variables:"
    echo "  CODEX_API_URL   API base URL (default: http://localhost:8765)"
}

# Parse arguments
DO_LOGIN=false
POSITIONAL_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --login)
            DO_LOGIN=true
            shift
            ;;
        --api-url)
            API_URL="$2"
            shift 2
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            POSITIONAL_ARGS+=("$1")
            shift
            ;;
    esac
done

# Set positional arguments
USERNAME="${POSITIONAL_ARGS[0]:-$DEFAULT_USERNAME}"
PASSWORD="${POSITIONAL_ARGS[1]:-$DEFAULT_PASSWORD}"
EMAIL="${POSITIONAL_ARGS[2]:-${USERNAME}@example.com}"

echo -e "${YELLOW}Registering user...${NC}"
echo "  API URL:  $API_URL"
echo "  Username: $USERNAME"
echo "  Email:    $EMAIL"
echo ""

# Register the user
REGISTER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}/register" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"${USERNAME}\", \"password\": \"${PASSWORD}\", \"email\": \"${EMAIL}\"}")

HTTP_CODE=$(echo "$REGISTER_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$REGISTER_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 201 ]; then
    echo -e "${GREEN}✓ User registered successfully!${NC}"
    if command -v jq &> /dev/null; then
        echo "$RESPONSE_BODY" | jq .
    else
        echo "$RESPONSE_BODY"
    fi
elif [ "$HTTP_CODE" -eq 400 ]; then
    echo -e "${YELLOW}⚠ User may already exist:${NC}"
    if command -v jq &> /dev/null; then
        echo "$RESPONSE_BODY" | jq -r '.detail // .'
    else
        echo "$RESPONSE_BODY"
    fi
else
    echo -e "${RED}✗ Registration failed (HTTP $HTTP_CODE):${NC}"
    echo "$RESPONSE_BODY"
    exit 1
fi

# Optionally login and get token
if [ "$DO_LOGIN" = true ]; then
    echo ""
    echo -e "${YELLOW}Logging in...${NC}"

    LOGIN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=${USERNAME}&password=${PASSWORD}")

    HTTP_CODE=$(echo "$LOGIN_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$LOGIN_RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" -eq 200 ]; then
        echo -e "${GREEN}✓ Login successful!${NC}"
        if command -v jq &> /dev/null; then
            TOKEN=$(echo "$RESPONSE_BODY" | jq -r '.access_token')
            echo ""
            echo "Access Token:"
            echo "$TOKEN"
            echo ""
            echo "Use with curl:"
            echo "  curl -H \"Authorization: Bearer $TOKEN\" ${API_URL}/users/me"
        else
            echo "$RESPONSE_BODY"
        fi
    else
        echo -e "${RED}✗ Login failed (HTTP $HTTP_CODE):${NC}"
        echo "$RESPONSE_BODY"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}Done!${NC}"
echo ""
echo "Quick reference - Test user credentials:"
echo "  Username: $USERNAME"
echo "  Password: $PASSWORD"
echo "  Email:    $EMAIL"
