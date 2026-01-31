# Codex Build System
# ==================
# Build and development commands for the Codex project.
#
# Quick Start (Docker Deployment):
#   make deploy       - Build plugins and start Docker containers
#   make deploy-prod  - Build and deploy production
#
# Development:
#   make install      - Install all dependencies
#   make dev          - Start development servers
#   make test         - Run all tests

.PHONY: all install build dev test clean help
.PHONY: install-backend install-frontend install-plugins
.PHONY: build-plugins build-frontend
.PHONY: dev-backend dev-frontend
.PHONY: test-backend test-frontend
.PHONY: lint lint-backend lint-frontend
.PHONY: typecheck typecheck-backend typecheck-frontend typecheck-plugins
.PHONY: clean-plugins clean-frontend clean-backend
.PHONY: deploy deploy-prod docker-build docker-up docker-down docker-logs

# Default target - deploy with Docker
all: deploy

# =============================================================================
# Docker Deployment (Primary Use Case)
# =============================================================================

# Build plugins and start Docker development environment
deploy: build-plugins docker-up
	@echo ""
	@echo "Deployment complete!"
	@echo "  Backend:  http://localhost:8765"
	@echo "  Frontend: http://localhost:8065"

# Build plugins and start Docker production environment
deploy-prod: build-plugins docker-build-prod docker-up-prod
	@echo ""
	@echo "Production deployment complete!"

# Build Docker images (rebuilds if Dockerfiles changed)
docker-build: build-plugins
	@echo "Building Docker images..."
	docker compose build

docker-build-prod: build-plugins
	@echo "Building production Docker images..."
	docker compose -f docker-compose.prod.yml build

# Start Docker containers
docker-up:
	@echo "Starting Docker containers..."
	docker compose up -d
	@echo ""
	@echo "Services starting..."
	@echo "  Backend:  http://localhost:8765"
	@echo "  Frontend: http://localhost:8065"
	@echo ""
	@echo "Run 'make docker-logs' to view logs"

docker-up-prod:
	@echo "Starting production Docker containers..."
	docker compose -f docker-compose.prod.yml up -d

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
# Installation (for local development)
# =============================================================================

install: install-backend install-frontend install-plugins
	@echo "All dependencies installed!"

install-backend:
	@echo "Installing backend dependencies..."
	cd backend && pip install -e ".[dev]"

install-frontend:
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

install-plugins:
	@echo "Installing plugin build dependencies..."
	cd plugins && npm install

# =============================================================================
# Build
# =============================================================================

build: build-plugins build-frontend
	@echo ""
	@echo "Build complete!"
	@echo "  - Plugins:  plugins/*/dist/"
	@echo "  - Frontend: frontend/dist/"

build-plugins:
	@if [ ! -d "plugins/node_modules" ]; then \
		echo "Installing plugin dependencies..."; \
		cd plugins && npm install; \
	fi
	@echo "Building plugins..."
	cd plugins && npm run build

build-frontend: build-plugins
	@echo "Building frontend..."
	cd frontend && npm run build

# Watch plugins for changes (development)
watch-plugins:
	@echo "Watching plugins for changes..."
	cd plugins && npm run build:watch

# =============================================================================
# Development (Local, non-Docker)
# =============================================================================

dev: dev-backend
	@echo "Starting development servers..."

dev-backend:
	@echo "Starting backend server on http://localhost:8000..."
	cd backend && python -m codex.main

dev-frontend:
	@echo "Starting frontend dev server on http://localhost:5173..."
	cd frontend && npm run dev

# Run both servers (requires separate terminals)
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
	@echo "Docker Deployment (recommended):"
	@echo "  make              Build plugins and start dev containers"
	@echo "  make deploy       Same as above"
	@echo "  make deploy-prod  Build and start production containers"
	@echo "  make docker-up    Start containers (assumes plugins built)"
	@echo "  make docker-down  Stop containers"
	@echo "  make docker-logs  View container logs"
	@echo "  make docker-restart  Restart after plugin changes"
	@echo "  make docker-rebuild  Full rebuild and restart"
	@echo ""
	@echo "Build Commands:"
	@echo "  make build        Build plugins + frontend"
	@echo "  make build-plugins  Build plugin Vue components only"
	@echo "  make watch-plugins  Watch and rebuild plugins"
	@echo ""
	@echo "Install Commands (local dev):"
	@echo "  make install      Install all dependencies"
	@echo ""
	@echo "Development (local, non-Docker):"
	@echo "  make dev          Start backend dev server"
	@echo "  make dev-frontend Start frontend dev server"
	@echo ""
	@echo "Test Commands:"
	@echo "  make test         Run all tests"
	@echo "  make test-coverage Run tests with coverage"
	@echo ""
	@echo "Quality Commands:"
	@echo "  make lint         Run all linters"
	@echo "  make typecheck    Run type checkers"
	@echo "  make format       Format code"
	@echo ""
	@echo "Clean Commands:"
	@echo "  make clean        Clean build artifacts"
	@echo "  make clean-all    Clean everything including Docker"
	@echo ""
	@echo "Database Commands:"
	@echo "  make db-migrate   Run database migrations"
	@echo "  make db-seed      Seed test data"
