# 9Router Setup

oh-my-class uses 9Router as the local LLM gateway. `f.light` and `f.pro`
are combos configured in 9Router — the app never sees provider names.

## Prerequisites

9Router running on port 20128:

```bash
npm i -g 9router@latest && 9router
# → dashboard at http://localhost:20128/dashboard
```

## Import config

1. Open http://localhost:20128/dashboard
2. Settings → Import Config → select `infra/9router/config-export.json`
3. Add your provider credentials via the Providers tab:
   - **Kiro AI** (free tier): login with AWS Builder ID at https://kiro.ai → copy API key
4. Verify `f.light` and `f.pro` combos appear under the Combos tab

## Docker image (for future production use)

```
decolua/9router:latest
```

Run command: `npm i -g 9router@latest && 9router` (no `start` subcommand needed)

## .env.local

Copy `.env.local` to `.env` before starting:

```bash
cp .env.local .env
```

The key variables:

```bash
LLM_CLIENT_BASE_URL=http://localhost:20128   # 9Router direct
LLM_CLIENT_API_KEY=dummy                     # no auth enforcement locally
```

## Onboarding flow (new contributor)

```bash
# Step 1: install + start 9Router
npm i -g 9router@latest && 9router

# Step 2: import config
# → http://localhost:20128/dashboard → Settings → Import → infra/9router/config-export.json
# → Add Kiro AI API key via Providers tab (free tier: AWS Builder ID login)
# → Verify f.light and f.pro combos appear

# Step 3: copy env
cp .env.local .env

# Step 4: start dev
make dev          # Python gateway on :8001
make dev-all      # Python gateway + Next.js frontend concurrently
```

## Architecture

```
Agent
  └─► 9Router :20128  (RTK compression, free tier, combo routing)
        └─► Kiro AI   (Claude Sonnet 4.5 free tier via AWS Builder ID)
```

For production deployment (LiteLLM + Postgres + Redis), see `.scratch/litellm-proxy/ISSUE.md`.

## Combo reference

| Combo | Strategy | Use case |
|-------|----------|---------|
| `f.light` | round-robin | Summarization, title generation, schema rewrite |
| `f.pro` | round-robin + fusion | Content generation, quality gate, fact verification, blueprint |

RTK token compression is applied automatically by 9Router (20–40% reduction) — no app changes needed.
