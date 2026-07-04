# [OPS-09] Multi-tenancy org/school layer

Status: TODO
Labels: ops, tenancy
ADR: 034
Depends on: none

## Context

Isolation today is **per-`teacher_id` only**. Ownership is enforced at the row level via
`current_user.user_id` → `TeacherId` (`services/gateway/routers/teaching_pack_runs.py:84`) and
every router uses `get_run_with_ownership` (`services/gateway/routers/teaching_pack_deps.py`,
enforced by the guard test `services/gateway/tests/test_no_unscoped_accessor_in_routers.py`).
Roles already include `SCHOOL_ADMIN` and `SYSTEM_ADMIN`
(`services/gateway/auth/models.py:20-30`; `TEACHER_ROLES` / `ADMIN_ROLES` frozensets), but there
is no `org`/`school` entity, so a `school_admin` cannot see or govern the runs of teachers in
their school, and quotas cannot be applied at a school level.

Backpressure is per-teacher + global only
(`BackpressureConfig.max_active_runs_per_teacher=3`, `max_total_active_runs=20`, etc.,
`services/gateway/backpressure.py:36-42`); budget is per-run (`services/gateway/budget.py`).
At the north-star scale (~1,000 teachers across many schools) a single school could either be
starved by the global cap or monopolize it — there is no per-org fairness or attribution.

ADR-034 decision 6: additive **org/school layer** (`org_id`) with org-scoped quotas + query
scoping; **row-scoping/RLS, NOT physical isolation** (no per-tenant DB/schema).

The `runs` table (`services/gateway/models.py:75-103`) has `teacher_id` but no `org_id`. There is
no `orgs` table and no teacher→org membership.

## Scope

- [ ] Add an `organizations` table (`org_id` PK, name, created_at, status) and a
      teacher→org membership (either an `org_id` FK on `users` for the single-org case, or an
      `org_memberships` join table if a teacher may belong to multiple schools — pick single-org
      unless product says otherwise; document the choice).
- [ ] Add **additive, nullable-then-backfilled** `org_id` FK column to `runs`
      (`services/gateway/models.py`) and to `run_jobs` (so queue-level quotas can scope by org).
      Expand-contract: add nullable → backfill (OPS-14) → enforce NOT NULL + FK in a later
      contract migration. New Alembic revision after `019_*` (next id `020_org_tenancy.py`).
- [ ] Stamp `org_id` at run-create time from the authenticated teacher's org
      (`teaching_pack_runs.py` create path, alongside the existing `teacher_id` stamp at line 84).
      Fail-closed: a teacher with no resolvable org must not silently create an org-less run —
      either assign a default personal org or reject with a clear error.
- [ ] Org-scoped quotas: extend `BackpressureConfig` with `max_active_runs_per_org` and
      `max_queued_runs_per_org`, and add per-org counting queries in `check_backpressure`
      (`services/gateway/backpressure.py:60+`) alongside the existing per-teacher and global
      checks. Order of checks: per-teacher → per-org → global; the most specific violated limit
      wins in the `reason` string (matches existing `reason=f"..."` style at lines 132-146).
- [ ] Org-scoped budget caps: extend budget so an org has an aggregate cap in addition to the
      per-run `BudgetConfig` (`services/gateway/budget.py`) — a rolling per-org daily/period ceiling
      the platform can attribute and (optionally) enforce. Cost is not a hard constraint per the
      north star, so this is primarily **attribution/capacity**, but the cap must be enforceable.
- [ ] Query scoping so `school_admin` sees org-wide runs: add an org-scoped accessor
      (parallel to `get_run_with_ownership`) used by admin/list endpoints. A `school_admin` sees
      runs where `run.org_id == caller.org_id`; a `system_admin` sees all; a `teacher` still sees
      only their own rows. Extend the router guard test
      (`test_no_unscoped_accessor_in_routers.py`) so org-list endpoints must go through the
      org-scoped accessor (no raw unscoped queries).
- [ ] Usage attribution per org: an aggregate view/rollup of runs, tokens
      (`runs.tokens_used`), cost (`runs.cost_usd`), success rate, and queue depth **grouped by
      `org_id`** — feed the OPS-03 KPI dashboard so capacity can be reasoned about per school.
- [ ] Defense-in-depth: add Postgres **Row-Level Security (RLS)** policies on `runs`/`run_jobs`
      keyed on a session-set `app.current_org_id` / `app.current_teacher_id`, so a query bug
      cannot leak cross-org rows. RLS is a backstop, not a replacement for app-level scoping.
      Document how the connection sets the session vars per request.

## Acceptance

- A `school_admin` calling the org-list endpoint sees exactly the runs of teachers in their org
  and none from other orgs; a teacher sees only their own; a `system_admin` sees all — proven by
  a live-path test against a real DB with ≥2 orgs and cross-org rows.
- Creating runs past `max_active_runs_per_org` returns a backpressure rejection with an
  org-scoped `reason`; per-teacher and global limits still fire independently.
- With app-level scoping deliberately bypassed in a test, RLS still prevents cross-org row reads.
- `org_id` is populated on all new runs; the backfill (OPS-14) fills historical rows; the
  contract migration enforcing NOT NULL runs clean.
- Per-org usage rollup returns correct token/cost/success aggregates for a known fixture.

## References

- `services/gateway/routers/teaching_pack_runs.py:84` — per-teacher stamp at create.
- `services/gateway/routers/teaching_pack_deps.py` — `get_run_with_ownership`.
- `services/gateway/tests/test_no_unscoped_accessor_in_routers.py` — router-scoping guard test.
- `services/gateway/auth/models.py:20-35` — roles + `TEACHER_ROLES`/`ADMIN_ROLES`.
- `services/gateway/backpressure.py:36-146` — `BackpressureConfig`, per-teacher/global checks.
- `services/gateway/budget.py` — per-run budget.
- `services/gateway/models.py:62-103` — `User` and `Run` tables (no `org_id` today).
- `services/gateway/alembic/versions/` — migrations (next id `020_*`).
- ADR-034 decision 6.

## Implementation notes

- Keep it **additive**: no rename of `teacher_id`; org is a new axis layered above it.
- Prefer a single `org_id` FK on `users` for v1 (a teacher belongs to one school). Multi-org
  membership is a strictly larger change — only build it if product requires it now.
- RLS session vars: set `SET LOCAL app.current_org_id = ...` inside the request/session scope so
  they never leak across pooled connections; verify with a pooled-connection test.
- Fail-closed on org resolution: no org ⇒ explicit error or explicit personal-org, never a
  silently unscoped/null-org run that would escape org quotas and RLS.
- Depends on OPS-14 for the backfill of historical `org_id`; ship the nullable column here and
  the NOT-NULL contract migration only after backfill lands.
