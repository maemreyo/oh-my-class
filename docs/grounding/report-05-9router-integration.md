# Grounding Report: Report 05 — 9Router Integration

**Date**: 2026-06-24  
**Prepared for**: Implementation of Report 05 tickets  
**Source Report**: `docs/reports/core/05-9router-integration.md` (486 lines)

---

## 1. Report 05 Summary

**Title**: Tích hợp 9Router vào oh-my-class (2-Layer Architecture)  
**Core Architecture**: 9Router as sidecar (port 20128) — free-tier aggregation, RTK token compression, combo routing

### What is 9Router?

- JS-based AI coding-agent gateway (18K+ stars, MIT License)
- Specializes in: free-tier aggregation, RTK token compression (20-40%), combo/fusion routing
- Already running locally — user uses `f.light`/`f.pro` combos daily in OpenCode
- App calls 9Router directly at `http://localhost:20128` — no LiteLLM needed for local dev

### 2-Layer Architecture (from Report 04 + 05)

```
Agent
  └─► LiteLLM :4000      (budget control, cost tracking, fallback chains) [P2, production only]
        └─► 9Router :20128  (RTK compression, free tiers, fusion combo) [P1, local dev]
              ├─► Kiro AI   (Claude 4.5 free tier)
              ├─► OpenCode  (free tier)
              └─► Vertex AI ($300 credits)
```

### 9Router Combos (from AGENTS.md §6.3)

| Combo Name | Strategy | Use Case |
|-----------|----------|---------|
| `f.light` | free-tier → Kiro AI | High-volume drafting, zero cost |
| `f.pro` | free-tier → Kiro AI + fusion | Quality gate, max accuracy |

### Model Routing (Single Source of Truth)

```python
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

### Key Design Decisions

| Code | Decision | Rationale |
|------|----------|-----------|
| **MN2-combo** | `f.light`/`f.pro` are 9Router combo names | Not LiteLLM aliases, not code-level translation |
| **FC1** | No separate fusion combo | `f.pro` is sufficient for all high-quality tasks |
| **RD1** | Use existing local 9Router | No containerization for local dev |
| **LP1** | LiteLLM demoted to P2 | Production-only, not needed locally |
| **AM1** | No `AGENT_MODEL_CONFIG` dict | Use `MODELS` from `gate-config` directly |
| **RK1** | RTK Token Compression is transparent | 9Router applies automatically, no app changes |
| **OB1** | Commit stripped config export | For fast contributor onboarding |
| **DN1** | Local dev runs app directly | `uvicorn`/`npm dev`, not Docker |

---

## 2. Issues Tagged `report: "05"`

**Only 1 issue found**:

### Issue: 9Router Integration (`9router-integration`) — P1, `ready`

**Path**: `.scratch/9router-integration/ISSUE.md`  
**Status**: `ready`  
**Priority**: `p1` (highest)  
**Labels**: `infrastructure`, `llm`, `developer-experience`

**Description**: Build the 9Router integration layer. The user already runs 9Router locally. App calls 9Router directly at `http://localhost:20128`. Deliver stripped config export for contributor onboarding.

#### Files to Create / Modify

| File | Action | Description |
|------|--------|-------------|
| `infra/9router/config-export.json` | **Create** | Stripped 9Router config (no secrets) — importable via dashboard |
| `infra/9router/README.md` | **Create** | Setup instructions: install, import config, set `.env.local` |
| `Makefile` (root) | **Create** | Dev/prod commands: `make dev`, `make dev-all`, `make prod-up`, etc. |
| `docker-compose.yml` | **Modify** | Remove 9Router service (RD1: external to Docker) |
| `.env.local` | **Modify** | Set `LLM_CLIENT_API_KEY=dummy`, `LLM_CLIENT_BASE_URL=http://localhost:20128` |
| `litellm-proxy/ISSUE.md` | **Modify** | Demote to `priority: p2`, `status: deferred` |

#### Acceptance Criteria (8)

1. `infra/9router/config-export.json` — committed, secrets stripped, importable via dashboard
2. `infra/9router/README.md` — install, import, and `.env.local` instructions
3. `Makefile` — targets: `dev`, `dev-all`, `prod-up`, `test`, `lint`
4. `docker-compose.yml` — 9Router service removed (RD1)
5. `.env.local` — `LLM_CLIENT_API_KEY=dummy`, `LLM_CLIENT_BASE_URL=http://localhost:20128`
6. `litellm-proxy/ISSUE.md` — demoted to p2 with deferred note
7. New contributor can onboard in **< 5 minutes** following README
8. `AGENT_MODEL_CONFIG` does **NOT** appear anywhere in codebase

#### Dependencies

- **Blocked by**: Nothing — infra/config only
- **Blocks**: All local dev workflows (every agent needs 9Router reachable)
- **Priority**: P1 — first thing to set up before any agent development

#### Onboarding Flow (Target)

```bash
npm i -g 9router@latest && 9router           # Step 1: install + start 9Router
# Step 2: http://localhost:20128/dashboard → Settings → Import → infra/9router/config-export.json
# Step 3: Add provider credentials (Kiro AI free tier: AWS Builder ID login)
cp .env.local .env                            # Step 4
make dev                                      # Step 5: Python API on :8000
make dev-all                                  # Step 6: Python API + frontend
```

---

## 3. Current Codebase State (Relevant to Report 05)

### What Exists

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| **9Router running locally** | ✅ Active | `http://localhost:20128` | User already uses it daily |
| **`f.light`/`f.pro` combos** | ✅ Configured | 9Router dashboard | Working in OpenCode |
| **Docker Compose** | ✅ Exists | `infra/compose/docker-compose.yml` | May have 9Router service to remove |
| **Gateway service** | ✅ Complete | `services/gateway/` | FastAPI on port 8001 |
| **LLM Client** | ❌ Not implemented | `packages/llm_client/` | Report 04 scope — blocks agent LLM calls |
| **`gate-config`** | Check status | `.scratch/gate-config/` | `MODELS` source of truth |

### What's Missing (Report 05 Scope)

| Component | Status | Impact |
|-----------|--------|--------|
| **`infra/9router/config-export.json`** | ❌ Not created | Contributors can't import combos |
| **`infra/9router/README.md`** | ❌ Not created | No setup documentation |
| **`Makefile`** | ❌ Not created | No standardized dev commands |
| **`.env.local`** | ❌ Not created | No local env config |
| **`docker-compose.yml` cleanup** | ❌ Not done | May have redundant 9Router service |

---

## 4. Dependencies & Blockers

### Report 05 Internal Dependencies

None — this is a standalone infrastructure/config issue.

### Cross-Report Dependencies

| Report 05 Task | Depends On | Report |
|-----------------|------------|--------|
| `config-export.json` | 9Router running locally | — (already true) |
| `Makefile` targets | Gateway, frontend setup | Report 01, 03 |
| `.env.local` | `LLM_CLIENT_BASE_URL` pattern | Report 04 (llm-client) |

### What Blocks Report 05

**Nothing** — this is the first thing to set up before any agent development.

### What Report 05 Blocks

| Blocked Item | Impact |
|--------------|--------|
| All local dev workflows | Every agent needs 9Router reachable |
| LLM Client testing | Needs `LLM_CLIENT_BASE_URL=http://localhost:20128` |
| Agent node development | Can't call LLMs without 9Router |

---

## 5. Implementation Plan (Recommended Order)

### Wave 1: Config Export (Core)

1. **Export 9Router config** — from running instance, strip API keys/secrets
2. **Create `infra/9router/config-export.json`** — commit stripped config
3. **Create `infra/9router/README.md`** — setup instructions with onboarding flow

### Wave 2: Dev Workflow (Makefile)

1. **Create root `Makefile`** — targets: `dev`, `dev-all`, `prod-up`, `test`, `lint`
2. **Verify targets work** — `make dev` starts gateway, `make dev-all` starts gateway + frontend

### Wave 3: Environment & Compose

1. **Create `.env.local`** — `LLM_CLIENT_API_KEY=dummy`, `LLM_CLIENT_BASE_URL=http://localhost:20128`
2. **Modify `docker-compose.yml`** — remove 9Router service (RD1)
3. **Demote `litellm-proxy/ISSUE.md`** — p2, deferred

### Wave 4: Verification

1. **Test onboarding flow** — fresh contributor can setup in < 5 minutes
2. **Verify `AGENT_MODEL_CONFIG`** — does NOT appear anywhere in codebase
3. **Verify all Makefile targets** — work correctly

---

## 6. Key Files to Reference

| Purpose | File | Why |
|---------|------|-----|
| Current Docker Compose | `infra/compose/docker-compose.yml` | May have 9Router service to remove |
| Gateway main | `services/gateway/main.py` | Where app starts — Makefile will invoke this |
| Frontend package.json | `apps/web/package.json` | Where frontend starts — Makefile will invoke this |
| AGENTS.md §6 | `AGENTS.md` | Model routing table — source of truth for `f.light`/`f.pro` |
| Report 04 grounding | `docs/grounding/report-04-llm-proxy-cost.md` | Cross-reference for LLM Client dependency |
| Gate config issue | `.scratch/gate-config/ISSUE.md` | `MODELS` source of truth — verify status |

---

## 7. Risks & Considerations

| Risk | Mitigation |
|------|------------|
| 9Router config may contain secrets | Strip all API keys before committing — use placeholder values |
| `gate-config` may not be implemented yet | Check status — `MODELS` is source of truth for model names |
| Makefile targets may conflict with existing scripts | Check `scripts/` directory for existing dev commands |
| `.env.local` may conflict with existing `.env` | Use `.env.local` as override (gitignored) |
| Docker Compose changes may break existing setup | Test `docker compose up` after changes |

---

## 8. Verification Checklist

Before starting implementation:

- [ ] Confirm 9Router is running locally at `http://localhost:20128`
- [ ] Verify `f.light`/`f.pro` combos are configured in dashboard
- [ ] Check `infra/compose/docker-compose.yml` for existing 9Router service
- [ ] Check `scripts/` for existing dev commands
- [ ] Verify `.env` or `.env.example` exists

After implementation:

- [ ] `infra/9router/config-export.json` — secrets stripped, valid JSON
- [ ] `infra/9router/README.md` — clear setup instructions
- [ ] `Makefile` — all targets work (`make dev`, `make dev-all`, `make test`, `make lint`)
- [ ] `docker-compose.yml` — 9Router service removed
- [ ] `.env.local` — correct env vars set
- [ ] `litellm-proxy/ISSUE.md` — demoted to p2/deferred
- [ ] New contributor onboarding: < 5 minutes
- [ ] `AGENT_MODEL_CONFIG` — not found in codebase

---

**Last updated**: 2026-06-24  
**Status**: Ready for implementation
