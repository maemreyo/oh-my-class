---
title: Independent feature flags and AI-rewrite call-count rate limit
status: ready-for-agent
labels: [ready-for-agent, slide-deck, editor, ops]
created: 2026-07-07
---

## Parent

ADR-047: Slide Deck Editor and AI-Assisted Revision (decisions 13, 14)

## What to build

Gate rollout behind two independent feature flags — one for manual structured edit (low risk), one for AI-rewrite (higher risk: live LLM cost, content-validation exposure) — following the existing `FEATURE_TOPIC_DECOMPOSITION_V1` / `FEATURE_VOCABULARY_BATCH_V1` convention. Add a simple, self-contained per-teacher call-count rate limit on AI-rewrite, reusing the webhook rate-limiter pattern — not a full dollar cost cap (that remains `ops-observability/004`'s job; this issue does not block on it).

## Acceptance criteria

- [ ] Two flags exist (e.g. `FEATURE_SLIDE_DECK_EDITOR_V1`, `FEATURE_SLIDE_DECK_AI_REWRITE_V1`); disabling AI-rewrite alone leaves manual editing (SDE-03/04) fully functional.
- [ ] AI-rewrite (SDE-08) is rate-limited per teacher (call count per hour/day, configurable), reusing `services/gateway/routers/webhooks.py`'s sliding-window pattern — not a new rate-limiting subsystem.
- [ ] Exceeding the rate limit returns a clear, teacher-safe message (not a raw 429/stack trace) and does not crash the editor.
- [ ] This issue does not depend on and does not block on `ops-observability/004` (per-teacher dollar cost cap).

## Blocked by

- SDE-08-ai-assisted-block-rewrite.md
