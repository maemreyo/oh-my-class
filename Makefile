# ════════════════════════════════════════════════════════════════════
# oh-my-class — Unified Dev Commands
# ════════════════════════════════════════════════════════════════════
#
# Usage: make <target>
# All commands assume you've run `make setup` first.
#
# ── Daily commands ──
#   make up           Start dev stack (db, redis, litellm, 9router, gateway, web)
#   make down         Stop all services
#   make logs         Tail service logs
#   make test         Run all tests (Python + TypeScript)
#   make lint         Run all linters + boundary checks
#   make fmt          Format all code
#
# ── Setup ──
#   make setup        Bootstrap dev environment (first time)
#   make migrate      Run database migrations
#   make seed         Seed question bank (500+ items)
#
# ── Database ──
#   make reset-db     Delete DB volume (local only!)
#
# ── Quality ──
#   make calibrate    Cohen's κ calibration for Layer 4 judge
#
# ── Schema ──
#   make gen-schemas  Generate Zod schemas from Pydantic
#   make check-schemas Verify schema parity (Pydantic ↔ Zod)
# ════════════════════════════════════════════════════════════════════

.PHONY: dev dev-frontend dev-all prod-up prod-down up down logs test test-python test-ts test-integration lint lint-python lint-ts fmt setup migrate seed reset-db calibrate gen-schemas check-schemas typecheck help

# ── Docker compose path ──
COMPOSE := docker compose -f infra/compose/docker-compose.yml

# ── Local dev (no Docker — assumes 9Router on :20128) ──────────────────────
dev: ## Start Python gateway (port 8001 — 9Router must be running on :20128)
	uv run uvicorn services.gateway.main:app --reload --port 8001

dev-frontend: ## Start teacher dashboard (Next.js on port 3000)
	cd apps/web && npm run dev

dev-all: ## Start Python gateway + frontend concurrently
	$(MAKE) -j2 dev dev-frontend

# ── Production ──────────────────────────────────────────────────────────────
prod-up: ## Start full production stack (LiteLLM + Postgres + Redis + app)
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-down: ## Stop production stack
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down

# ── Default target ──
.DEFAULT_GOAL := help

# ── Docker ──
up: ## Start dev stack (db, redis, litellm, 9router, gateway, web)
	$(COMPOSE) up -d
	@echo ""
	@echo "Services started:"
	@echo "   Gateway:    http://localhost:8001"
	@echo "   Dashboard:  http://localhost:3000"
	@echo "   LiteLLM:    http://localhost:4000"
	@echo "   9Router:    http://localhost:20128"

down: ## Stop all services
	$(COMPOSE) down

logs: ## Tail service logs (last 100 lines)
	$(COMPOSE) logs -f --tail=100

# ── Testing ──
test: ## Run all tests (Python + TypeScript)
	@echo "Running Python tests..."
	uv run pytest packages/agents packages/quality common/contracts services/gateway tests/ -v
	@echo ""
	@echo "Running TypeScript tests..."
	pnpm -r test
	@echo ""
	@echo "All tests passed"

test-python: ## Run Python tests only
	uv run pytest packages/agents packages/quality common/contracts services/gateway tests/ -v

test-ts: ## Run TypeScript tests only
	pnpm -r test

test-integration: ## Run integration tests only
	uv run pytest tests/integration/ -v

# ── Linting ──
lint: ## Run all linters + boundary checks
	@echo "Python linting..."
	ruff check .
	lint-imports
	bash scripts/typecheck.sh
	@echo ""
	@echo "TypeScript linting..."
	pnpm -r lint
	pnpm depcruise --validate .dependency-cruiser.cjs .
	@echo ""
	@echo "All linters passed"

lint-python: ## Python linting only
	ruff check .
	lint-imports
	bash scripts/typecheck.sh

lint-ts: ## TypeScript linting only
	pnpm -r lint
	pnpm depcruise --validate .dependency-cruiser.cjs .

typecheck: ## Run basedpyright type check
	bash scripts/typecheck.sh

# ── Formatting ──
fmt: ## Format all code
	ruff format .
	pnpm -r format

# ── Setup ──
setup: ## Bootstrap dev environment (first time)
	@echo "Setting up oh-my-class development environment..."
	@if [ ! -f .env ]; then \
		echo "Copying .env.example to .env..."; \
		cp .env.example .env; \
		echo "Edit .env with your API keys before running 'make up'"; \
	fi
	@echo ""
	@echo "Setting up Python workspace..."
	uv sync || pip install -e packages/agents -e packages/quality -e common/contracts -e services/gateway
	@echo ""
	@echo "Installing TypeScript dependencies..."
	pnpm install
	@echo ""
	@echo "Generating theme CSS..."
	python scripts/generate_theme.py
	@echo ""
	@echo "Setup complete! Run 'make up' to start services."

# ── Database ──
migrate: ## Run Alembic migrations
	cd services/gateway && uv run alembic upgrade head

seed: ## Seed question bank (500+ items)
	uv run python scripts/seed_questions.py

reset-db: ## Delete DB volume (LOCAL ONLY!)
	@echo "This will DELETE all data in the database!"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	$(COMPOSE) down -v
	@echo "Database volume deleted"

# ── Quality ──
calibrate: ## Cohen's kappa calibration for Layer 4 judge
	uv run python packages/quality/calibrate.py

# ── Schema ──
gen-schemas: ## Generate Zod schemas from Pydantic
	python scripts/generate_zod_schemas.py

check-schemas: ## Verify schema parity (Pydantic <-> Zod)
	python scripts/verify_schema_parity.py

# ── Help ──
help: ## Show this help message
	@echo "oh-my-class dev commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Run 'make setup' first, then 'make up' to start."
