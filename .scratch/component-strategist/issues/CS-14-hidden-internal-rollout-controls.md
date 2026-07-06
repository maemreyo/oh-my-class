---
title: Enable hidden/internal Component Strategist rollout controls
status: ready-for-agent
labels: [component-strategist, rollout, feature-flag]
created: 2026-07-06
---

## Parent

`.omo/ulw-research/20260706-103328-component-strategist-web/ROUGH-REPORT-verdicts-and-direction.md`

## What to build

Enable the Component Strategist code path across local, staging, and production while keeping production hidden/internal. The rollout must support an immediate global kill switch, explicit admin/dev and teacher-test allowlisting, and run-level behavior pinning so an in-flight run does not change strategist behavior halfway through execution.

This slice is for internal/pre-user Vietnamese improvement only. It must not expose a public MOET-compliant claim or open the strategist broadly to production tenants.

## Acceptance criteria

- [ ] A global control can disable the Component Strategist path immediately without code changes.
- [ ] Production strategist access is limited to admin/dev accounts and explicit teacher test accounts.
- [ ] Each run records the strategist enablement decision so resumed/in-flight runs keep the same behavior.
- [ ] Flag-off behavior and old runs without component strategy plans remain compatible.
- [ ] Tests prove allowed accounts use the strategist path, non-allowlisted production accounts stay on the safe path, and the kill switch restores safe behavior.

## Blocked by

- CS-04 LangGraph stage and blueprint payload.
- CS-08 golden scenarios, CLI smoke, and E2E release gate.
- CS-10 knowledge lifecycle, versioning, and capability-manifest governance.
