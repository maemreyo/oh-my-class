---
title: "9Router Integration: Combo f.light/f.pro, Config Export, Makefile Dev Workflow"
status: superseded
labels: [infrastructure, llm, developer-experience]
created: 2026-06-24
superseded: 2026-07-08
priority: p1
report: "05"
---

> **Superseded (2026-07-08):** 9Router :20128 with `f.light`/`f.pro` combos via
> Kiro AI free tier is no longer in use. The project now runs 9Router directly
> at `:20228` with model alias `4omc` (see `.env.example`,
> `packages/llm_client/config.py`). `infra/9router/` was removed 2026-07-08.
> Kept here only as historical record.

## What to build

9Router integration layer for oh-my-class. User already has 9Router running locally with `f.light`/`f.pro` combos configured (used daily in OpenCode). App calls 9Router directly at `http://localhost:20128` — no LiteLLM needed for local dev. Commit a stripped config export so contributors can import combos quickly.

**Design decisions:**
- **MN2-combo**: `f.light`/`f.pro` are 9Router combo names — not LiteLLM aliases, not code-level translation
- **FC1**: No separate fusion combo — `f.pro` combo is sufficient for all high-quality tasks
- **RD1**: Use existing local 9Router instance — no containerization for local dev
- **LP1**: LiteLLM demoted to p2, production-only (see `litellm-proxy/ISSUE.md`)
- **AM1**: No `AGENT_MODEL_CONFIG` dict — use `MODELS` from `gate-config` directly
- **RK1**: RTK Token Compression transparent — 9Router applies automatically, no app changes
- **OB1**: Commit `infra/9router/config-export.json` (secrets stripped) for fast onboarding
- **DN1 + Makefile**: Local dev = run app directly (`uvicorn`/`npm dev`), not in Docker

## File Structure

```
infra/9router/
├── config-export.json     # stripped 9Router config (no secrets) — import via dashboard
└── README.md              # setup: install, import config, set .env.local

Makefile                   # root-level dev/prod commands
```

**Updates to existing files:**
- `litellm-proxy/ISSUE.md` → priority: p2, note: production-only
- `.env.local` → `LLM_CLIENT_API_KEY=dummy` (user runs 9Router without auth enforcement)
- `docker-compose.yml` → remove 9Router service (RD1: external to Docker)

## Implementation Spec

### `infra/9router/config-export.json`

Exported from 9Router dashboard → stripped of all secrets (provider API keys, passwords).
Structure preserves: combo definitions, routing rules, model mappings.

```json
{
  "_export_version": "1",
  "_note": "Secrets stripped. Add provider API keys via dashboard after import.",
  "combos": [
    {
      "name": "f.light",
      "models": ["<provider>/cheapest-model"],
      "strategy": "round-robin"
    },
    {
      "name": "f.pro",
      "models": ["<provider>/best-model"],
      "strategy": "round-robin"
    }
  ],
  "routing_rules": []
}
```

> **Note:** Commit the actual export from user's running 9Router instance. Replace placeholder model names with real ones after export. Strip `apiKey`, `password`, `token` fields before committing.

### `infra/9router/README.md`

```markdown
# 9Router Setup

oh-my-class uses 9Router as the local LLM gateway. `f.light` and `f.pro`
are combos configured in 9Router — the app never sees provider names.

## Prerequisites

9Router running on port 20128:
\`\`\`bash
npm i -g 9router@latest && 9router
# → dashboard at http://localhost:20128/dashboard
\`\`\`

## Import config

1. Open http://localhost:20128/dashboard
2. Settings → Import Config → select `infra/9router/config-export.json`
3. Add your provider credentials (Kiro AI, OpenAI, Anthropic) via Providers tab
4. Verify `f.light` and `f.pro` combos appear under Combos tab

## Docker image (for future production use)

Official image: `decolua/9router:latest`
Command: `npm i -g 9router@latest && 9router` (no `start` subcommand)

## .env.local

\`\`\`bash
LLM_CLIENT_BASE_URL=http://localhost:20128
LLM_CLIENT_API_KEY=dummy   # no auth enforcement needed for local dev
\`\`\`
```

### `Makefile` (root)

```makefile
.PHONY: dev dev-frontend dev-all prod-up prod-down test lint

# ── Local dev ──────────────────────────────────────────────────────────────
dev:          ## Start Python API (assumes 9Router on :20128)
	uvicorn packages.app.main:app --reload --port 8000

dev-frontend: ## Start teacher dashboard (Next.js)
	cd packages/dashboard && npm run dev

dev-all:      ## Start Python API + frontend concurrently
	make -j2 dev dev-frontend

# ── Production ─────────────────────────────────────────────────────────────
prod-up:      ## Start full production stack (LiteLLM + Postgres + Redis + app)
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-down:    ## Stop production stack
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down

# ── Quality ────────────────────────────────────────────────────────────────
test:         ## Run full test suite
	pytest packages/ -x -q

lint:         ## Type check + lint
	pyright packages/
	cd packages/dashboard && npm run type-check
```

### `docker-compose.yml` (updated — remove 9Router service)

```yaml
# Local production reference: app only
# For local dev, use: make dev-all
# 9Router runs separately on host (see infra/9router/README.md)

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    restart: unless-stopped
    env_file: .env.local
    ports:
      - "8000:8000"
    # Note: LLM_CLIENT_BASE_URL must point to host's 9Router
    # Mac/Windows: http://host.docker.internal:20128
    # Linux: use --network=host or add extra_hosts
```

### `.env.local` (updated)

```bash
# Local dev — safe to commit (no secrets)

# LLM
LLM_CLIENT_BASE_URL=http://localhost:20128   # 9Router direct
LLM_CLIENT_API_KEY=dummy                     # 9Router runs without auth locally
LLM_CLIENT_TIMEOUT_S=120

# Gate config
GATE_JUDGE_MIN_SCORE=7.0
GATE_MAX_RETRIES=3
```

### `litellm-proxy/ISSUE.md` update

Change frontmatter:
```yaml
priority: p2
status: deferred
```
Add note at top of file:
```
> **Deferred (p2):** Not needed for local dev. Implement only when preparing
> production deployment. Local dev uses 9Router direct via LLM_CLIENT_BASE_URL.
```

## `gate-config` MODELS stays as-is

`AGENT_MODEL_CONFIG` from Report 05 is dropped. `MODELS` from `gate-config` is the single source of truth:

```python
# packages/agents/config.py — no change needed
MODELS = ModelConfig(
    content_generation = "f.pro",
    quality_gate       = "f.pro",
    fact_verification  = "f.pro",
    blueprint_design   = "f.pro",
    summarization      = "f.light",
    title_generation   = "f.light",
    schema_rewrite     = "f.light",
)
```

## Onboarding Flow (new contributor)

```bash
# 1. Install + start 9Router
npm i -g 9router@latest && 9router

# 2. Import config
# → http://localhost:20128/dashboard → Settings → Import → infra/9router/config-export.json
# → Add provider credentials (Kiro AI free tier: AWS Builder ID login)

# 3. Copy env
cp .env.local .env

# 4. Start dev
make dev         # Python API on :8000
make dev-all     # Python API + frontend
```

## Acceptance Criteria

- [ ] `infra/9router/config-export.json` — committed, secrets stripped, importable via dashboard
- [ ] `infra/9router/README.md` — install, import, .env.local instructions
- [ ] `Makefile` — `make dev`, `make dev-all`, `make prod-up`, `make test`, `make lint`
- [ ] `docker-compose.yml` — 9Router service removed (RD1)
- [ ] `.env.local` — `LLM_CLIENT_API_KEY=dummy`, `LLM_CLIENT_BASE_URL=http://localhost:20128`
- [ ] `litellm-proxy/ISSUE.md` — demoted to p2 with deferred note
- [ ] New contributor can onboard in < 5 minutes following README
- [ ] `AGENT_MODEL_CONFIG` does NOT appear anywhere in codebase

## Dependencies

- Blocked by: nothing — infra/config only
- Blocks: all local dev workflows (every agent needs 9Router reachable)
- Priority: p1 — first thing to set up before any agent development
