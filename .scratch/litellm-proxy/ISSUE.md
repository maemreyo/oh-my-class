---
title: "LiteLLM Proxy: P2+FB3+DC2 — 2-Layer Gateway, f.light/f.pro, Compose Override"
status: deferred
labels: [infrastructure, llm, deployment]
created: 2026-06-24
priority: p2
report: "04"
---

> **Deferred (p2):** Not needed for local dev. User calls 9Router directly
> (`LLM_CLIENT_BASE_URL=http://localhost:20128`). Implement only when preparing
> production deployment. See `9router-integration/ISSUE.md` for local dev setup.

## What to build

LiteLLM proxy configuration for production deployment. Exposes `f.light` and `f.pro` as virtual model names (agents never see provider names). Routes to 9Router sidecar for execution. Docker Compose base + prod override pattern for local vs production.

**Design decisions:**
- **P2**: 2-layer — LiteLLM (port 4000) → 9Router (port 20128) → providers
- **CA-A**: `LLM_CLIENT_BASE_URL` selects endpoint — local uses 9Router directly
- **FB3**: LiteLLM handles infra/provider errors; `healing_node` handles content errors
- **DC2**: `docker-compose.yml` base + `docker-compose.prod.yml` override
- **f.light/f.pro**: model names consistent with `gate-config` MODELS

## File Structure

```
infra/litellm/
├── config.yaml              # LiteLLM config — f.light/f.pro → 9Router
├── .env.example             # all env vars documented
└── scripts/
    ├── create-keys.sh       # create virtual keys per agent
    └── health-check.sh      # verify proxy is up

docker-compose.yml           # base: app + 9router (local dev)
docker-compose.prod.yml      # override: + litellm + postgres + redis
.env.local                   # local defaults
.env.production              # production template (no secrets — committed)
```

## Implementation Spec

### `infra/litellm/config.yaml`

```yaml
# ================================================================
# oh-my-class LiteLLM Proxy Configuration
# All agents use f.light or f.pro — never provider-specific names
# ================================================================

model_list:
  # f.light — fast, cheap tasks (summarization, title, light review)
  - model_name: f.light
    litellm_params:
      model: openai/f.light          # 9Router resolves this
      api_base: http://9router:20128/v1
      api_key: os.environ/NINE_ROUTER_API_KEY
    model_info:
      description: "Fast/cheap model via 9Router — summarization, title, light tasks"

  # f.pro — heavy tasks (content generation, judgment, fact verification)
  - model_name: f.pro
    litellm_params:
      model: openai/f.pro            # 9Router resolves this
      api_base: http://9router:20128/v1
      api_key: os.environ/NINE_ROUTER_API_KEY
    model_info:
      description: "High-quality model via 9Router — generation, reasoning, judgment"

# === ROUTER SETTINGS ===
router_settings:
  routing_strategy: simple-shuffle
  enable_pre_call_checks: true

  redis_host: os.environ/REDIS_HOST
  redis_port: os.environ/REDIS_PORT
  redis_password: os.environ/REDIS_PASSWORD

  # FB3: LiteLLM handles infra/provider errors only
  # healing_node handles content/quality errors at application level
  allowed_fails: 3          # fails before cooldown
  cooldown_time: 30         # seconds in cooldown

  retry_policy:
    AuthenticationErrorRetries: 0    # never retry auth errors
    TimeoutErrorRetries: 2
    RateLimitErrorRetries: 3
    InternalServerErrorRetries: 2

# === LITELLM SETTINGS ===
litellm_settings:
  num_retries: 2
  request_timeout: 120
  drop_params: true          # ignore unknown params gracefully
  json_logs: true

  # L1 exact-match Redis cache (built-in LiteLLM feature)
  cache: true
  cache_params:
    type: redis
    host: os.environ/REDIS_HOST
    port: os.environ/REDIS_PORT
    password: os.environ/REDIS_PASSWORD
    ttl: 3600              # 1 hour cache TTL

  # FB3 fallback: only for provider-level failures
  # These are infra fallbacks — not content quality decisions
  fallbacks:
    - f.light: ["f.pro"]   # if f.light provider errors → try f.pro
    # f.pro has no fallback — if it fails, healing_node handles escalation

# === GENERAL SETTINGS ===
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: os.environ/DATABASE_URL
  alerting: []               # no Slack locally — add "slack" in production
  proxy_batch_write_at: 60
  allow_requests_on_db_unavailable: true
```

### `docker-compose.yml` (base — local dev)

```yaml
# Local development: just 9router + app
# Run with: docker compose up

services:
  9router:
    image: 9router/9router:latest
    restart: unless-stopped
    ports:
      - "20128:20128"
    volumes:
      - ./infra/9router/config.yaml:/app/config.yaml:ro
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:20128/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build:
      context: .
      dockerfile: Dockerfile
    restart: unless-stopped
    depends_on:
      9router: { condition: service_healthy }
    env_file: .env.local
    environment:
      LLM_CLIENT_BASE_URL: http://9router:20128   # direct to 9Router locally
    volumes:
      - .:/app
    ports:
      - "8000:8000"

volumes:
  pgdata:
  redis_data:
```

### `docker-compose.prod.yml` (override — production)

```yaml
# Production overlay: add LiteLLM + Postgres + Redis
# Run with: docker compose -f docker-compose.yml -f docker-compose.prod.yml up

services:
  db:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_USER: litellm
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: litellm
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U litellm -d litellm"]
      interval: 5s
      retries: 10

  redis:
    image: redis:7-alpine
    restart: always
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      retries: 10

  litellm:
    image: ghcr.io/berriai/litellm-database:main-stable
    restart: always
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }
      9router: { condition: service_healthy }
    ports:
      - "4000:4000"
    volumes:
      - ./infra/litellm/config.yaml:/app/config.yaml:ro
    command: ["--config", "/app/config.yaml", "--port", "4000"]
    env_file: .env.production
    environment:
      DATABASE_URL: postgresql://litellm:${POSTGRES_PASSWORD}@db:5432/litellm
      REDIS_HOST: redis
      REDIS_PORT: "6379"
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:4000/health/readiness || exit 1"]
      interval: 15s
      timeout: 10s
      retries: 5
      start_period: 30s

  # Override app to use LiteLLM in production
  app:
    depends_on:
      litellm: { condition: service_healthy }
    environment:
      LLM_CLIENT_BASE_URL: http://litellm:4000  # via LiteLLM in production
```

### `.env.local` (committed — no secrets)

```bash
# Local development defaults
LLM_CLIENT_BASE_URL=http://localhost:20128
LLM_CLIENT_API_KEY=dummy
LLM_CLIENT_TIMEOUT_S=120

NINE_ROUTER_API_KEY=local-dev-key

# Gate config
GATE_JUDGE_MIN_SCORE=7.0
GATE_MAX_RETRIES=3
```

### `.env.production` (template — committed, no secrets)

```bash
# Production template — fill secrets in CI/CD or secrets manager
LLM_CLIENT_BASE_URL=http://litellm:4000
LLM_CLIENT_API_KEY=${LITELLM_AGENT_KEY}    # virtual key from create-keys.sh

LITELLM_MASTER_KEY=                        # fill in deployment
LITELLM_SALT_KEY=                          # fill in deployment
NINE_ROUTER_API_KEY=                       # fill in deployment
POSTGRES_PASSWORD=                         # fill in deployment

REDIS_HOST=redis
REDIS_PORT=6379

# Gate config (production values)
GATE_JUDGE_MIN_SCORE=7.0
GATE_MAX_RETRIES=3
GATE_RESPONSIVE_CHECK_ENABLED=true
```

### `infra/litellm/scripts/create-keys.sh`

```bash
#!/bin/bash
# Create virtual keys per agent type for cost attribution

BASE_URL="http://localhost:4000"
MASTER_KEY="${LITELLM_MASTER_KEY}"

create_key() {
  local alias="$1"
  local models="$2"
  local budget="$3"

  curl -s -X POST "${BASE_URL}/key/generate" \
    -H "Authorization: Bearer ${MASTER_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
      \"key_alias\": \"${alias}\",
      \"models\": ${models},
      \"max_budget\": ${budget},
      \"budget_duration\": \"1mo\",
      \"rpm_limit\": 100
    }" | python3 -c "import sys, json; print(json.load(sys.stdin)['key'])"
}

echo "Creating virtual keys..."
echo "content-creator: $(create_key 'content-creator' '["f.pro"]' 50)"
echo "llm-judge:       $(create_key 'llm-judge'       '["f.pro"]' 30)"
echo "fact-checker:    $(create_key 'fact-checker'     '["f.pro"]' 20)"
echo "summarizer:      $(create_key 'summarizer'       '["f.light"]' 10)"
echo "Done. Add keys to .env.production"
```

## Quick Start

```bash
# Local dev (just 9Router)
docker compose up -d
# → LLM_CLIENT_BASE_URL=http://9router:20128 (set in docker-compose.yml)

# Production (full stack)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
bash infra/litellm/scripts/create-keys.sh
# → LLM_CLIENT_BASE_URL=http://litellm:4000 (set in docker-compose.prod.yml)
```

## Acceptance Criteria

- [ ] `config.yaml` — models named `f.light` and `f.pro` (no provider names visible to agents)
- [ ] Both `f.light` and `f.pro` route through `http://9router:20128/v1`
- [ ] `f.light` has fallback to `f.pro` for provider errors (FB3: infra only)
- [ ] `f.pro` has no fallback — `healing_node` handles application-level escalation
- [ ] `docker-compose.yml` — local: 9router + app, zero LiteLLM infra
- [ ] `docker-compose.prod.yml` — override adds LiteLLM + Postgres + Redis
- [ ] Switching local→production = `docker compose -f ... -f ...` only
- [ ] `.env.local` committed (safe defaults), `.env.production` template committed (no secrets)
- [ ] `create-keys.sh` creates per-agent virtual keys for cost attribution
- [ ] `LLM_CLIENT_BASE_URL` is the single switch between local and production

## Dependencies

- Blocked by: `llm-client` (LLMClientConfig reads LLM_CLIENT_BASE_URL)
- Blocks: production deployment
- Priority: p1 — needed for production, not for local dev
