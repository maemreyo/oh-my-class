# Báo cáo Kỹ thuật 04: Hạ tầng LLM Proxy & Tối ưu Chi phí

> **Mục tiêu**: Thiết kế hệ thống LLM Proxy 2-layer (LiteLLM → 9Router → Providers), model routing, và cost optimization cho oh-my-class.
>
> **Phiên bản**: 1.1 | **Ngày**: 2026-06-23 | **Cập nhật**: Thêm kiến trúc 2-layer với 9Router sidecar

---

## Mục lục

1. [Tổng quan LLM Proxy Frameworks](#1-tổng-quan-llm-proxy-frameworks)
2. [So sánh LiteLLM vs OneAPI vs Portkey](#2-so-sánh-litellm-vs-oneapi-vs-portkey)
3. [Model Routing Strategies](#3-model-routing-strategies)
4. [Caching & Cost Management](#4-caching--cost-management)
5. [Cấu hình Production cho oh-my-class](#5-cấu-hình-production-cho-oh-my-class)
6. [Model-to-Agent Mapping](#6-model-to-agent-mapping)
7. [Docker Compose Deployment](#7-docker-compose-deployment)
8. [Client Code & Integration](#8-client-code--integration)

---

## 1. Tổng quan LLM Proxy Frameworks

### 1.1 Tại sao cần 2-Layer Architecture?

oh-my-class sử dụng kiến trúc **2-layer proxy**:

```
Layer 1: LiteLLM (Primary Gateway)
  → Virtual key management, budget control, cost tracking
  → Fallback chains, retry logic, Slack alerts

Layer 2: 9Router (Sidecar Gateway)
  → RTK token compression (20-40% savings)
  → Free-tier aggregation (Kiro AI, Vertex, OpenCode Free)
  → Combo routing (fusion, round-robin)
```

**Tại sao 2 layer thay vì 1?**

| Layer | Responsibility | Không có nó thì... |
|-------|---------------|-------------------|
| LiteLLM | Budget control, per-key limits, cost alerts | Không track được chi phí per-agent |
| 9Router | Token compression, free tiers, combo routing | Mất 20-40% token savings + free tier access |

### 1.2 Kiến trúc Tổng thể — 2-Layer

```
┌──────────────────────────────────────────────────────────────┐
│                    oh-my-class Agents                         │
│              (Python — LangGraph pipeline)                    │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│              LiteLLM Proxy (Primary, port 4000)               │
│                                                               │
│  • Virtual keys per agent ($100/month budget each)           │
│  • Cost tracking → Slack alerts                              │
│  • Fallback chains → retry → cooldown                        │
│  • Redis caching (exact-match)                               │
│  • Per-agent cost attribution via tags                       │
└───────────────────────────┬──────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐  ┌──────────────────┐  ┌──────────────┐
│   Direct     │  │   9Router        │  │   Direct     │
│   Providers  │  │   (Sidecar)      │  │   Providers  │
│              │  │   port 20128     │  │              │
│  • DeepSeek  │  │                  │  │  • Anthropic │
│  • OpenAI    │  │  • RTK Compress  │  │  • Custom    │
│              │  │  • Free Tiers    │  │  • Other     │
│              │  │  • Combo/Fusion  │  │              │
└──────────────┘  └────────┬─────────┘  └──────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌──────────┐ ┌──────────┐ ┌──────────┐
       │ Kiro AI  │ │ Vertex   │ │ OpenCode │
       │ (Free)   │ │ ($300)   │ │ (Free)   │
       └──────────┘ └──────────┘ └──────────┘
```

### 1.3 Flow chi tiết — 1 request qua 2 layer

```
1. Agent gọi LiteLLM: client.chat.completions.create(model="deepseek-free")
2. LiteLLM lookup: model "deepseek-free" → api_base: http://9router:20128/v1
3. LiteLLM forward request sang 9Router với api_key
4. 9Router nhận request → resolve "deepseek/deepseek-chat"
5. 9Router RTK compress tool outputs (nếu có)
6. 9Router check free tier → route đến Kiro AI (free)
7. Kiro AI respond → 9Router translate format → stream back
8. LiteLLM nhận response → log cost (cost=0 for free tier)
9. Agent nhận response
```

### 1.4 Multi-agent system như oh-my-class sử dụng nhiều model (DeepSeek, GPT-4o, Claude) cho các task khác nhau. LLM Proxy cung cấp:

- **Unified API**: Tất cả agents gọi cùng 1 endpoint, proxy route đến đúng provider
- **Cost Tracking**: Theo dõi chi phí per-agent, per-task, per-user
- **Fallback Chains**: Khi provider A fail → tự động chuyển provider B

### 1.2 Kiến trúc Tổng thể

```
┌──────────────┐     ┌────────────────────────────────────────────────┐
│  oh-my-class │     │           LLM Proxy (port 4000)                │
│   Agents     │────▶│                                                │
│              │     │  Router → Cost-Based / Latency-Based           │
│  DraftAgent  │     │  ↓                                             │
│  QualityGate │     │  Fallback Chain → Cooldown → Retry             │
│  CodeAgent   │     │  ↓                                             │
│  EvalAgent   │     │  Cost Tracker → DB (spend tracking)            │
└──────────────┘     └──────┬────────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                  ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │  DeepSeek    │  │   OpenAI     │  │  Anthropic   │
  │  V4-Flash    │  │   GPT-5.4   │  │  Sonnet 4.6  │
  │  ($0.14/$0.28)│  │  ($2.50/$10) │  │  ($3/$15)    │
  │  Drafting    │  │  Quality Gate│  │  Code/Reason │
  └──────────────┘  └──────────────┘  └──────────────┘
```

---

## 2. So sánh LiteLLM vs OneAPI vs Portkey

### 2.1 Ma trận So sánh Tổng quan

| Dimension | **LiteLLM** | **OneAPI** | **Portkey** |
|-----------|-------------|------------|-------------|
| **License** | MIT (core) | MIT | Apache 2.0 (gateway) |
| **Language** | Python | Go | Node.js |
| **GitHub Stars** | 47.8k+ | 35k+ | 25k+ |
| **Self-host** | ✅ Docker | ✅ Single binary | ✅ (enterprise) |
| **Providers** | 100+ | 50+ (strong CN) | 250+ models |
| **Routing** | 5 strategies | Weighted + pinning | Conditional + nestable |
| **Semantic Caching** | ❌ (simple Redis) | ❌ | ✅ Built-in (Pro+) |
| **Guardrails** | Via plugins | ❌ | ✅ 50+ built-in |
| **Cost Tracking** | ✅ Per-key/user/team | ✅ Quota-based | ✅ Per-request |
| **UI Dashboard** | Functional | ✅ Full web | ✅ Polished |
| **Latency overhead** | ~8ms P95 | Minimal (Go) | <1ms claimed |
| **Best for** | Python multi-agent | Chinese ecosystem | Enterprise compliance |

### 2.2 Khuyến nghị: LiteLLM

**Lý do chọn LiteLLM cho oh-my-class:**

1. **Python-native** — oh-my-class agents là Python, LiteLLM integrate trực tiếp
2. **Cost tracking per-agent** — Virtual keys + metadata tags solve this natively
3. **100+ providers** — DeepSeek, OpenAI, Anthropic, Google — tất cả supported
4. **Self-hosted Docker** — Chi phí $0 gateway markup
5. **Production-proven** — 1,000 RPS load-tested on single instance
6. **Config-driven** — YAML controls everything, không cần code changes

---

## 3. Model Routing Strategies

### 3.1 Routing Strategy Matrix (LiteLLM)

| Strategy | Algorithm | Best For | Trade-off |
|----------|-----------|----------|-----------|
| **simple-shuffle** (default) | Random weighted distribution | General production | Ignores actual performance |
| **least-busy** | Routes to fewest active requests | High concurrency | Slightly higher p99 |
| **latency-based** | Picks fastest responder (sliding window) | Latency-critical apps | May overload fast responders |
| **cost-based** | Picks cheapest deployment | Cost-sensitive apps | May pick slow providers |
| **usage-based-v2** | Routes to lowest RPM/TPM (Redis) | Respecting rate limits | NOT recommended for prod |

### 3.2 Giá Models Hiện tại (June 2026)

| Model | Input $/1M | Output $/1M | Cache Read $/1M | Best For |
|-------|-----------|------------|-----------------|----------|
| **DeepSeek V4-Flash** | **$0.14** | **$0.28** | **$0.003** | Drafting, classification |
| DeepSeek V4-Pro | $0.435 | $0.87 | $0.004 | Higher quality drafting |
| GPT-4o-mini | $0.15 | $0.60 | $0.075 | Budget general purpose |
| **GPT-5.4** | **$2.50** | **$10.00** | **$1.25** | Quality gate, complex reasoning |
| Claude Haiku 3.5 | $0.25 | $1.25 | — | High-volume structured tasks |
| **Claude Sonnet 4.6** | **$3.00** | **$15.00** | **$0.30** | Balanced cost-performance |
| Claude Opus 4.6 | $5.00 | $25.00 | $0.50 | Best reasoning, long-context |
| GPT-4.1-mini | $0.40 | $1.60 | — | Fallback, 1M context |

> **Key Insight**: DeepSeek V4-Flash **18x rẻ hơn input** và **36x rẻ hơn output** so với GPT-5.4.

### 3.3 Capability-Based Routing cho oh-my-class

```
Request → Router → Intent Classification
                    ├── Content Drafting → DeepSeek V4-Flash ($0.14/$0.28)
                    ├── Research/Gathering → DeepSeek V4-Flash ($0.14/$0.28)
                    ├── Quality Gate → GPT-5.4 ($2.50/$10.00)
                    ├── Complex Reasoning → Claude Sonnet 4.6 ($3/$15)
                    ├── Code Generation → Claude Sonnet 4.6 ($3/$15)
                    └── Fallback → GPT-4.1-mini ($0.40/$1.60)
```

### 3.4 Fallback Chains

```yaml
litellm_settings:
  # General fallback — any error after retries exhausted
  fallbacks:
    - deepseek-v4-flash: ["deepseek-v4-pro", "gpt-4.1-mini"]
    - gpt-5.4: ["claude-sonnet-4-6"]
    - claude-sonnet-4-6: ["gpt-5.4"]

  # Context window exceeded — route to larger context model
  context_window_fallbacks:
    - deepseek-v4-flash: ["gpt-4.1-mini"]     # 128K → 1M context
    - gpt-5.4: ["claude-sonnet-4-6"]           # 400K → 1M context

  # Content policy violation — route to different provider
  content_policy_fallbacks:
    - claude-sonnet-4-6: ["gpt-5.4"]
    - gpt-5.4: ["claude-sonnet-4-6"]

  # Retry configuration
  num_retries: 3
  request_timeout: 600    # seconds
```

**Fallback Flow:**

```
Request → order=1 deployment
  ↓ fail → retry (num_retries) with cooldown tracking
  ↓ all order=1 exhausted → try order=2 deployments
  ↓ all order levels exhausted → try configured fallbacks
  ↓ all fallbacks fail → return error to client
```

**Cooldown System**: `allowed_fails: 3` per minute → deployment parked for `cooldown_time: 30` seconds.

---

## 4. Caching & Cost Management

### 4.1 Three-Layer Caching Hierarchy

| Layer | Type | Mechanism | Hit Rate | Latency | Cost Impact |
|-------|------|-----------|----------|---------|-------------|
| **L1** | Exact-match | SHA-256 hash of normalized prompt | 5-15% | <1ms | 100% savings on hit |
| **L2** | Semantic cache | Cosine similarity (>=0.95) via vector DB | 30-50% | ~5-50ms | 100% savings on hit |
| **L3** | Provider prompt caching | KV cache (Anthropic/OpenAI built-in) | 60-90% | 0ms | 90% off cached input |

### 4.2 Real-World Cache Results

- **67-73% total cache hit rate** trong multi-agent NL→Code systems
- **73% cost reduction** combining semantic + rate limiting
- **80-99% prefix cache hit rate** trong multi-agent forks
- **~62% monthly inference cost reduction** trong 3-tier Redis cache setups

### 4.3 Token Budget Management

```yaml
task_budgets:
  classify:
    max_tokens: 100
    model: deepseek-v4-flash
  draft_content:
    max_tokens: 4000
    model: deepseek-v4-flash
  quality_gate:
    max_tokens: 2000
    model: gpt-5.4
  complex_reasoning:
    max_tokens: 4000
    model: claude-sonnet-4-6
```

```python
# Adaptive budgets using exponential moving average
task_history: dict[str, float] = {}

def allocate(task_type: str) -> int:
    """Allocate token budget based on historical usage."""
    if task_type not in task_history:
        return 2000  # Default
    return int(task_history[task_type] * 1.5)

def record(task_type: str, tokens_used: int):
    """Record actual usage for future allocation."""
    if task_type not in task_history:
        task_history[task_type] = tokens_used
    else:
        task_history[task_type] = 0.9 * task_history[task_type] + 0.1 * tokens_used
```

### 4.4 Per-Key/Per-Team Budgets

```bash
# Virtual key for a content agent — $100/month budget
curl -X POST 'http://litellm-proxy:4000/key/generate' \
  -H 'Authorization: Bearer sk-master' \
  -d '{
    "key_alias": "content-agent-drafting",
    "max_budget": 100,
    "budget_duration": "1mo",
    "models": ["deepseek-v4-flash", "deepseek-v4-pro"],
    "tpm_limit": 100000,
    "rpm_limit": 100
  }'

# Virtual key for quality gate — $200/month budget
curl -X POST 'http://litellm-proxy:4000/key/generate' \
  -H 'Authorization: Bearer sk-master' \
  -d '{
    "key_alias": "quality-gate",
    "max_budget": 200,
    "budget_duration": "1mo",
    "models": ["gpt-5.4", "claude-sonnet-4-6"],
    "tpm_limit": 200000,
    "rpm_limit": 50
  }'
```

### 4.5 Per-Agent Cost Attribution

```python
response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[...],
    extra_body={
        "metadata": {
            "tags": [
                "task:draft-content",
                "agent:deepseek-writer",
                "pipeline:oh-my-class",
                "run_id:run-12345"
            ]
        }
    }
)
```

Biến "AI costs $50K/month" thành "content pipeline spent $12K on DeepSeek, quality gate spent $38K on GPT-5.4."

### 4.6 Batching Strategy

| Provider | Discount | SLA | Best For |
|----------|----------|-----|----------|
| OpenAI Batch API | **50% off** | 24h | Document enrichment, dataset gen |
| Anthropic Batch API | **50% off** | 24h | Report generation |
| DeepSeek | Check docs | — | High-volume drafting |

**Ví dụ thực tế**: Pipeline 100K records/day → từ $500/day xuống $250/day với batch.

---

## 5. Cấu hình Production cho oh-my-class

### 5.1 Complete LiteLLM config.yaml

```yaml
# ================================================================
# oh-my-class LiteLLM Proxy Configuration
# ================================================================

model_list:
  # --- DeepSeek (Drafting: cheap, high volume) ---
  - model_name: deepseek-v4-flash
    litellm_params:
      model: openai/deepseek-chat
      api_key: os.environ/DEEPSEEK_API_KEY
      api_base: https://api.deepseek.com
    model_info:
      mode: chat
      supported_environments: ["development", "staging", "production"]

  - model_name: deepseek-v4-pro
    litellm_params:
      model: openai/deepseek-reasoner
      api_key: os.environ/DEEPSEEK_API_KEY
      api_base: https://api.deepseek.com
    model_info:
      mode: chat
      supported_environments: ["production"]

  # --- OpenAI (Quality Gate: expensive, low volume) ---
  - model_name: gpt-5.4
    litellm_params:
      model: openai/gpt-5.4
      api_key: os.environ/OPENAI_API_KEY
    model_info:
      mode: chat
      supported_environments: ["production"]

  - model_name: gpt-4.1-mini
    litellm_params:
      model: openai/gpt-4.1-mini
      api_key: os.environ/OPENAI_API_KEY
    model_info:
      mode: chat
      supported_environments: ["staging", "production"]

  # --- Anthropic (Code, Long Context) ---
  - model_name: claude-sonnet-4-6
    litellm_params:
      model: anthropic/claude-sonnet-4-6
      api_key: os.environ/ANTHROPIC_API_KEY
    model_info:
      mode: chat
      supported_environments: ["production"]

  - model_name: claude-haiku-3.5
    litellm_params:
      model: anthropic/claude-3-5-haiku-20241022
      api_key: os.environ/ANTHROPIC_API_KEY
    model_info:
      mode: chat
      supported_environments: ["staging", "production"]

# === ROUTER SETTINGS ===
router_settings:
  routing_strategy: simple-shuffle
  enable_pre_call_checks: true

  redis_host: os.environ/REDIS_HOST
  redis_port: os.environ/REDIS_PORT
  redis_password: os.environ/REDIS_PASSWORD

  allowed_fails: 3
  cooldown_time: 30
  max_fallbacks: 5

  routing_groups:
    - group_name: realtime
      models: [gpt-5.4, claude-sonnet-4-6]
      routing_strategy: latency-based-routing
      routing_strategy_args:
        ttl: 60
    - group_name: batch
      models: [deepseek-v4-flash, deepseek-v4-pro]
      routing_strategy: cost-based-routing

  retry_policy:
    AuthenticationErrorRetries: 0
    TimeoutErrorRetries: 3
    RateLimitErrorRetries: 3
    InternalServerErrorRetries: 4

# === LITELLM SETTINGS ===
litellm_settings:
  num_retries: 3
  request_timeout: 120
  drop_params: true
  set_verbose: false
  json_logs: true

  cache: true
  cache_params:
    type: redis
    host: os.environ/REDIS_HOST
    port: os.environ/REDIS_PORT
    password: os.environ/REDIS_PASSWORD

  fallbacks:
    - deepseek-v4-flash: ["deepseek-v4-pro", "gpt-4.1-mini"]
    - gpt-5.4: ["claude-sonnet-4-6"]
    - claude-sonnet-4-6: ["gpt-5.4"]
  context_window_fallbacks:
    - deepseek-v4-flash: ["gpt-4.1-mini"]
    - gpt-5.4: ["claude-sonnet-4-6"]
  content_policy_fallbacks:
    - claude-sonnet-4-6: ["gpt-5.4"]

# === GENERAL SETTINGS ===
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: os.environ/DATABASE_URL
  alerting: ["slack"]
  proxy_batch_write_at: 60
  disable_error_logs: false
  allow_requests_on_db_unavailable: true
```

### 5.2 .env Template

```bash
# ========= LITELLM PROXY =========
LITELLM_MASTER_KEY=sk-oh-my-class-master-...
LITELLM_SALT_KEY=sk-oh-my-class-salt-...
LITELLM_MODE=PRODUCTION
LITELLM_ENVIRONMENT=production

# ========= DATABASE =========
DATABASE_URL=postgresql://litellm:password@db:5432/litellm

# ========= REDIS (Caching + Shared State) =========
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=

# ========= PROVIDER API KEYS =========
# DeepSeek (drafting agent - HIGH volume, LOW cost)
DEEPSEEK_API_KEY=sk-...

# OpenAI (quality gate - LOW volume, HIGH cost)
OPENAI_API_KEY=sk-...

# Anthropic (code generation, long context)
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini (fallback option)
GEMINI_API_KEY=AIza...

# ========= KEY ROTATION =========
LITELLM_KEY_ROTATION_ENABLED=true
LITELLM_KEY_ROTATION_CHECK_INTERVAL_SECONDS=86400
LITELLM_KEY_ROTATION_GRACE_PERIOD=48h

# ========= MONITORING =========
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

### 5.3 Environment Switching

```yaml
model_info:
  supported_environments: ["development", "staging", "production"]
```

| Environment | Models Available | Purpose |
|-------------|-----------------|---------|
| **development** | All models (including cheap) | Testing, debugging |
| **staging** | Subset (no ultra-expensive) | Pre-production validation |
| **production** | Only tested models | Live system |

---

## 6. Model-to-Agent Mapping

### 6.1 Bảng Phân bổ Chi tiết

| Agent | Model | Input $/1M | Output $/1M | Est. Tokens/Request | Est. Cost/Request |
|-------|-------|-----------|------------|--------------------|------------------|
| Content Drafting | DeepSeek V4-Flash | $0.14 | $0.28 | 8K in / 2K out | **$0.0017** |
| Research Gathering | DeepSeek V4-Flash | $0.14 | $0.28 | 5K in / 1K out | **$0.0010** |
| Quality Gate (GPT) | GPT-5.4 | $2.50 | $10.00 | 4K in / 500 out | **$0.015** |
| Quality Gate (Claude) | Claude Sonnet 4.6 | $3.00 | $15.00 | 4K in / 500 out | **$0.0195** |
| Code Generation | Claude Sonnet 4.6 | $3.00 | $15.00 | 6K in / 1K out | **$0.033** |
| Fallback Cheap | GPT-4.1-mini | $0.40 | $1.60 | 4K in / 500 out | **$0.0024** |

### 6.2 Ước tính Chi phí Hàng tháng

**Kịch bản**: 10K drafts + 10K quality gates + 2K code gen per month

| Component | Model | Calls | Est. Cost |
|-----------|-------|-------|-----------|
| Content Drafting | DeepSeek V4-Flash | 10,000 | **$17** |
| Quality Gate | GPT-5.4 | 10,000 | **$150** |
| Code Generation | Claude Sonnet 4.6 | 2,000 | **$66** |
| **Total Provider Cost** | | | **~$233/month** |
| **LiteLLM Server** | | | **~$25/month** |
| **Grand Total** | | | **~$258/month** |

**So sánh**: Nếu dùng GPT-5.4 cho tất cả: 22K × $0.05 = **$1,100/month**.

> **Tiết kiệm: ~77% ($842/month)** nhờ multi-model routing.

### 6.3 ROI Analysis

```
Monthly savings from multi-model routing: $842
Annual savings: $10,104
LiteLLM setup cost: ~$0 (self-hosted Docker)
Payback period: Immediate
```

---

## 7. Docker Compose Deployment

### 7.1 docker-compose.yml

```yaml
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
    image: ghcr.io/berriai/litellm-database:v1.85.0
    restart: always
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }
    ports:
      - "4000:4000"
    volumes:
      - ./config.yaml:/app/config.yaml:ro
    command: ["--config", "/app/config.yaml", "--port", "4000", "--num_workers", "4"]
    environment:
      LITELLM_MASTER_KEY: ${LITELLM_MASTER_KEY}
      LITELLM_SALT_KEY: ${LITELLM_SALT_KEY}
      DATABASE_URL: postgresql://litellm:${POSTGRES_PASSWORD}@db:5432/litellm
      REDIS_HOST: redis
      REDIS_PORT: 6379
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      SLACK_WEBHOOK_URL: ${SLACK_WEBHOOK_URL}
    healthcheck:
      test: ["CMD-SHELL", "python -c 'import urllib.request; urllib.request.urlopen(\"http://localhost:4000/health/readiness\")' 2>/dev/null || exit 1"]
      interval: 15s
      timeout: 10s
      retries: 5
      start_period: 30s

volumes:
  pgdata:
  redis_data:
```

### 7.2 Startup Commands

```bash
# Start infrastructure
docker compose up -d

# Verify health
docker compose ps
curl http://localhost:4000/health/readiness

# Create virtual keys
curl -X POST 'http://localhost:4000/key/generate' \
  -H 'Authorization: Bearer sk-master' \
  -d '{"key_alias": "content-agent", "max_budget": 100, "budget_duration": "1mo"}'

# Test routing
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-content-agent-key" \
  -H "Content-Type: application/json" \
  -d '{"model": "deepseek-v4-flash", "messages": [{"role": "user", "content": "Hello"}]}'
```

---

## 8. Client Code & Integration

### 8.1 oh-my-class Agent Client

```python
import openai

# Point ALL agents to the same LiteLLM proxy
client = openai.OpenAI(
    api_key="sk-oh-my-class-agent-key",  # Virtual key with budget limits
    base_url="http://localhost:4000"      # LiteLLM proxy
)

# DeepSeek does the drafting (cheap, high volume)
draft = client.chat.completions.create(
    model="deepseek-v4-flash",           # $0.0017/call
    messages=[{"role": "user", "content": "Viết bài giảng về Phân số lớp 5..."}],
    extra_body={"metadata": {"tags": ["agent:drafting", "pipeline:oh-my-class"]}},
    response_format={"type": "json_object"},
)

# GPT-5.4 does the quality gate (expensive, low volume)
review = client.chat.completions.create(
    model="gpt-5.4",                     # $0.015/call
    messages=[{"role": "user", "content": f"Review this content:\n{draft.choices[0].message.content}"}],
    extra_body={"metadata": {"tags": ["agent:quality-gate", "pipeline:oh-my-class"]}},
    response_format={"type": "json_object"},
)

# Claude does complex reasoning when needed
reasoning = client.chat.completions.create(
    model="claude-sonnet-4-6",           # $0.033/call
    messages=[{"role": "user", "content": "Phân tích logic bài toán..."}],
    extra_body={"metadata": {"tags": ["agent:reasoning", "pipeline:oh-my-class"]}},
)
```

### 8.2 LangGraph Integration

```python
from langchain_openai import ChatOpenAI

# LangGraph nodes use LiteLLM proxy automatically
def create_llm(model_name: str):
    return ChatOpenAI(
        model=model_name,
        api_key="sk-oh-my-class-agent-key",
        base_url="http://localhost:4000",
        temperature=0.1,
    )

# Content Creator uses DeepSeek (cheap)
content_llm = create_llm("deepseek-v4-flash")

# Quality Gate uses GPT-5.4 (expensive)
gate_llm = create_llm("gpt-5.4")

# Use in LangGraph nodes
def content_generation_node(state):
    result = content_llm.invoke(f"Generate content: {state['synthesized_facts']}")
    return {"content_draft": result.content}

def quality_review_node(state):
    result = gate_llm.invoke(f"Review content: {state['content_draft']}")
    return {"quality_scores": parse_scores(result.content)}
```

---

> **Nguồn tham khảo**:
> - LiteLLM: https://github.com/BerriAI/litellm
> - LiteLLM Docs: https://docs.litellm.ai/
> - OneAPI: https://github.com/songquanpeng/one-api
> - Portkey: https://github.com/Portkey-AI/gateway
> - DeepSeek Pricing: https://api-docs.deepseek.com/quick_start/pricing
> - LLM Gateway Comparison: https://klymentiev.com/blog/llm-gateway-guide
