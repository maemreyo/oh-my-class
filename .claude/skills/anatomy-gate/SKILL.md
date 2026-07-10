---
name: anatomy-gate
description: >-
  Runs a pass/fail staleness check of an existing docs/anatomy/ output
  (written by the `anatomy` skill) against the current source tree, with
  severity ranked by how central each stale module is. Use for pre-commit
  hooks, CI checks on a pull request, or whenever the user asks whether
  docs/anatomy is stale, out of date, or needs a re-trace before merging --
  as a quick check, not a full re-trace. Triggers on requests to "check if
  the architecture docs are stale," "add a CI/pre-commit check for
  docs/anatomy," "gate this PR on docs freshness," or similar. Does not
  write or update any documentation itself -- for that, use the `anatomy`
  skill. Requires a prior `anatomy` run (a `_manifest.json` and
  `_modules.json` already sitting in the output folder); if neither
  exists, say so and point at the `anatomy` skill instead of guessing.
---

# Anatomy Gate

## Why this is a separate skill

`anatomy` itself already computes a hash-modules + diff every time it
runs (Phase 0, for deciding full vs incremental vs fast-path). That's
built for a human reading a paragraph of context before a re-trace. A
gate that runs on every commit or every PR needs something else: a
pass/fail result with an exit code, produced without loading anatomy's
full 7-Phase workflow into context just to answer "is anything stale
right now." This skill is that -- a thin wrapper that reads
`_manifest.json`/`_modules.json`/`_graph.json` and exits.

## What it does

`scripts/docs_gate.py` re-hashes each module (same content-hash logic
`anatomy`'s `state.py` uses, vendored into `scripts/_state_lite.py` so
this skill doesn't need to locate `anatomy`'s own install path at
runtime), diffs against `_manifest.json`, and -- the part a plain
`state.py diff` doesn't do -- cross-references every stale module against
`_graph.json`'s `health_signals` to rank severity:

- **high** -- a stale module that's also in `most_connected` (its docs,
  and everything that cites it in a "Depends on"/"Used by" line, are the
  most likely to now be wrong), or a module that's been added or removed
  from source entirely (no docs at all / docs for something that's gone)
- **medium** -- a stale module not otherwise flagged
- **low** -- a stale module that's also in `orphan_candidates` (nothing
  else in the traced graph depends on its documented interface)

This ranking exists specifically so a daily gate doesn't become a wall of
red that trains people to ignore it -- a stale central module should
block a merge; a stale orphan probably shouldn't by default.

## Running it

```bash
python3 scripts/docs_gate.py <output_root> [--repo-root PATH] [--fail-on {high,medium,low,none}] [--format {json,text}]
```

- `<output_root>` -- `docs/anatomy/` (or wherever the user's `anatomy` run
  wrote its output). Ask if it's not obvious; don't assume a nonstandard
  path.
- `--repo-root` -- defaults to the current working directory, which is
  correct when this runs from a pre-commit hook or a CI job checked out
  at the repo root. Pass it explicitly if you're running this from
  somewhere else (e.g. a scratch directory).
- `--fail-on` -- default `high`. This is the knob that keeps the gate
  usable day to day: `high` only blocks on the findings that actually
  matter; `--fail-on none` makes the script report-only (always exits 0),
  useful for a first rollout or a "just tell me, don't block" pre-commit
  hook while a team gets used to it.
- `--format text` -- a short human-readable summary instead of JSON, for
  local pre-commit output. JSON (the default) is the right choice for a
  CI step that another tool will parse.

Exit code is `0` for pass, `1` for fail, `2` for a setup error (no
`_manifest.json`/`_modules.json` found -- meaning `anatomy` hasn't been
run here yet). Report the exit code and the `status` field plainly; don't
paraphrase a fail as a pass or vice versa.

## Setting this up as a hook or CI check

If the user wants this wired in rather than run once:

- **Pre-commit**: a local hook entry that runs
  `python3 <path-to-this-skill>/scripts/docs_gate.py docs/anatomy --format text`
  and lets the hook framework handle the exit code.
- **CI (PR check)**: a step that runs the same command with the default
  JSON format, checked out at the repo root so `--repo-root` can be
  omitted. Suggest `--fail-on high` to start, and mention that a team can
  loosen or tighten it later based on how noisy it turns out to be in
  practice -- don't pick `--fail-on medium` or `low` by default; that's
  more likely to create the wall-of-red problem this scoring exists to
  avoid.

Don't write the hook/CI config file yourself unless the user explicitly
asks for that file -- offer it, but the command above is the actual
deliverable most people want first.

## An open question worth surfacing, not silently resolving

Content-hash diffing here is coarse: a comment-only or whitespace-only
edit to a module still counts as "changed" and will surface as a
finding. This skill does not try to filter that out with a heavristic
diff-of-the-diff (e.g. "only comments changed, skip it") -- doing so
trades a rare, low-cost false positive (an occasional needless nag) for a
much more dangerous false negative (a real behavioral change that
happens to land in the same commit as a comment tweak, silently
excused). If a user asks for that kind of filtering, say plainly that
it's a deliberate omission for this reason rather than an oversight, and
that adding it would weaken the gate's actual guarantee.

## Relationship to the other satellite skills

- `anatomy-ask` reuses this same freshness-check idea (its own vendored
  copy of the hashing logic, `scripts/_state_lite.py`) to decide whether
  to caveat an answer as possibly stale -- it doesn't call into this
  skill directly, but the underlying check is the same one.
- `anatomy-drift-watch` is a different concern: it compares two
  `_graph.json` snapshots across runs to catch structural drift (new
  cycles, rank jumps), not source-vs-docs staleness. Use that one when
  the question is "did the architecture shift," not "are the docs stale."
