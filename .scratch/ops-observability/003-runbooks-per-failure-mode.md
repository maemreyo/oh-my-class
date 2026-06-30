---
title: Runbooks per failure mode
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Operational runbooks for the failure modes the architecture already anticipates, linked from alerts (issue 001).

- One runbook per mode: provider-down / free-tier-exhausted (scaling-resilience 003), job-queue stuck / stale leases (scaling-resilience 001 + sweeper), gate-timeout backlog (24h TTL auto-escalate), render-pool crash (scaling-resilience 002), DB restore (issue 002), content recall (trust-lifecycle 004).
- Each: symptom, alert that fires it, diagnosis steps, remediation, escalation, and a verification step.
- Stored in `docs/runbooks/`, linked from alert payloads.

## Acceptance criteria

- [ ] A runbook exists for each listed failure mode with symptom → diagnosis → remediation → escalation → verify.
- [ ] Alerts (issue 001) link to the relevant runbook.
- [ ] Runbooks reference the actual recovery mechanisms (requeue, sweeper, escalation, restore, recall) — not generic advice.

## Detailed test suite

- [ ] Doc-presence/lint test: each enumerated failure mode has a runbook file with the required sections.
- [ ] Link test: alert payloads reference an existing runbook path.
- [ ] Run the docs/link check in CI.

## Blocked by

- .scratch/ops-observability/001-slo-and-alerting.md
