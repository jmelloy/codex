#!/usr/bin/env bash
# Docker Compose Validation Script
# This script validates Docker Compose configurations without actually building images

set -e

echo "=========================================="
echo "Docker Compose Configuration Validation"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    exit 1
fi

# Check if Docker Compose is installed
if ! docker compose version &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed"
    exit 1
fi

echo "✅ Docker is installed: $(docker --version)"
echo "✅ Docker Compose is installed: $(docker compose version)"
echo ""

# Validate development docker-compose.yml
echo "Validating docker-compose.yml (development)..."
if docker compose -f docker-compose.yml config > /dev/null 2>&1; then
    echo "✅ docker-compose.yml is valid"
else
    echo "❌ docker-compose.yml has errors"
    exit 1
fi
echo ""

# Validate production docker-compose.prod.yml
echo "Validating docker-compose.prod.yml (production)..."
if docker compose -f docker-compose.prod.yml config > /dev/null 2>&1; then
    echo "✅ docker-compose.prod.yml is valid"
else
    echo "❌ docker-compose.prod.yml has errors"
    exit 1
fi
echo ""

# Check for required files
echo "Checking required files..."
required_files=(
    "Dockerfile"
    "frontend/Dockerfile"
    "frontend/Dockerfile.dev.frontend"
    "frontend/nginx.conf"
    "pyproject.toml"
    ".env.example"
)

all_files_exist=true
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file is missing"
        all_files_exist=false
    fi
done

if [ "$all_files_exist" = false ]; then
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ All validations passed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  - For development: docker compose up -d"
echo "  - For production:  docker compose -f docker-compose.prod.yml up -d"
echo ""
echo "See DOCKER.md for detailed deployment instructions."
