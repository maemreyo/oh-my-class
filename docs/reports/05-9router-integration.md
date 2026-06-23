# Báo cáo Kỹ thuật 05: Tích hợp 9Router vào oh-my-class (2-Layer Architecture)

> **Mục tiêu**: Thiết kế cách tích hợp 9Router làm sidecar trong kiến trúc 2-layer (LiteLLM → 9Router → Providers) cho oh-my-class.
>
> **Phiên bản**: 1.1 | **Ngày**: 2026-06-23 | **Cập nhật**: Xác nhận kiến trúc 2-layer

---

## Mục lục

1. [Tổng quan 9Router](#1-tổng-quan-9router)
2. [Kiến trúc 2-Layer](#2-kiến-trúc-2-layer)
3. [LiteLLM config.yaml — 9Router làm Provider](#3-litellm-configyaml--9router-làm-provider)
4. [9Router Setup](#4-9router-setup)
5. [Agent Model Selection — 2-Layer](#5-agent-model-selection--2-layer)
6. [OpenAI-Compatible API](#6-openai-compatible-api)
7. [Chi phí & Tiết kiệm](#7-chi-phí--tiết-kiệm)
8. [Docker Compose — Cả 2 Layer](#8-docker-compose--cả-2-layer)

---

## 1. Tổng quan 9Router

### 1.1 Repository

- **Repo**: `decolua/9router` — 18K+ stars, MIT License
- **Stack**: JavaScript (Next.js 16 + React 19)
- **First commit**: January 2026 — ~6 tháng tuổi
- **Releases**: 69 releases (latest v0.5.8, June 21 2026)
- **Contributors**: 140+, Forks: 2,886

### 1.2 9Router là gì?

9Router là **AI coding-agent gateway** — không phải general-purpose LLM gateway. Nó được build riêng cho:

- **Free-tier aggregation** — tổng hợp các free tier từ nhiều providers
- **RTK Token Compression** — nén semantic content để giảm 20-40% token usage
- **Combo routing** — fusion (parallel+judge), round-robin, fallback
- **Format translation** — OpenAI ↔ Claude ↔ Gemini

### 1.3 Core Differentiators

| Feature | 9Router | LiteLLM | Portkey |
|---------|:-------:|:-------:|:-------:|
| **Free Tier Aggregation** | ✅ Core focus | ❌ | ❌ |
| **RTK Token Compression** | ✅ Unique (20-40%) | ❌ | ❌ |
| **Fusion (Parallel+Judge)** | ✅ Unique | ❌ | ❌ |
| **Capability Auto-Switch** | ✅ Unique | ❌ | ❌ |
| **Virtual Key Budgets** | ⚠️ Basic | ✅ Per-key/user/team | ✅ |
| **Guardrails** | ❌ | ✅ (Presidio) | ✅ (50+) |
| **Semantic Caching** | ❌ | ❌ | ✅ (Pro) |
| **Python Native** | ❌ (JS) | ✅ | ✅ |
| **Production Maturity** | ⚠️ <6 months | ✅ Years | ✅ |

---

## 2. Kiến trúc 2-Layer

### 2.1 Tại sao 2 Layer?

| Layer | Responsibility | Nếu thiếu |
|-------|---------------|-----------|
| **LiteLLM** (Primary) | Budget control, per-key limits, cost alerts, fallback chains, retry, Slack notifications | Không track được chi phí per-agent, không có guard |
| **9Router** (Sidecar) | RTK token compression (20-40%), free-tier aggregation, combo/fusion routing | Mất token savings + free tier access |

### 2.2 Sơ đồ Tổng thể

```
┌──────────────────────────────────────────────────────────────┐
│                    oh-my-class Agents                         │
│              (Python — LangGraph pipeline)                    │
│                                                               │
│  LLM Config:                                                 │
│    base_url = http://litellm:4000  (luôn gọi LiteLLM)        │
│    api_key  = sk-omc-agent-key     (virtual key từ LiteLLM)  │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│              LiteLLM Proxy (Primary, port 4000)               │
│                                                               │
│  职责:                                                         │
│  • Virtual keys per agent ($100/month budget each)           │
│  • Cost tracking → Slack alerts trên $50/month               │
│  • Fallback chains → retry → cooldown                        │
│  • Redis caching (exact-match L1)                            │
│  • Per-agent cost attribution via metadata tags              │
│  • Retry policy: 3 retries, exponential backoff              │
│  • Timeout: 120s per request                                 │
│                                                               │
│  Model routing decisions:                                      │
│  "deepseek-direct"    → Direct to DeepSeek API              │
│  "deepseek-free"      → Forward to 9Router (free tier)      │
│  "deepseek-compressed" → Forward to 9Router (RTK)           │
│  "gpt-5.4"            → Direct to OpenAI API                │
│  "gpt-5.4-fusion"     → Forward to 9Router (fusion combo)   │
└───────────────────────────┬──────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐  ┌──────────────────┐  ┌──────────────┐
│   Direct     │  │   9Router        │  │   Direct     │
│   Providers  │  │   (Sidecar)      │  │   Providers  │
│              │  │   port 20128     │  │              │
│  • DeepSeek  │  │                  │  │  • Anthropic │
│    API       │  │ 职责:             │  │    API       │
│  • OpenAI    │  │  • RTK Compress  │  │  • Custom    │
│    API       │  │  • Free Tiers    │  │  • Other     │
│              │  │  • Combo/Fusion  │  │              │
│              │  │  • Format Xlate  │  │              │
└──────────────┘  └────────┬─────────┘  └──────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌──────────┐ ┌──────────┐ ┌──────────┐
       │ Kiro AI  │ │ Vertex   │ │ OpenCode │
       │ (Free)   │ │ ($300)   │ │ (Free)   │
       │ Claude   │ │ Gemini   │ │ Various  │
       │ 4.5      │ │          │ │          │
       └──────────┘ └──────────┘ └──────────┘
```

### 2.3 Flow chi tiết — 1 Request qua 2 Layer

```
1. Agent → LiteLLM: POST /chat/completions (model="deepseek-free")
2. LiteLLM: lookup model config
   → deepseek-free: { api_base: http://9router:20128/v1, model: openai/deepseek-chat }
3. LiteLLM: check virtual key budget ($100/month, used $45)
   → OK, proceed
4. LiteLLM: check Redis cache (exact-match)
   → MISS, forward to 9Router
5. LiteLLM → 9Router: POST http://9router:20128/v1/chat/completions
   → api_key: sk-9router-dashboard-key
   → model: openai/deepseek-chat
6. 9Router: resolve model → check free tier availability
   → Kiro AI available (Claude 4.5, free)
7. 9Router: RTK compress any tool outputs in messages
   → 20-40% token reduction
8. 9Router → Kiro AI: POST https://kiro.ai/api/v1/chat/completions
   → translate OpenAI format → Anthropic format
9. Kiro AI → 9Router: SSE stream response
   → translate Anthropic format → OpenAI format
10. 9Router → LiteLLM: SSE stream response
11. LiteLLM: log cost ($0 for free tier), check Slack alert threshold
12. LiteLLM → Agent: SSE stream response
```

---

## 3. LiteLLM config.yaml — 9Router làm Provider

```yaml
model_list:
  # ─── Direct Providers (paid, reliable) ───
  - model_name: deepseek-direct
    litellm_params:
      model: openai/deepseek-chat
      api_key: os.environ/DEEPSEEK_API_KEY
      api_base: https://api.deepseek.com
    model_info:
      supported_environments: ["production"]

  - model_name: gpt-5.4
    litellm_params:
      model: openai/gpt-5.4
      api_key: os.environ/OPENAI_API_KEY
    model_info:
      supported_environments: ["production"]

  # ─── Via 9Router: Free Tier (zero cost) ───
  - model_name: deepseek-free
    litellm_params:
      model: openai/deepseek-chat          # 9Router resolve → Kiro AI free
      api_key: os.environ/NINE_ROUTER_API_KEY
      api_base: http://9router:20128/v1    # ← 9Router as provider
    model_info:
      supported_environments: ["staging", "production"]

  - model_name: claude-free
    litellm_params:
      model: openai/claude-sonnet-4-5      # 9Router resolve → Kiro AI free
      api_key: os.environ/NINE_ROUTER_API_KEY
      api_base: http://9router:20128/v1
    model_info:
      supported_environments: ["staging", "production"]

  # ─── Via 9Router: RTK Compression (20-40% savings) ───
  - model_name: deepseek-compressed
    litellm_params:
      model: openai/deepseek-chat
      api_key: os.environ/NINE_ROUTER_API_KEY
      api_base: http://9router:20128/v1
    model_info:
      supported_environments: ["production"]

  # ─── Via 9Router: Fusion (parallel + judge) ───
  - model_name: content-fusion
    litellm_params:
      model: openai/omc-quality-fusion     # 9Router combo name
      api_key: os.environ/NINE_ROUTER_API_KEY
      api_base: http://9router:20128/v1
    model_info:
      supported_environments: ["production"]

# === ROUTER SETTINGS ===
router_settings:
  routing_strategy: simple-shuffle

# === FALLBACKS ===
litellm_settings:
  fallbacks:
    # Content drafting: free → compressed → direct
    - deepseek-free: ["deepseek-compressed", "deepseek-direct"]
    # Quality gate: fusion → direct
    - content-fusion: ["gpt-5.4"]
    # General: free → direct
    - claude-free: ["deepseek-direct"]

  num_retries: 3
  request_timeout: 120
```

---

## 4. 9Router Setup

### 4.1 Docker Deployment

```yaml
# docker-compose.yml — thêm service 9router
services:
  9router:
    image: node:22-alpine
    restart: always
    ports:
      - "20128:20128"
    volumes:
      - ./9router-data:/root/.9router
    environment:
      INITIAL_PASSWORD: ${NINE_ROUTER_PASSWORD}
    command: >
      sh -c "npm install -g 9router && 9router start --port 20128"
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:20128/api/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 4.2 Dashboard Setup (Sau khi start)

1. Mở `http://localhost:20128/dashboard`
2. Login với password từ env `INITIAL_PASSWORD`
3. **Providers** → Add providers:
   - Kiro AI (free): Login với AWS Builder ID
   - OpenAI: Nhập API key (nếu có)
   - Anthropic: Nhập API key (nếu có)
4. **Combos** → Tạo combo:
   ```json
   {
     "name": "omc-quality-fusion",
     "models": ["openai/gpt-5.4", "anthropic/claude-sonnet-4-6"],
     "strategy": "fusion",
     "fusionConfig": { "minPanel": 2, "graceMs": 8000, "timeoutMs": 90000 }
   }
   ```
5. **API Keys** → Tạo key cho LiteLLM → copy key
6. Set env: `NINE_ROUTER_API_KEY=sk-copied-key`

### 4.3 .env Updates

```bash
# Thêm vào .env hiện tại
NINE_ROUTER_PASSWORD=your-strong-password-here  # KHÔNG dùng 123456
NINE_ROUTER_API_KEY=sk-from-9router-dashboard
```

---

## 5. Agent Model Selection — 2-Layer

```python
# oh-my-class agent → model mapping (2-layer aware)

AGENT_MODEL_CONFIG = {
    # High-volume drafting: free tier first, fallback to paid
    "content-drafting": {
        "primary": "deepseek-free",           # LiteLLM → 9Router → Kiro (free)
        "fallback_1": "deepseek-compressed",   # LiteLLM → 9Router RTK (cheap)
        "fallback_2": "deepseek-direct",       # LiteLLM → DeepSeek API (paid)
    },

    # Quality gate: fusion for best quality, fallback to direct
    "quality-gate": {
        "primary": "content-fusion",           # LiteLLM → 9Router Fusion → GPT+Claude
        "fallback": "gpt-5.4",                 # LiteLLM → OpenAI direct
    },

    # Research gathering: free tier
    "research": {
        "primary": "deepseek-free",
        "fallback": "deepseek-direct",
    },

    # Non-critical: always free
    "classification": {
        "primary": "deepseek-free",
    },
}

# Usage trong LangGraph
from langchain_openai import ChatOpenAI

def create_llm(agent_type: str):
    config = AGENT_MODEL_CONFIG[agent_type]
    return ChatOpenAI(
        model=config["primary"],
        api_key="sk-omc-agent-key",          # Virtual key từ LiteLLM
        base_url="http://litellm:4000",       # Luôn gọi LiteLLM
        temperature=0.1,
    )

# Agent nodes
content_llm = create_llm("content-drafting")   # → LiteLLM → 9Router → Free
gate_llm = create_llm("quality-gate")          # → LiteLLM → 9Router → Fusion
```

---

## 6. OpenAI-Compatible API

### 6.1 Cả 2 Layer đều OpenAI-Compatible

```
Agent → LiteLLM (/v1/chat/completions) → 9Router (/v1/chat/completions) → Provider
         OpenAI format                     OpenAI format                    Any format
```

- **LiteLLM**: Nhận OpenAI format → route → respond OpenAI format
- **9Router**: Nhận OpenAI format → translate → Provider format → translate back → respond OpenAI format
- **Agent**: Chỉ thấy OpenAI format xuyên suốt

### 6.2 Python Client

```python
import openai

# Agent gọi LiteLLM (luôn luôn)
client = openai.OpenAI(
    api_key="sk-omc-drafting-key",
    base_url="http://litellm:4000",
)

# LiteLLM tự route sang 9Router hoặc Direct tùy model name
response = client.chat.completions.create(
    model="deepseek-free",  # LiteLLM → 9Router → Kiro AI (free)
    messages=[{"role": "user", "content": "Tạo bài giảng..."}],
)
```

---

## 7. Chi phí & Tiết kiệm

### 7.1 RTK Compression Savings

| Loại Tool Output | Reduction | Ví dụ |
|-----------------|-----------|-------|
| git-diff | 40-60% | 10K tokens → 4K tokens |
| grep output | 30-50% | 5K tokens → 2.5K tokens |
| ls/tree | 50-70% | 3K tokens → 1K tokens |
| build logs | 60-80% | 8K tokens → 2K tokens |

**Estimated**: ~15-25% token reduction cho content generation với file operations.

### 7.2 Free Tier Value

| Provider | Model | Limit | Value/tháng |
|----------|-------|-------|-------------|
| Kiro AI | Claude 4.5 + GLM-5 | Unlimited | ~$50-100 |
| OpenCode Free | Various | Varies | ~$10-30 |
| Vertex AI | Gemini | $300 credits | $300 one-time |

### 7.3 Tổng Chi phí

| Component | Không có 9Router | Với 2-Layer | Tiết kiệm |
|-----------|-----------------|-------------|------------|
| Provider costs | $233/month | ~$186/month | ~$47 (RTK) |
| Free tier value | $0 | ~$60-130/month | ~$60-130 |
| Server cost | $25/month | $35/month (+9Router) | -$10 |
| **Net** | **$258/month** | **~$91-201/month** | **~$57-167/month** |

---

## 8. Docker Compose — Cả 2 Layer

```yaml
services:
  # ═══ Layer 0: Infrastructure ═══
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

  # ═══ Layer 2: 9Router (Sidecar) ═══
  9router:
    image: node:22-alpine
    restart: always
    ports:
      - "20128:20128"
    volumes:
      - ./9router-data:/root/.9router
    environment:
      INITIAL_PASSWORD: ${NINE_ROUTER_PASSWORD}
    command: >
      sh -c "npm install -g 9router && 9router start --port 20128"
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:20128/api/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # ═══ Layer 1: LiteLLM (Primary) ═══
  litellm:
    image: ghcr.io/berriai/litellm-database:v1.85.0
    restart: always
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }
      9router: { condition: service_healthy }
    ports:
      - "4000:4000"
    volumes:
      - ./litellm-config.yaml:/app/config.yaml:ro
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
      NINE_ROUTER_API_KEY: ${NINE_ROUTER_API_KEY}
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

---

> **Nguồn tham khảo**:
> - 9Router: https://github.com/decolua/9router
> - LiteLLM: https://github.com/BerriAI/litellm
> - 9Router Architecture: https://github.com/decolua/9router/blob/master/docs/ARCHITECTURE.md
