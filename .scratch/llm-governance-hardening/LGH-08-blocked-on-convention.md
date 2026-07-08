---
title: "BLOCKED-ON marker convention + listing script; apply to ownership.py's organization_id gap"
status: done
labels: [governance, process, auth]
created: 2026-07-08
priority: p2
epic: llm-governance-hardening
sequence: 8
---

> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 8. As of 2026-07-08, `services/gateway/auth/ownership.py`'s `SCHOOL_ADMIN` cross-org path is still fail-closed and unreachable, pending an `organization_id` column on `users` (confirmed still missing — no migration adds it). ADR-047 (Decision #9) already independently notes this same gap for the slide-deck editor's authorization model, and states editor access "inherits that fix automatically" once it lands — this issue is the first place that fix itself gets tracked, not just referenced.

## What to build

1. **Convention**: a `# BLOCKED-ON: <short description> (see <.scratch path or issue id>)` comment marker for code that is correctly implemented but permanently unreachable pending external work (a migration, another team's deliverable, etc.) — distinct from a `TODO` (which implies "not yet written") or dead code (which implies "should be removed"). Document this convention alongside the `KNOWN_DARK` ledger's documentation, since it addresses an adjacent but distinct failure mode (code that's real and correct but silently inert, vs. code that's real but never called at all).
2. **`scripts/list_blocked_on_markers.py`**: grep the repo for `# BLOCKED-ON:` and print each with its file/line and referenced tracking issue, as a standing report (same non-blocking cadence as `LGH-04`/`LGH-07`).
3. Apply the marker now: add `# BLOCKED-ON: users.organization_id migration (see .scratch/multi-tenancy/organization-id-migration.md)` above `_check_same_organization` in `services/gateway/auth/ownership.py:42`.
4. Create `.scratch/multi-tenancy/organization-id-migration.md` tracking the actual migration (add `organization_id` to `users`, backfill strategy, and unblocking `SCHOOL_ADMIN`/ADR-047's editor authorization) as its own issue — **do not implement the migration itself in this issue**; multi-tenancy data modeling needs its own scoping, not a rushed decision inside an LLM-focused grill session.

## Acceptance criteria

- [x] `# BLOCKED-ON:` convention documented.
- [x] Listing script implemented and run once to confirm it finds the marker added in step 3.
- [x] `ownership.py` carries the marker with a working reference to the tracking issue.
- [x] `.scratch/multi-tenancy/organization-id-migration.md` exists with `status: ready` (not `ready-for-agent` — needs product/data-model scoping first) and cross-references ADR-047 Decision #9 and this issue.

> Done (2026-07-08): convention documented in `tests/test_no_dark_runtime_modules.py`'s
> module docstring, next to `KNOWN_DARK` (no separate shared conventions doc existed
> to reuse — `.scratch/README.md` only covers the issue `status` field). Added
> `scripts/list_blocked_on_markers.py` (informational, always exits 0) and confirmed
> it finds the one marker now in the tree: `services/gateway/auth/ownership.py:42`
> above `_check_same_organization`. `.scratch/multi-tenancy/organization-id-migration.md`
> already existed from a prior pass and matches (status: ready, cross-references
> ADR-047 Decision #9 and this issue).

## Blocked by

Nothing for the marker/script. The migration itself (tracked separately) is blocked on multi-tenancy data-model scoping, out of this session's scope.
