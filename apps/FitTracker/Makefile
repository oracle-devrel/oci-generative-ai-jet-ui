# FitTrack Makefile
# Development commands for the FitTrack application

.PHONY: help setup dev stop logs test test-unit test-integration test-cov \
        db-migrate db-seed db-reset lint format typecheck clean

# Default target
help:
	@echo "FitTrack Development Commands"
	@echo "=============================="
	@echo ""
	@echo "Setup & Run:"
	@echo "  make setup          - First-time setup (creates .env, installs deps)"
	@echo "  make dev            - Start all services (Oracle, Redis, API)"
	@echo "  make dev-api        - Start API only (requires Oracle & Redis running)"
	@echo "  make stop           - Stop all services"
	@echo "  make logs           - View logs from all services"
	@echo "  make logs-api       - View API logs only"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-cov       - Run tests with coverage report"
	@echo "  make test-watch     - Run tests in watch mode"
	@echo ""
	@echo "Database:"
	@echo "  make db-migrate     - Run pending migrations"
	@echo "  make db-seed        - Seed database with synthetic data"
	@echo "  make db-reset       - Drop and recreate database with seed data"
	@echo "  make db-shell       - Open Oracle SQL shell"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           - Run linter (ruff)"
	@echo "  make format         - Format code (black, isort)"
	@echo "  make typecheck      - Run type checker (mypy)"
	@echo "  make check          - Run all checks (lint, typecheck, test)"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean          - Remove generated files"
	@echo "  make shell          - Open Python shell with app context"

# =============================================================================
# Setup & Run
# =============================================================================

setup:
	@echo "Setting up FitTrack development environment..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env from .env.example"; \
	fi
	pip install -e ".[dev]"
	pre-commit install || true
	@echo ""
	@echo "Setup complete! Run 'make dev' to start services."

dev:
	@echo "Starting FitTrack services..."
	docker compose up -d
	@echo ""
	@echo "Services starting..."
	@echo "  API:     http://localhost:8000"
	@echo "  Docs:    http://localhost:8000/docs"
	@echo "  DevTools: http://localhost:8000/devtools"
	@echo "  Mailpit: http://localhost:8025"
	@echo ""
	@echo "Run 'make logs' to view logs"

dev-api:
	@echo "Starting API server (hot-reload)..."
	PYTHONPATH=src uvicorn fittrack.main:app --reload --host 0.0.0.0 --port 8000

stop:
	@echo "Stopping FitTrack services..."
	docker compose down

logs:
	docker compose logs -f

logs-api:
	docker compose logs -f api

# =============================================================================
# Testing
# =============================================================================

test:
	@echo "Running all tests..."
	PYTHONPATH=src pytest tests/ -v

test-unit:
	@echo "Running unit tests..."
	PYTHONPATH=src pytest tests/unit/ -v -m "unit or not integration"

test-integration:
	@echo "Running integration tests..."
	PYTHONPATH=src pytest tests/integration/ -v -m integration

test-cov:
	@echo "Running tests with coverage..."
	PYTHONPATH=src pytest tests/ --cov=fittrack --cov-report=html --cov-report=term-missing
	@echo ""
	@echo "Coverage report: htmlcov/index.html"

test-watch:
	@echo "Running tests in watch mode..."
	PYTHONPATH=src pytest-watch tests/ -- -v

# =============================================================================
# Database
# =============================================================================

db-migrate:
	@echo "Running database migrations..."
	PYTHONPATH=src python -m fittrack.db.migrate

db-seed:
	@echo "Seeding database with synthetic data..."
	PYTHONPATH=src python scripts/seed_data.py

db-reset:
	@echo "Resetting database..."
	PYTHONPATH=src python scripts/reset_db.py
	@echo "Running migrations..."
	PYTHONPATH=src python -m fittrack.db.migrate
	@echo "Seeding database..."
	PYTHONPATH=src python scripts/seed_data.py
	@echo "Database reset complete!"

db-shell:
	@echo "Opening Oracle SQL shell..."
	docker compose exec oracle sqlplus fittrack/FitTrack2026!@//localhost:1521/FREEPDB1

# =============================================================================
# Code Quality
# =============================================================================

lint:
	@echo "Running linter..."
	ruff check src/ tests/
	@echo "Lint passed!"

lint-fix:
	@echo "Fixing lint issues..."
	ruff check src/ tests/ --fix

format:
	@echo "Formatting code..."
	black src/ tests/
	isort src/ tests/
	@echo "Formatting complete!"

typecheck:
	@echo "Running type checker..."
	mypy src/

check: lint typecheck test
	@echo ""
	@echo "All checks passed!"

# =============================================================================
# Utilities
# =============================================================================

clean:
	@echo "Cleaning generated files..."
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	rm -rf htmlcov .coverage coverage.xml
	rm -rf dist build *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Clean complete!"

shell:
	@echo "Opening Python shell..."
	PYTHONPATH=src python -c "from fittrack.main import app; import code; code.interact(local=locals())"
