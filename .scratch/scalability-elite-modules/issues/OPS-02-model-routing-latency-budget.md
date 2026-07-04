# [OPS-02] Model routing + per-stage latency budget to hold p95 pack < 8 min

Status: TODO
Labels: ops, performance, llm
ADR: 034
Depends on: none

## Context

Routing today is **config-per-agent** and works well: `packages/agents/config/models.py` maps each task/agent to a 9Router combo via `ModelAssignments` (env prefix `MODEL_`), with a strong/medium/fast tier system (`_STRONG_TIER` :38, `_FAST_TIER` :45), tier-alias fallback (`MODEL_STRONG_DEFAULT`/`MODEL_FAST_DEFAULT`, `apply_tier_defaults` :94), and per-agent output caps (`MaxTokensConfig`, `content_creator` = 16384 :136). ADR-034 §1 says **keep this routing** — do not replace it.

The gap is **latency governance**. There is a per-run *budget* (`services/gateway/budget.py`: `max_tokens_per_run=500k`, searches, fetches, retries) but **no latency budget**. The north-star bar is **p95 pack < 8 min**, and the dominant stage is `content_creator` streaming (it has the largest `max_tokens` at 16384 and is the generation workhorse — medium tier, per-agent in `ModelAssignments` :77). Without per-stage latency budgets and drift detection, a slow provider or a routing change to a slower model silently erodes p95 until the SLO breaks, and we only find out from OPS-03/04 alerts after the fact.

`model_drift.py` already exists (`packages/agents/config/model_drift.py`): `snapshot_models` :20 captures the full assignment map, and `evaluate_model_drift` compares snapshots and alerts on `golden_score_delta < -0.02`. It monitors **quality** drift on model changes but not **latency** drift. OPS-02 adds the latency dimension and wires stage budgets so p95 is a governed, observable property — not an emergent one.

## Scope

- [ ] **Keep config-per-agent routing** — no change to the `ModelAssignments` shape, tier system, or `MODEL_*` env contract. OPS-02 is purely additive.
- [ ] **Per-stage latency budget object** — introduce a `StageLatencyBudget` config (mirroring `budget.py` style: frozen dataclass, env-mappable) assigning a p95 wall-clock target per pipeline stage that sums (with headroom) to < 8 min. Give `content_creator` the largest slice since it is the dominant stage; give quality-gate/judge stages tight caps. Values must be env-tunable (dev may be looser).
- [ ] **Measure stage latency on the live path** — record per-stage wall-clock from the existing observability events (`stage_transition` in `packages/agents/events.py:24`, and `step_started`/`step_completed` :34-36). Derive `stage_latency_p95_seconds` — note `slo_metrics.SloDimension.stage_latency_p95_seconds` already exists as a field but is populated with `{}` (`slo_metrics.py:104`). OPS-02 makes that field real by computing per-stage p95 from `run_events`. (Feeds OPS-03/04.)
- [ ] **Budget breach → observable signal, not hard-kill** — when a stage exceeds its latency budget, emit an observability event (reuse an existing type or add a `stage_latency_exceeded` type to `ObservabilityEventType`) so OPS-03 dashboards and OPS-04 warn-tier alerts can see it. Do NOT kill a mid-flight generation on a soft budget breach (that would fail the run and hurt the 99.5% SLO); the latency budget is a governance/alerting instrument. A hard wall-clock ceiling (well above p95, e.g. run-level timeout) may fail-close a truly hung run — keep that distinct from the per-stage p95 budget.
- [ ] **Latency drift in `model_drift`** — extend the drift check so that when the model assignment map changes (`snapshot_models` diff), it also flags **latency regression** (per-stage p95 worsening beyond a threshold after the change), not only `golden_score_delta`. A routing change that keeps quality but doubles content_creator latency must alert.
- [ ] **Env mapping** — dev: budgets present but non-blocking / loose, no alerting required. staging/prod: budgets enforced as alerting thresholds, latency drift monitored, p95 tracked against the 8-min bar continuously.

## Acceptance

- `SloDimension.stage_latency_p95_seconds` returns real per-stage p95 values (not `{}`) computed from `run_events`, with `content_creator` visible as a distinct stage.
- A configured per-stage latency budget exists whose sum + headroom < 8 min; exceeding a stage budget emits an observable event that OPS-03 can chart and OPS-04 can warn on — without failing the run.
- Changing a `MODEL_*` assignment to a slower-but-equal-quality model triggers a latency-drift alert from `model_drift`, distinct from the quality-drift (`golden_score_delta`) alert.
- Routing config contract (`ModelAssignments`, tiers, `MAX_TOKENS_*`) is unchanged; existing model-config tests still pass.
- Measured against real runs (real LLM via LiteLLM→9Router, real Postgres `run_events`), not synthetic timings.

## References

- `packages/agents/config/models.py` — `ModelAssignments` :52, tiers :38/:45, `apply_tier_defaults` :94, `MaxTokensConfig` :119 (`content_creator=16384` :136), `NinerouterConfig` :142.
- `packages/agents/config/model_drift.py` — `snapshot_models` :20, `evaluate_model_drift` :43 (`golden_score_delta` gate), `DriftDecision` :15.
- `services/gateway/budget.py` — `BudgetConfig` :26, `check_budget` :47, `record_usage` :76 (the pattern to mirror for latency).
- `services/gateway/slo_metrics.py` — `SloDimension.stage_latency_p95_seconds` :21 (currently `{}` at :104), `_p95` :145.
- `packages/agents/events.py` — `stage_transition` :24, `step_started`/`step_completed`/`step_failed` :34-36, `ObservabilityEventType` :23 (add `stage_latency_exceeded` here if needed).
- ADR-034 §1 (routing stays config-per-agent + per-stage latency budget to hold p95).

## Implementation notes

- The `_p95` helper in `slo_metrics.py:145` is the canonical percentile function — reuse it for stage p95 so run-level and stage-level p95 agree.
- Per-stage timing is derivable from consecutive `stage_transition`/`step_*` timestamps already persisted in `run_events` (RunEvent has `created_at` and `stage` — `teaching_pack_models.py`), so no new instrumentation on the hot path is strictly required; prefer deriving from existing events over adding timers inside nodes.
- Keep the latency budget a **pure config + pure evaluator** (like `budget.py` is a pure ledger) so it is unit-testable without a running pipeline; the wiring into node execution / `run_events` querying is the thin adapter layer.
- Do not conflate the three limiters: token budget (`budget.py`, resource cap), latency budget (this issue, p95 governance/alerting), and a run-level hard timeout (hung-run fail-close). Document which is which.
- content_creator streaming: because it streams (`teaching_pack_stream.py`), latency should be measured to *first token* and to *completion* separately — a stall in first-token is a different failure than slow total generation. Capture both if cheap.
