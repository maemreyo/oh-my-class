---
title: Add cache, privacy, and observability-retention boundaries
status: ready-for-agent
labels: [component-strategist, privacy, observability, testing]
created: 2026-07-05
---

## Parent

ADR-036 and ADR-038.

## What to build

Define and implement the Component Strategist's privacy-minimized request fingerprints, safe caching rules, default observability events, debug ledger redaction/TTL, and selector data boundary. The strategist must be explainable without leaking classroom content or storing raw free text in cache keys, snapshots, or normal logs.

## Acceptance criteria

- [ ] Component strategy cache keys and request fingerprints use normalized structured inputs only: objective refs, subject/domain, grade band, duration bucket, artifact/export requirements, locale, class context tags, typed research signal digest, teacher preference version, outcome signal version, and knowledge/scoring/selector/renderer/exporter versions.
- [ ] Raw teacher text, free-form feedback notes, full research prose, student names, emails, individual scores, and PII-bearing fields are excluded from cache keys, snapshots, and default observability events.
- [ ] Cross-run final-plan caching is disabled in v1 unless a future feature includes full versioned fingerprints and explicit invalidation rules.
- [ ] Allowed caching is limited to read-only knowledge/capability index loads, normalized candidate/index lookups, deterministic score primitives, localized deterministic rationale templates, and optional LLM-polished rationale keyed by structured facts + locale + model/template version.
- [ ] Selector input contract accepts class-level/cohort-level signals only and rejects individual-student fields.
- [ ] Teacher free-text feedback/misconception notes are stored separately with privacy handling; snapshots store only refs/metadata or typed sanitized signals.
- [ ] Default observability events are minimized and structured: status, versions, quality summary, fallback reason, blocking issue codes, latency, and cache hit/miss.
- [ ] Full `StrategyDecisionLedger` is written only in explicit debug mode, redacts PII before write, carries `contains_strategy_debug_data`, and expires under a diagnostic TTL separate from normal run retention.
- [ ] Debug ledgers are admin/debug-only and never included in teacher approval payloads.
- [ ] Tests prove PII-like fields are rejected/excluded from fingerprints/events, debug ledger TTL metadata is set, and normal events contain no raw lesson/free-text content.

## Blocked by

- CS-01 contracts and immutable strategy snapshot.
- CS-03 selector, scorer, and diversity core.
- CS-06 strategy quality gates and observability.

## References

- `docs/adr/036-component-strategy-knowledge-and-governance.md`
- `docs/adr/038-component-strategy-validators-and-release-gates.md`
- `packages/agents/events.py`
- `packages/agents/teaching_pack/store_namespaces.py`
- `packages/agents/teaching_pack/teacher_memory.py`
- `services/gateway/teaching_pack_store.py`

## Implementation notes

- Privacy is primarily enforced by the small explicit request interface; do not turn the selector into a general PII scanner.
- If raw notes are needed for support, store them outside the immutable strategy snapshot with retention/access controls.
- Full ledgers are diagnostic artifacts, not long-lived replay state.
