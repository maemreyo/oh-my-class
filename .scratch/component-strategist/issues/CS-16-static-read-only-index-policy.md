---
title: Lock v1 SQLite index to static read-only runtime policy
status: ready-for-agent
labels: [component-strategist, knowledge-db, sqlite]
created: 2026-07-06
---

## Parent

`.omo/ulw-research/20260706-103328-component-strategist-web/ROUGH-REPORT-verdicts-and-direction.md`

## What to build

Make the v1 strategy knowledge index explicitly static and read-only at runtime. Runtime should open the generated SQLite artifact for reads only, avoid hot updates, and require a rebuild/redeploy or explicit connection reopen when knowledge changes.

This slice turns the report's SQLite policy into a verifiable runtime contract without changing the knowledge authoring model.

## Acceptance criteria

- [ ] Runtime opens the generated strategy SQLite index in read-only/query-only mode.
- [ ] `immutable=1` is used only when the DB artifact cannot change during the lifetime of open connections.
- [ ] Runtime does not regenerate or mutate the SQLite index silently.
- [ ] Connection policy is explicit and safe for the deployment model used by the strategist.
- [ ] Tests prove stale/missing/mutable index scenarios fail closed or use the documented safe fallback.

## Blocked by

- CS-02 YAML knowledge DB and SQLite index.
- CS-10 knowledge lifecycle, versioning, and capability-manifest governance.
