---
title: Runbooks per failure mode
status: done
labels: []
created: 2026-06-30
---

## What to build

Operational runbooks for the failure modes the architecture already anticipates, linked from alerts (issue 001).

- One runbook per mode: provider-down / free-tier-exhausted (scaling-resilience 003), job-queue stuck / stale leases (scaling-resilience 001 + sweeper), gate-timeout backlog (24h TTL auto-escalate), render-pool crash (scaling-resilience 002), DB restore (issue 002), content recall (trust-lifecycle 004).
- Each: symptom, alert that fires it, diagnosis steps, remediation, escalation, and a verification step.
- Stored in `docs/runbooks/`, linked from alert payloads.

## Acceptance criteria

- [x] A runbook exists for each listed failure mode with symptom → diagnosis → remediation → escalation → verify.
- [x] Alerts (issue 001) link to the relevant runbook.
- [x] Runbooks reference the actual recovery mechanisms (requeue, sweeper, escalation, restore, recall) — not generic advice.

## Detailed test suite

- [x] Doc-presence/lint test: each enumerated failure mode has a runbook file with the required sections.
- [x] Link test: alert payloads reference an existing runbook path.
- [x] Run the docs/link check in CI.

## Blocked by

- .scratch/ops-observability/001-slo-and-alerting.md

## Verification

```
uv run pytest tests/test_runbook_presence.py -q
```

12 passed (6 existence checks + 6 section-content checks across all failure modes).
