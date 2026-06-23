# Observability — Langfuse

## Overview

oh-my-class uses [Langfuse](https://langfuse.com/) for pipeline observability.
Langfuse is open-source, self-hostable, and free — no usage-based pricing.

## Architecture

```
LangGraph Pipeline Nodes
    ↓ (tracing.py)
Langfuse SDK
    ↓ (HTTP)
Langfuse Server (:3001)
    ↓ (PostgreSQL)
Langfuse DB (schema: langfuse)
```

## Integration Points

| Component | What's Traced | How |
|-----------|--------------|-----|
| LangGraph nodes | Pipeline step timing, success/failure | `trace_node()` context manager |
| LLM calls | Model, tokens, cost, latency | `trace_llm_call()` context manager |
| LiteLLM proxy | Cost logs, model routing | LiteLLM native Langfuse integration |
| Teacher gates | Approval decisions, revision feedback | Metadata on trace |

## Trace Structure

```
Trace: run:{run_id}
├── Span: step-03-planner
│   └── Generation: f.light (deepseek-v4-flash via 9Router, 150 tokens, $0)
├── Span: step-07-researcher
│   └── Generation: f.light (deepseek-v4-flash via 9Router, 200 tokens, $0)
├── Span: step-08-content-creator
│   └── Generation: f.light (deepseek-free via 9Router, 500 tokens, $0)
└── Span: step-10-reviewer
    └── Generation: f.pro (content-fusion via 9Router, 300 tokens, $0)
```

> All LLM calls route through 9Router combos (f.light, f.pro).
> Cost is $0 because all providers are free tier.

## Metadata Tags

Every trace includes:
- `run_id`: Links to OhMyClassState.run_id
- `agent`: Which agent (planner, researcher, content_creator, reviewer)
- `step`: Pipeline step number (1-13)
- `teacher_id`: Which teacher initiated the run
- `pipeline`: Always "oh-my-class"

## Setup

1. Add Langfuse to docker-compose (already done)
2. Start services: `docker compose -f infra/compose/docker-compose.yml up -d`
3. Open Langfuse UI: http://localhost:3001
4. Create account and get API keys
5. Add keys to `.env`:
   ```
   LANGFUSE_PUBLIC_KEY=pk-...
   LANGFUSE_SECRET_KEY=sk-...
   ```
6. Restart gateway: `docker compose restart gateway`

## Fallback Behavior

If Langfuse is not configured (no API keys) or unreachable:
- Tracing is silently disabled (no-op)
- Pipeline continues without tracing
- No errors thrown — observability never breaks the pipeline
