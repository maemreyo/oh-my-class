---
title: "Add organization_id to users table — unblocks SCHOOL_ADMIN cross-org access"
status: ready
labels: [multi-tenancy, auth, migration]
created: 2026-07-08
priority: p2
---

## Context

`services/gateway/auth/ownership.py`'s `_check_same_organization` (marked `# BLOCKED-ON`, see `LGH-08`) has been coded and fail-closed since before this session, waiting on an `organization_id` column on the `users` table. Until it lands, `SCHOOL_ADMIN` users can never access a run belonging to a teacher in their own organization — the role exists but this specific cross-org path is permanently a no-op.

ADR-047 (Slide Deck Editor, Decision #9) explicitly designed the editor's authorization to reuse `check_run_owner` unchanged, on the assumption that this fix "unblocks `SCHOOL_ADMIN` same-org access" and that editor access "inherits that fix automatically" once it ships — i.e. this migration is already a soft dependency of at least one shipped ADR, not a purely hypothetical gap.

## What to build

Not scoped in detail here deliberately — this needs actual multi-tenancy data-model decisions before implementation, not a rushed answer inside an LLM-integration grill session:

- Confirm the organization/school data model: does a `User` belong to exactly one organization, or can they belong to multiple (e.g. a teacher who works at two schools)? `ownership.py`'s current code (`owner_org == user.organization_id`, singular) assumes exactly one.
- Migration: add `organization_id` (FK to an `organizations`/`schools` table, or a plain string/UUID if no such table exists yet — confirm) to `users`, with a backfill strategy for existing rows (what organization do pre-existing users belong to?).
- Update `services/gateway/models.py`'s `User` ORM model to have a real `organization_id` field (currently `ownership.py:67` uses `getattr(owner, "organization_id", None)` defensively, implying the ORM model doesn't declare the column at all).

## Acceptance criteria

- [ ] Data model for organization membership confirmed with product (single-org vs multi-org per user).
- [ ] Migration adds the column with an explicit backfill plan (no silently-null rows left in an ambiguous state for existing users).
- [ ] `services/gateway/models.py`'s `User` model declares `organization_id` directly (the `getattr(..., None)` defensive pattern in `ownership.py:67` can be simplified once the column always exists).
- [ ] `_check_same_organization` is exercised by a real test proving `SCHOOL_ADMIN` cross-org access actually works end-to-end post-migration (currently only the fail-closed path is testable).
- [ ] The `# BLOCKED-ON` marker in `ownership.py` is removed once this lands.
- [ ] ADR-047's slide-deck editor authorization is confirmed to inherit the fix automatically, as that ADR assumed.

## Blocked by

Needs product/data-model scoping (organization membership shape) before implementation can start.
