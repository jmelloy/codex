# Codex Build System
# ==================
# Build and development commands for the Codex project.
#
# Quick Start:
#   make              - Build plugins and start production containers
#   make dev-docker   - Setup and start development containers (with hot-reload)
#
# Local Development (no Docker):
#   make install      - Install all dependencies
#   make dev          - Start local development servers

.PHONY: all install build dev test clean help
.PHONY: install-backend install-frontend install-plugins
.PHONY: build-plugins build-plugin build-frontend
.PHONY: dev-backend dev-frontend dev-docker
.PHONY: test-backend test-frontend test-e2e test-e2e-local
.PHONY: lint lint-backend lint-frontend
.PHONY: typecheck typecheck-backend typecheck-frontend typecheck-plugins
.PHONY: clean-plugins clean-frontend clean-backend
.PHONY: deploy docker-build docker-up docker-down docker-logs

# Default target - production deployment
all: deploy

# =============================================================================
# Docker Deployment
# =============================================================================

# Production: Build plugins and start containers
deploy: build-plugins docker-build docker-up
	@echo ""
	@echo "Deployment complete!"
	
# Development: Setup override file and start with hot-reload
dev-docker: build-plugins
	@if [ ! -f docker-compose.override.yml ]; then \
		echo "Setting up development environment..."; \
		cp docker-compose.override.yml.example docker-compose.override.yml; \
		echo "Created docker-compose.override.yml"; \
	fi
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env from .env.example"; \
	fi
	@echo "Starting development containers..."
	docker compose up -d --remove-orphans
	@echo ""
	@echo "Development environment ready!"
	@echo "  Backend:  http://localhost:8765 (hot-reload enabled)"
	@echo "  Frontend: http://localhost:5165 (Vite dev server)"
	@echo ""
	@echo "Run 'make docker-logs' to view logs"

# Build Docker images
docker-build: build-plugins
	@echo "Building Docker images..."
	docker compose build

# Start Docker containers
docker-up:
	@echo "Starting Docker containers..."
	docker compose up -d --remove-orphans
	@echo ""
	@echo "Services starting..."
	@echo "  Backend:  http://localhost:8765"
	@if [ -f docker-compose.override.yml ]; then \
		echo "  Frontend (dev server): http://localhost:5165"; \
	else \
		echo "  Frontend: http://localhost:8065"; \
	fi
	@echo ""
	@echo "Run 'make docker-logs' to view logs"

# Stop Docker containers
docker-down:
	@echo "Stopping Docker containers..."
	docker compose down

# View Docker logs
docker-logs:
	docker compose logs -f

# Restart containers (useful after plugin changes)
docker-restart: build-plugins
	@echo "Restarting Docker containers..."
	docker compose restart
	@echo "Containers restarted!"

# Full rebuild and restart
docker-rebuild: build-plugins docker-build
	@echo "Rebuilding and restarting..."
	docker compose up -d --force-recreate
	@echo "Rebuild complete!"

# =============================================================================
# Installation (for local development without Docker)
# =============================================================================

install: install-backend install-frontend install-plugins
	@echo "All dependencies installed!"

install-backend:
	@echo "Installing backend dependencies..."
	cd backend && pip install -e ".[dev]"

install-frontend:
	@echo "Installing frontend dependencies..."
	cd frontend && pnpm install

install-plugins:
	@echo "Installing plugin build dependencies..."
	cd plugins && pnpm install

# =============================================================================
# Build
# =============================================================================

build: build-plugins build-frontend
	@echo ""
	@echo "Build complete!"
	@echo "  - Plugins:  plugins/*/dist/"
	@echo "  - Frontend: frontend/dist/"

build-plugins: install-frontend
	@echo "Building plugins..."
	cd plugins && npm install && npm run build

# Build a specific plugin independently
# Usage: make build-plugin PLUGIN=weather-api
build-plugin:
	@if [ -z "$(PLUGIN)" ]; then \
		echo "Error: PLUGIN variable is required"; \
		echo "Usage: make build-plugin PLUGIN=weather-api"; \
		exit 1; \
	fi
	@if [ ! -d "plugins/node_modules" ]; then \
		echo "Installing plugin dependencies..."; \
		cd plugins && npm install; \
	fi
	@echo "Building plugin: $(PLUGIN)..."
	cd plugins && npm run build -- --plugin=$(PLUGIN)

build-frontend: build-plugins
	@echo "Building frontend..."
	cd frontend && npm run build

# Watch plugins for changes (development)
watch-plugins:
	@echo "Watching plugins for changes..."
	cd plugins && npm run build:watch

# =============================================================================
# Local Development (without Docker)
# =============================================================================

dev: dev-backend

dev-backend:
	@echo "Starting backend server on http://localhost:8000..."
	cd backend && python -m codex.main

dev-frontend:
	@echo "Starting frontend dev server on http://localhost:5173..."
	cd frontend && npm run dev

dev-all:
	@echo "Start servers in separate terminals:"
	@echo "  Terminal 1: make dev-backend"
	@echo "  Terminal 2: make dev-frontend"

# =============================================================================
# Testing
# =============================================================================

test: test-backend test-frontend
	@echo "All tests passed!"

test-backend:
	@echo "Running backend tests..."
	cd backend && pytest -v

test-frontend:
	@echo "Running frontend tests..."
	cd frontend && npm test -- --run

test-e2e:
	@echo "Running E2E tests via Docker Compose..."
	docker compose -f docker-compose.e2e.yml up --build --abort-on-container-exit --exit-code-from playwright
	docker compose -f docker-compose.e2e.yml down -v

test-e2e-local:
	@echo "Running E2E tests against local Docker Compose..."
	@echo "Make sure 'docker compose up' is running first."
	cd e2e && npm install && npx playwright install chromium && npx playwright test

test-coverage:
	@echo "Running tests with coverage..."
	cd backend && pytest -v --cov=. --cov-report=term-missing
	cd frontend && npm run coverage

# =============================================================================
# Linting & Type Checking
# =============================================================================

lint: lint-backend lint-frontend
	@echo "Linting complete!"

lint-backend:
	@echo "Linting backend..."
	cd backend && ruff check .

lint-frontend:
	@echo "Linting frontend..."
	cd frontend && npm run build 2>/dev/null || true

typecheck: typecheck-backend typecheck-frontend typecheck-plugins
	@echo "Type checking complete!"

typecheck-backend:
	@echo "Type checking backend..."
	cd backend && mypy .

typecheck-frontend:
	@echo "Type checking frontend..."
	cd frontend && npm run build

typecheck-plugins:
	@echo "Type checking plugins..."
	cd plugins && npm run typecheck

# =============================================================================
# Formatting
# =============================================================================

format: format-backend
	@echo "Formatting complete!"

format-backend:
	@echo "Formatting backend..."
	cd backend && black .

# =============================================================================
# Clean
# =============================================================================

clean: clean-plugins clean-frontend clean-backend
	@echo "Clean complete!"

clean-plugins:
	@echo "Cleaning plugin build artifacts..."
	cd plugins && npm run clean 2>/dev/null || true
	rm -rf plugins/node_modules

clean-frontend:
	@echo "Cleaning frontend build artifacts..."
	rm -rf frontend/dist
	rm -rf frontend/node_modules

clean-backend:
	@echo "Cleaning backend artifacts..."
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find backend -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.pytest_cache
	rm -rf backend/.mypy_cache
	rm -rf backend/.ruff_cache

# Clean everything including Docker
clean-all: clean
	@echo "Cleaning Docker resources..."
	docker compose down -v --rmi local 2>/dev/null || true

# =============================================================================
# Database
# =============================================================================

db-migrate:
	@echo "Running database migrations..."
	cd backend && alembic -c alembic.ini -n workspace upgrade head

db-seed:
	@echo "Seeding test data..."
	cd backend && python -m codex.scripts.seed_test_data

db-clean:
	@echo "Cleaning test data..."
	cd backend && python -m codex.scripts.seed_test_data clean

# =============================================================================
# Help
# =============================================================================

help:
	@echo "Codex Build System"
	@echo "=================="
	@echo ""
	@echo "Docker (recommended):"
	@echo "  make              Build plugins + start production containers"
	@echo "  make deploy       Same as above"
	@echo "  make dev-docker   Setup + start development containers (hot-reload)"
	@echo "  make docker-down  Stop containers"
	@echo "  make docker-logs  View container logs"
	@echo "  make docker-restart  Restart after plugin changes"
	@echo "  make docker-rebuild  Full rebuild and restart"
	@echo ""
	@echo "Build:"
	@echo "  make build        Build plugins + frontend"
	@echo "  make build-plugins  Build all plugin Vue components"
	@echo "  make build-plugin PLUGIN=<name>  Build a specific plugin"
	@echo "  make watch-plugins  Watch and rebuild plugins"
	@echo ""
	@echo "Local Development (no Docker):"
	@echo "  make install      Install all dependencies"
	@echo "  make dev          Start backend dev server"
	@echo "  make dev-frontend Start frontend dev server"
	@echo ""
	@echo "Testing:"
	@echo "  make test         Run all tests"
	@echo "  make test-coverage Run tests with coverage"
	@echo "  make test-e2e     Run Chromium E2E tests (Docker)"
	@echo "  make test-e2e-local  Run E2E tests against running containers"
	@echo ""
	@echo "Quality:"
	@echo "  make lint         Run all linters"
	@echo "  make typecheck    Run type checkers"
	@echo "  make format       Format code"
	@echo ""
	@echo "Clean:"
	@echo "  make clean        Clean build artifacts"
	@echo "  make clean-all    Clean everything including Docker"
