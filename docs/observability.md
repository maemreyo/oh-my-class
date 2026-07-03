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
├── Span: planning_blueprint
│   └── Generation: 4omc via 9Router, tags include agent:planner and stage:planning_blueprint
├── Span: post_blueprint_research
│   └── Generation: 4omc via 9Router, tags include agent:researcher and stage:post_blueprint_research
├── Span: artifact_workflow
│   └── Generation: 4omc via 9Router, tags include agent:content_creator and stage:artifact_workflow
└── Span: render_quality
    └── Generation: 4omc via 9Router, tags include agent:reviewer and stage:render_quality
```

> Dev LLM calls route to the host 9Router endpoint; production may place LiteLLM in front for budget and logging.

## Metadata Tags

Every LLM call includes metadata tags:
- `agent:{name}`: Which agent made the call
- `step:{number}`: Numeric teaching-pack stage number
- `stage:{label}`: Stage label, such as `artifact_workflow`
- `run:{id}`: Links to the active teaching-pack run state
- `attempt:{n}`: Retry attempt number
- `pipeline:oh-my-class`: Fixed pipeline identifier

Teacher-visible run events are persisted through gateway `RunEvent` rows after package-level observability events are drained. Important event names include `stage_transition`, `gate_decision`, `healing_decision`, `escalate`, `breaker_tripped`, and `hard_block_violation`.

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
