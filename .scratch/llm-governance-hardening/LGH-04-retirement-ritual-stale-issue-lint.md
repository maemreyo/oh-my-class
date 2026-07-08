---
title: "Formalize .scratch issue status schema + stale-issue report"
status: ready-for-agent
labels: [governance, process, scratch]
created: 2026-07-08
priority: p3
epic: llm-governance-hardening
sequence: 4
---

> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 3. The `status: superseded` (+ `superseded: <date>`) convention already exists informally — used for real in `.scratch/9router-integration/ISSUE.md` and `.scratch/litellm-proxy/ISSUE.md` as of commit `ec10283`. As of 2026-07-08 there are 22 `status: ready`, 10 `ready-for-agent`, and 1 `deferred` issues in `.scratch/` of unknown freshness.

## What to build

1. Document the `status` field's fixed enum (`ready | ready-for-agent | deferred | done | superseded`) and the `superseded`/`created` date-field convention in a short `.scratch/README.md` or similar, if one doesn't already exist.
2. `scripts/check_stale_scratch_issues.py`: list every `.scratch/**/ISSUE.md` (and this session's `LIC-*`/`LGH-*` issue files, once numbered issue files are adopted more broadly) with `status` in `{ready, ready-for-agent, deferred}` and `created` older than 3 months. Print as a report — **do not fail CI** on this (staleness is a signal for human review, not an automatic verdict — an issue can legitimately sit `ready` for a long time waiting on priority, not because it's superseded).
3. Run it as a scheduled/manual report, not a PR-blocking gate.

## Acceptance criteria

- [ ] `status` enum documented somewhere discoverable (README or CONTRIBUTING).
- [ ] Report script correctly parses frontmatter across the existing `.scratch/**/ISSUE.md` and epic-numbered files (`LIC-*.md`, `LGH-*.md`, `td-*`, `vb-*`, `sdh-*`, etc. — confirm frontmatter schema is consistent enough across all of them, or scope the script to files that have a `status:` field at all).
- [ ] First run's output is triaged at least once (some of the current 22 `ready` + 10 `ready-for-agent` + 1 `deferred` issues may turn out to be superseded already) as a smoke test that the script is useful, not just theoretically correct.

## Blocked by

Nothing.
