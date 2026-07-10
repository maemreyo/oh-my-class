---
name: anatomy-link
description: >-
  Inserts or updates a small, marked, idempotent block in agent-instruction
  files (AGENTS.md, CLAUDE.md, and similar) that points coding agents at an
  existing `anatomy` skill output (docs/anatomy/ by default), so a fresh
  session finds the architecture docs instead of re-deriving them from
  source every time. Use whenever the user asks to "link", "wire up",
  "connect", or "hook" anatomy's docs into AGENTS.md/CLAUDE.md; wants coding
  agents to automatically discover architecture docs at the start of a
  session; or wants AGENTS.md/CLAUDE.md kept pointing at the latest
  docs/anatomy/ output after a re-trace. Safe to re-run any number of times
  -- it only touches the content between its own markers and leaves the
  rest of the file untouched. NOT for generating the architecture docs
  themselves (that's the `anatomy` skill) and NOT a general-purpose
  find-and-replace tool for arbitrary Markdown edits.
---

# Anatomy Link

## Why this exists

`anatomy` writes trustworthy architecture docs to `docs/anatomy/`, but an
agent only benefits from them if it actually reads them. Left alone, a
coding agent starting a fresh session has no way to know those docs exist
short of stumbling into the folder, so it re-derives the same architecture
understanding from source on every session -- exactly the wasted work
`anatomy` exists to avoid. `AGENTS.md` and `CLAUDE.md` are the files agents
are most likely to read first; this skill's only job is to make sure they
point at `docs/anatomy/index.md`, and to keep that pointer current, without
disturbing anything else a human wrote in those files.

## What this touches

Exactly one thing: a single marked block, delimited by
`<!-- anatomy:start -->` / `<!-- anatomy:end -->`, inside each target file.

- If the markers already exist, only the text between them is replaced.
- If they don't exist yet, the block is inserted once -- immediately after
  the file's first `#` heading if it has one, otherwise at the very top.
- Everything else in the file (a human's own notes, other sections, their
  ordering) is left byte-for-byte alone.

This makes the operation idempotent: running it again with nothing changed
produces no diff, and running it again after `anatomy` re-traces the
codebase updates only the pointer block to match.

## Workflow

### Step 1 -- Confirm there's something to link to

Check that the anatomy output actually exists before touching anything --
by default `docs/anatomy/index.md` (pass `--anatomy-root` if the user
traced to a different location, e.g. a scoped subdirectory trace). If it
isn't there, don't invent content or half-fill the block; tell the user to
run the `anatomy` skill first.

### Step 2 -- Run the linker

This is the one command the whole skill boils down to -- there is no
separate install/setup step, and nothing runs in the background. It's a
single idempotent script invocation, safe to call as often as you like:

```bash
python3 scripts/link.py <repo_root> [--anatomy-root docs/anatomy] [--targets AGENTS.md CLAUDE.md] [--create] [--check]
```

- Default targets are `AGENTS.md` and `CLAUDE.md` at the repo root. Pass
  `--targets` to add others the project actually uses (e.g. `GEMINI.md`,
  `.cursor/rules`, `.clinerules`) -- don't assume every project wants every
  possible agent file created.
- Files that don't exist are skipped by default (reported, not silently
  ignored) since creating an `AGENTS.md`/`CLAUDE.md` from scratch is a
  bigger decision than updating one that's already there. Pass `--create`
  only if the user actually wants new files created.
- Use `--check` first if you want to preview what would change without
  writing anything -- worth doing before touching a file you didn't create
  yourself.

The script reads `docs/anatomy/_manifest.json` (if present) to include a
freshness note (source commit) in the block, and checks which optional
`anatomy` outputs exist (`data-model.md`, `deployment.md`,
`system-diagram.html`) so the block only links to files that are actually
there.

### Step 3 -- Report back

Tell the user which files were updated, created, or skipped, and -- this
matters more than it sounds -- whether anything actually *changed* versus
already being up to date (the script reports both, per file). If a target
was skipped because it doesn't exist, mention that and let the user decide
whether to create it, rather than creating it unprompted.

## Running it after every `anatomy` re-trace

This skill doesn't trigger itself automatically -- each pass of `anatomy`
only writes `docs/anatomy/`, it doesn't touch `AGENTS.md`/`CLAUDE.md`.
There's no cron job or hook involved either; re-running is just re-invoking
the same script by hand (or having the agent do it) whenever it's useful --
typically right after an `anatomy` run that changes which optional files
exist (e.g. `data-model.md` gets added for the first time) or after the
source commit moves meaningfully, so the freshness note stays honest. A
routine incremental update with no structural change is harmless to skip,
since the block's content won't have changed anyway -- but there's no harm
in always re-running it either, since it's a no-op when nothing changed.

## Scripts reference

- `scripts/link.py` -- stdlib-only Python (3.8+), no installs required.
  All behavior is flags on this one script; run with `-h` for full usage.

## A note on scope

Don't extend this skill's block to summarize the codebase, restate
`anatomy`'s findings, or duplicate content that already lives in
`docs/anatomy/index.md` -- the whole point is a short pointer, not a
second copy of the docs that can itself drift out of date. If the user
wants more agent-facing context than a pointer (build commands, coding
conventions, etc.), that's a separate, hand-written part of
`AGENTS.md`/`CLAUDE.md` outside this skill's marked block.
