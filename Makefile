# ════════════════════════════════════════════════════════════════════
# oh-my-class — Unified Dev Commands
# ════════════════════════════════════════════════════════════════════
#
# Usage: make <target>
# All commands assume you've run `make setup` first.
#
# ── Daily commands ──
#   make dev          Start local dev: db/redis in Docker + gateway + web locally
#   make docker       Start full Docker dev stack
#   make stop         Stop Docker services
#   make logs         Tail service logs
#   make test         Run all tests (Python + TypeScript)
#   make check        Run tests + build + linters + report format check
#   make lint         Run linters + boundary checks
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

.PHONY: dev clean-ports infra infra-full dev-gateway dev-web dev-all docker stop prod-up prod-down up down logs test test-python test-ts test-integration check lint lint-python lint-ts fmt fmt-reports check-reports check-architecture check-content-intelligence check-content-factory-v2 check-runtime-resilience setup migrate seed reset-db calibrate gen-schemas check-schemas typecheck help

# ── Docker compose path ──
COMPOSE := docker compose -f infra/compose/docker-compose.yml
LOCAL_WEB_PORT := 3100
LOCAL_GATEWAY_PORT := 8101

# ── Local dev ────────────────────────────────────────────────────────────────
dev: ## Start local dev: db/redis in Docker + gateway + web locally
	$(MAKE) infra
	$(MAKE) clean-ports
	$(MAKE) -j2 dev-gateway dev-web

clean-ports: ## Stop local dev servers on local dev ports
	@lsof -tiTCP:$(LOCAL_WEB_PORT) -sTCP:LISTEN | xargs -r kill
	@lsof -tiTCP:$(LOCAL_GATEWAY_PORT) -sTCP:LISTEN | xargs -r kill

infra: ## Start local infrastructure only (db, redis)
	$(COMPOSE) up -d db redis

infra-full: ## Start optional infrastructure (db, redis, langfuse)
	$(COMPOSE) up -d db redis langfuse

dev-gateway: ## Start Python gateway locally on port 8101
	uv run uvicorn services.gateway.main:app --reload --port $(LOCAL_GATEWAY_PORT)

dev-web: ## Start teacher dashboard locally on port 3100
	NEXT_PUBLIC_GATEWAY_URL=http://localhost:$(LOCAL_GATEWAY_PORT) pnpm --filter @oh-my-class/web exec next dev --turbopack -p $(LOCAL_WEB_PORT)

dev-all: dev ## Alias for make dev

# ── Default target ──
.DEFAULT_GOAL := help

# ── Docker ──
docker: ## Start full Docker dev stack
	$(COMPOSE) up -d
	@echo ""
	@echo "Services started:"
	@echo "   Gateway:    http://localhost:8001"
	@echo "   Dashboard:  http://localhost:3000"
	@echo "   Langfuse:   http://localhost:3001"

up: docker ## Alias for make docker

stop: down ## Stop Docker services

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

check: ## Run tests + build + linters + report format check
	$(MAKE) test
	pnpm build
	ruff check .
	uv run lint-imports
	bash scripts/typecheck.sh
	pnpm check:reports

# ── Formatting ──
fmt: ## Format all code
	ruff format .
	pnpm -r format
	pnpm format:reports

fmt-reports: ## Format generated reports and plans
	pnpm format:reports

check-reports: ## Check generated report and plan formatting
	pnpm check:reports

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
	uv run python scripts/generate_theme.py
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
	uv run python scripts/generate_zod_schemas.py

check-schemas: ## Verify schema parity (Pydantic <-> Zod)
	uv run python scripts/verify_schema_parity.py

check-architecture: ## Verify runtime manifest and generated anatomy trace freshness
	uv run pytest tests/test_architecture_sync.py tests/test_system_trace_refs.py tests/test_architecture_truth_gate.py -q
	uv run python scripts/check_architecture_truth.py
	uv run python scripts/verify_doc_refs.py

check-content-intelligence: ## #465: Content Intelligence Graph contract/integrity/tenant-isolation tests
	uv run pytest common/contracts/tests/content_intelligence_graph -q

check-specialist-registry: ## #464: fail-closed capability resolution + SpecialistModule registry-matrix/contract tests
	uv run pytest \
		packages/agents/tests/teaching_pack/test_specialist_capability.py \
		packages/agents/tests/teaching_pack/test_specialist_registry.py \
		packages/agents/tests/teaching_pack/test_specialist_module.py \
		packages/agents/tests/teaching_pack/test_content_coverage_resolution.py \
		packages/agents/tests/teaching_pack/test_content_orchestrator.py \
		packages/agents/tests/teaching_pack/test_generate_one_artifact.py \
		common/contracts/tests/test_dependency_plan.py \
		common/contracts/tests/test_strategy_review.py \
		packages/agents/tests/test_scoped_repair_loop.py \
		-v

check-content-factory-v2: ## #464-#469: typed briefs, deep specialists, tenancy, coherence
	uv run pytest \
		common/contracts/tests/content_factory \
		packages/agents/tests/teaching_pack/test_content_factory_depth.py \
		packages/agents/tests/teaching_pack/test_tenant_scoped_content_store.py \
		packages/agents/tests/teaching_pack/test_artifact_fanout_payload.py \
		-q

check-runtime-resilience: ## #471/#472: outbox replay and worker/job safety regression
	uv run pytest \
		services/gateway/tests/test_run_event_outbox.py \
		services/gateway/tests/test_teaching_pack_store.py \
		services/gateway/tests/test_teaching_pack_worker.py \
		services/gateway/tests/test_multi_worker_no_double_claim.py \
		services/gateway/tests/test_idempotent_reclaim.py \
		-q

# ── Help ──
help: ## Show this help message
	@echo "oh-my-class dev commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Run 'make setup' first, then 'make dev' for local dev or 'make docker' for Docker."
