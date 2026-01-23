#!/bin/bash
# Run Alembic migrations for the system database
# This script is used by Docker containers and can also be run manually

set -e

# Change to the backend directory
cd "$(dirname "$0")/.."

# Ensure the data directory exists
mkdir -p ./data

# Run alembic migrations
echo "Running database migrations..."
alembic upgrade head
echo "Migrations complete."
