# Grounding Report: Report 04 — LLM Proxy Infrastructure & Cost Optimization

**Date**: 2026-06-24  
**Prepared for**: Implementation of Report 04 tickets  
**Source Report**: `docs/reports/core/04-llm-proxy-cost.md` (739 lines)

---

## 1. Report 04 Summary

**Title**: Hạ tầng LLM Proxy & Tối ưu Chi phí  
**Core Architecture**: 2-layer proxy — LiteLLM (port 4000) → 9Router sidecar (port 20128) → Providers

### Key Design Decisions from Report 04

| Decision | Description |
|----------|-------------|
| **C3** | LLMClient wrapper — inject `openai.AsyncOpenAI`, single env var `LLM_CLIENT_BASE_URL` switches endpoints |
| **P2** | 2-layer gateway — LiteLLM handles budget/fallback, 9Router handles free-tier aggregation |
| **TB2** | TokenBudgetManager — separate module, EMA adaptive smoothing, soft/hard limits |
| **FB3** | Fallback strategy — LiteLLM handles infra errors only, no application-level retries |
| **DC2** | Docker Compose — base (dev) + prod override pattern |

### Model Routing (from AGENTS.md §6)

| Agent | Primary Model | Fallback | ~Cost/call |
|-------|--------------|----------|-----------|
| Lead Agent | `gpt-5.4` | `claude-sonnet-4-6` | $0.015 |
| Planner | `deepseek-v4-flash` | `deepseek-v4-pro` | $0.0017 |
| Researcher | `deepseek-v4-flash` | `deepseek-v4-pro` | $0.0010 |
| Content Creator | `deepseek-free` → `deepseek-compressed` → `deepseek-direct` | `gpt-4.1-mini` | $0 → $0.0017 |
| Reviewer | `content-fusion` | `gpt-5.4` | $0.015 |

### 9Router Combo Mapping

| LiteLLM Model Name | 9Router Combo | Cost |
|---|---|---|
| `gpt-5.4` | `f.pro` | $0 (free tier) |
| `deepseek-v4-flash` | `f.light` | $0 (free tier) |
| `deepseek-free` | `f.light` | $0 (free tier) |
| `content-fusion` | `f.pro` (fusion) | $0 (free tier) |
| `deepseek-compressed` | `f.light` (RTK) | $0 (free tier) |

---

## 2. Issues Tagged `report: "04"`

**Only 3 issues found** (not 7 as initially assumed):

### Issue 1: LLM Client (`llm-client`) — P0, `ready`

**Path**: `.scratch/llm-client/ISSUE.md`  
**Design Decision**: C3  
**Blocks**: All agent node implementations

**Files to create**:
```
packages/llm_client/
├── __init__.py
├── client.py        — LLMClient with chat() and stream()
├── config.py        — LLMClientConfig(BaseSettings) with LLM_CLIENT_ prefix
├── tags.py          — build_tags(agent, task, run_id) → metadata dict
├── mock.py          — MockLLMClient with set_response(), call_count(), last_call()
└── tests/
    ├── test_client.py
    ├── test_tags.py
    └── test_mock.py
```

**Acceptance Criteria (8)**:
1. Config reads `LLM_CLIENT_BASE_URL` env var
2. Model names are `f.light` / `f.pro` (not raw provider names)
3. `build_tags()` always appended to every LLM call
4. Mock queues deterministic responses
5. Mock tracks call count and last call
6. Agent tests use mock (no real LLM calls)
7. No fallback/retry in client (handled by LiteLLM layer)
8. Single env var switches between dev/staging/prod

**Dependencies**: Blocked by `gate-config` (MODELS naming)  
**Blocks**: All agent node implementations

---

### Issue 2: Token Budget (`token-budget`) — P1, `ready`

**Path**: `.scratch/token-budget/ISSUE.md`  
**Design Decision**: TB2  
**Blocks**: Nothing (non-blocking monitoring)

**Files to create**:
```
packages/llm_client/budget/
├── __init__.py
├── config.py        — TokenBudgetConfig(BaseSettings) with BUDGET_ prefix
├── manager.py       — TokenBudgetManager: get_limit(), record_usage(), check_soft_limit()
├── ema.py           — EMATracker: exponential moving average per task
└── tests/
    ├── test_manager.py
    └── test_ema.py
```

**Acceptance Criteria (11)**:
1. `BUDGET_` prefix separation from `LLM_CLIENT_`
2. Educational content → no hard limit (soft only)
3. Structured output tasks → hard limit
4. EMA returns `None` before warmup
5. EMA override after warmup
6. `record_usage()` updates both soft and hard limits
7. Soft limit logging (warn, never truncate)
8. `summary()` output format
9. LLMClient integration
10. Per-task EMA tracking
11. Configurable `alpha`, `headroom`, `min_samples`

**Dependencies**: Blocked by `llm-client`  
**Blocks**: Nothing

---

### Issue 3: LiteLLM Proxy (`litellm-proxy`) — P2, `deferred`

**Path**: `.scratch/litellm-proxy/ISSUE.md`  
**Design Decisions**: P2 + FB3 + DC2  
**Status**: Deferred — not needed for local dev; use 9Router directly via `LLM_CLIENT_BASE_URL=http://localhost:20128`

**Files to create**:
```
infra/litellm/
├── config.yaml       — models f.light/f.pro routing to 9Router
├── .env.example
└── scripts/
    ├── create-keys.sh
    └── health-check.sh

docker-compose.yml       — base (dev): just 9Router + app
docker-compose.prod.yml  — override: adds LiteLLM + Postgres + Redis
.env.local
.env.production
```

**Acceptance Criteria (10)**:
1. Model naming matches `f.light` / `f.pro`
2. Route through 9Router
3. Fallback rules per AGENTS.md §6.4
4. Compose patterns (base + override)
5. Env templates
6. Key creation scripts
7. Single-switch `LLM_CLIENT_BASE_URL`
8. Health check endpoint
9. CSP headers on proxy
10. Cost tracking per-agent

**Dependencies**: Blocked by `llm-client`  
**Blocks**: Production deployment

---

## 3. Current Codebase State (Relevant to Report 04)

### What Exists

| Component | Status | Location | Lines |
|-----------|--------|----------|-------|
| **LangGraph graph** | ✅ Complete | `packages/agents/graph.py` | 224 |
| **State schema** | ✅ Complete | `packages/agents/state.py` | 113 |
| **Lead Agent** | ✅ Complete | `packages/agents/lead_agent/` | ~315 |
| **Planner Agent** | ✅ Complete | `packages/agents/sub_agents/planner/` | ~200 |
| **Researcher Agent** | ✅ Complete | `packages/agents/sub_agents/researcher/` | ~230 |
| **Content Creator Agent** | ✅ Complete | `packages/agents/sub_agents/content_creator/` | ~275 |
| **Reviewer Agent** | ✅ Complete | `packages/agents/sub_agents/reviewer/` | ~150 |
| **Middleware chain** | ✅ Complete | `packages/agents/middleware/` | ~1,200 |
| **Quality gates** | ✅ Complete | `packages/quality/` | ~1,100 |
| **Gates** | ✅ Complete | `packages/agents/gates/` | ~400 |
| **Healing system** | ✅ Complete | `packages/agents/healing/` | ~200 |
| **Renderer** | ✅ Complete | `packages/renderer/` | ~1,500 |
| **Pydantic contracts** | ✅ Complete | `common/contracts/` | ~500 |
| **Zod schemas** | ✅ Complete | `common/schemas/` | ~1,320 |
| **Gateway** | ✅ Complete | `services/gateway/` | ~2,200 |

### What's Missing (Report 04 Scope)

| Component | Status | Impact |
|-----------|--------|--------|
| **LLM Client wrapper** | ❌ Not implemented | **BLOCKS all agent nodes** — agents currently have no way to call LLMs |
| **Token Budget manager** | ❌ Not implemented | No cost tracking or budget enforcement |
| **LiteLLM proxy config** | ❌ Not implemented | No production deployment capability |
| **LLM client tests** | ❌ Not implemented | No test coverage for LLM integration |

### What's Stub (Pre-existing, Not Report 04)

| Component | Status | Lines |
|-----------|--------|-------|
| Exporters (GIFT, H5P, QTI) | Stub | ~13 each |
| Gateway artifacts router | Stub | 19 |
| Reviewer tests | Stub | 10 |
| Layer 2/6 tests | Stub | ~9 each |

---

## 4. Dependencies & Blockers

### Report 04 Internal Dependencies

```
llm-client (P0)
    ├── blocks → token-budget (P1)
    └── blocks → litellm-proxy (P2, deferred)
```

### Cross-Report Dependencies

| Report 04 Issue | Depends On | Report |
|-----------------|------------|--------|
| `llm-client` | `gate-config` (MODELS naming) | Report 02 |
| `token-budget` | `llm-client` | Report 04 |
| `litellm-proxy` | `llm-client` | Report 04 |

### What Blocks Report 04

| Blocker | Status | Location |
|---------|--------|----------|
| `gate-config` (MODELS naming) | Check if implemented | `.scratch/gate-config/` |

---

## 5. Implementation Plan (Recommended Order)

### Wave 1: LLM Client (P0) — Foundation

1. **Create `packages/llm_client/` package structure**
2. **Implement `config.py`** — `LLMClientConfig(BaseSettings)` with `LLM_CLIENT_` prefix
3. **Implement `tags.py`** — `build_tags(agent, task, run_id)` → metadata dict
4. **Implement `mock.py`** — `MockLLMClient` for testing
5. **Implement `client.py`** — `LLMClient` wrapping `openai.AsyncOpenAI`
6. **Write tests** — `test_client.py`, `test_tags.py`, `test_mock.py`
7. **Verify** — All existing agent tests still pass with mock client

### Wave 2: Token Budget (P1) — Monitoring

1. **Create `packages/llm_client/budget/` subpackage**
2. **Implement `config.py`** — `TokenBudgetConfig(BaseSettings)` with `BUDGET_` prefix
3. **Implement `ema.py`** — `EMATracker` with exponential moving average
4. **Implement `manager.py`** — `TokenBudgetManager` with soft/hard limits
5. **Write tests** — `test_manager.py`, `test_ema.py`
6. **Integrate with `LLMClient`** — hook `record_usage()` into `chat()`

### Wave 3: LiteLLM Proxy (P2, Deferred) — Production

1. **Create `infra/litellm/` directory**
2. **Write `config.yaml`** — model routing to 9Router
3. **Write Docker Compose files** — base + prod override
4. **Write env templates** — `.env.local`, `.env.production`
5. **Write scripts** — `create-keys.sh`, `health-check.sh`

---

## 6. Key Files to Reference

| Purpose | File | Why |
|---------|------|-----|
| Agent definitions | `packages/agents/sub_agents/*/agent.py` | Shows how agents are structured — LLMClient will be injected here |
| State schema | `packages/agents/state.py` | OhMyClassState — where LLM calls originate |
| Graph definition | `packages/agents/graph.py` | LangGraph nodes — where LLMClient is used |
| Existing config pattern | `packages/agents/gates/gate_config.py` | BaseSettings pattern to follow |
| Mock pattern | `packages/agents/tests/sub_agents/test_planner.py` | Shows how agents are tested — mock client will replace current stubs |
| AGENTS.md §6 | `AGENTS.md` | Model routing table — source of truth for `f.light`/`f.pro` naming |

---

## 7. Risks & Considerations

| Risk | Mitigation |
|------|------------|
| `gate-config` may not be implemented yet | Check `.scratch/gate-config/ISSUE.md` status before starting |
| Existing agent tests may break when LLMClient is injected | Use mock client — no real LLM calls in tests |
| Token budget EMA may be over-engineered for MVP | Consider simple counter first, EMA in follow-up |
| LiteLLM proxy config complexity | Defer to P2 — local dev uses 9Router directly |
| Model naming inconsistency (`f.light` vs `deepseek-v4-flash`) | Follow AGENTS.md §6.1.1 — `f.light`/`f.pro` are 9Router combos, not raw model names |

---

## 8. Verification Checklist

Before starting implementation:

- [ ] Confirm `gate-config` issue status (blocking dependency)
- [ ] Verify `openai` package is in `packages/llm_client/pyproject.toml` dependencies
- [ ] Check if `pydantic-settings` is available for `BaseSettings`
- [ ] Verify existing agent tests pass before changes
- [ ] Confirm `LLM_CLIENT_BASE_URL` env var pattern matches AGENTS.md §6.2

After implementation:

- [ ] All new tests pass
- [ ] Existing agent tests still pass with mock client
- [ ] `build_tags()` output matches AGENTS.md §6.5 metadata format
- [ ] Token budget soft/hard limits work as specified
- [ ] No real LLM calls in test suite

---

**Last updated**: 2026-06-24  
**Status**: Ready for implementation
