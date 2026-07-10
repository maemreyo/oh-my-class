# Handling a pre-existing output folder

This is Phase 0 of the workflow in SKILL.md, expanded. The goal: re-running
this skill on a codebase that's already been traced should be fast and
should only touch what actually changed, while still keeping `index.md`,
`system-diagram.md`/`.html`, and `entry-points.md` fully correct for the
_current_ state of the whole system -- not just the part that changed.

## The manifest

`docs/anatomy/_manifest.json` records what was traced and a content hash
per module:

```json
{
  "version": 1,
  "source_root": "/abs/path/at/trace/time",
  "modules": {
    "api": { "hash": "sha256...", "file_count": 3 },
    "services": { "hash": "sha256...", "file_count": 5 }
  },
  "generated_at": "2026-07-09T12:34:56Z",
  "source_commit": "abc123... or null if not a git repo"
}
```

The hash is content-based (sha256 over every file in the module, produced by
`scripts/state.py hash-modules`) rather than relying on mtimes or git alone.
This matters because:

- Working trees have uncommitted changes constantly; git-commit-only
  comparison would miss them.
- Not every codebase is a git repo at all (vendored drops, extracted
  archives, a folder someone handed you).
- mtimes get touched by checkouts, CI, and editors without content actually
  changing, which would cause spurious "changed" flags.

`source_commit` is still recorded when available, purely as a friendly
reference point for the user ("last traced at commit abc123") -- never as
the sole basis for the diff decision.

Path information isn't in `_manifest.json` -- it's kept in a sibling file,
`docs/anatomy/_modules.json`, the persisted copy of Phase 2's slug ->
relative-path mapping (`{"api": "src/api", ...}`). Two consumers: Phase 2
on a later run, to reuse a still-valid path's existing slug instead of
inventing a new one (see SKILL.md's Phase 2); and `scripts/graph_export.py`,
to fill in each module's `path` field when it builds `_graph.json`. Written
at the *start* of Phase 5, before `graph_export.py` needs it -- earlier
than `_manifest.json`, which waits for Phase 6's fresh hashes -- every run,
full or incremental.

## Migrating from an older `docs/system-trace` output

Earlier versions of this skill defaulted to `docs/system-trace/` instead of
`docs/anatomy/`. If `docs/anatomy/_manifest.json` doesn't exist, check for
`docs/system-trace/_manifest.json` before concluding this is a clean first
run. If you find one there:

- Don't silently start a brand-new full trace into `docs/anatomy/` -- that
  leaves two documentation sets sitting in the same repo, with no signal to
  a future reader (or a future run of this skill) about which one is
  current, and doubles the drift-from-code problem this skill exists to
  prevent.
- Tell the user what you found and offer to migrate: `git mv
docs/system-trace docs/anatomy` (or a plain move if it's not a git repo),
  then proceed as an ordinary incremental update against the moved manifest.
  The manifest's content is location-independent (it's keyed by module
  hashes, not by its own path), so a straight rename is safe and loses
  nothing.
- If the user would rather keep the old location, that's fine -- just
  operate against `docs/system-trace/` for the rest of this run instead of
  defaulting to `docs/anatomy/`, and say so plainly in your summary so it's
  not a silent, easy-to-forget deviation from the default.

## Fast path: answering one specific question without a full run

Not every request needs the full Phase 0-7 workflow. If the user asks a
narrow, specific question -- "where does X live", "what would changing Y
break", "which module handles the `/orders` route" -- and a manifest
already exists, it's often both faster and more useful to answer directly
from the existing output than to re-run the whole workflow. SKILL.md's
Phase 0 covers exactly when to take this path instead of a full or
incremental run; this section covers the freshness check that path leans
on.

**Freshness, not just existence.** A stale `docs/anatomy/` answering a
specific question confidently is worse than not answering at all, so the
fast path always confirms freshness first -- it never just trusts that the
existing docs are current because they're present:

1. Run the same `state.py hash-modules` + `state.py diff` pair Phase 0
   already uses for incremental updates.
2. If `change_ratio` is `0.0` (nothing changed at all), the existing docs
   are current for the whole repo -- answer straight from `index.md` and
   the specific `modules/<slug>.md` file(s) the question touches, with no
   further reading needed.
3. If `change_ratio` is greater than `0.0` but the module(s) the question
   is actually about are in `unchanged` (not `changed`/`added`/`removed`),
   it's still safe to answer from the existing doc for _that_ module --
   but say so plainly ("some other modules have changed since this trace;
   `services` itself hasn't, so this answer is current") rather than
   implying the whole repo is fresh when only the relevant slice is.
4. If the relevant module _is_ in `changed`/`added`, or the question can't
   be mapped to a specific existing module at all, the fast path doesn't
   apply -- fall through to an ordinary incremental (or full) run instead
   of answering from what's now known-stale information.

This reuses the exact same diff machinery as an incremental update; the
only difference is that a fast-path answer doesn't write anything back
(no manifest update, no re-generated `index.md`/diagrams) -- it's a read,
not a run. If the user's question turns into "okay, now update the docs for
that," that's the cue to proceed into an ordinary incremental update from
here rather than trying to patch just the one file that was read.

## Decision tree

**1. Does `docs/anatomy/_manifest.json` exist?**

- **No, and neither it nor a legacy `docs/system-trace/_manifest.json`
  exists** -> straightforward full trace. This is the common case for a
  first run.
- **No, but the folder exists with other content** (hand-written docs, or
  output from a version of this skill old enough to predate the manifest
  entirely) -> there's no reliable state to diff against. Do a full trace.
  Skim what's already there first though -- if it uses module names/slugs
  that make sense, reuse them for continuity rather than picking different
  ones. Mention in your summary to the user that no prior trace-state was
  found, so this was a full trace rather than an update.
- **Yes** -> continue to step 2.

**2. Get the current module list** (Phase 1/2 of the main workflow: run
`scripts/inventory.py`, decide module boundaries per
`references/module-detection.md`).

**3. Compute fresh hashes and diff:**

```bash
python3 scripts/state.py hash-modules <repo_root> <modules.json> > fresh_hashes.json
python3 scripts/state.py diff <old_manifest_path> fresh_hashes.json
```

This returns `unchanged`, `changed`, `added`, `removed`, and a
`change_ratio` with a built-in recommendation.

**4. Decide the update scope:**

- **Nothing in changed/added/removed** -> the trace is already current.
  Still worth confirming this to the user rather than silently doing
  nothing -- e.g. "Checked for changes since the last trace (commit
  abc123) -- nothing has changed, docs/anatomy is up to date."
- **Some changed/added/removed, ratio comfortably below the ~60% line** ->
  incremental update:
  - Re-trace only the modules in `changed` and `added` (full Phase 3/4
    tracing for those specifically).
  - Delete `modules/<slug>.md` for anything in `removed`.
  - Leave `modules/<slug>.md` untouched for everything in `unchanged` --
    don't re-read or rewrite those files, other than the narrow
    edges-into-a-changed-module check below. This is the whole point of the
    manifest: it lets you skip real work, not just skip announcing it.
- **Ratio at or above ~60%, or the repo structure looks fundamentally
  reorganized** (e.g. most top-level directories are new) -> the diff
  itself will say so in its `recommendation` field. Don't silently pick a
  side here -- tell the user what the diff found and ask whether they want
  a full re-trace or to proceed incrementally anyway. A mostly-rewritten
  system is exactly the case where partial patching risks leaving the
  overall picture inconsistent.
- The user can always override either way by simply asking for a full
  re-trace, or by deleting `_manifest.json` themselves as a manual reset.

## Edges into a changed module

The hash diff tells you when a module's _own_ files changed. It says
nothing about whether an _unchanged_ module's description of its
relationship to a changed module is still accurate -- and that gap matters
more than it looks. Say module `A` is unchanged and its existing doc says
"**Depends on `B`** -- calls `B.charge()` synchronously, propagates its
errors." If `B` is in this run's `changed` set, `B.charge()` might now be
async, might have a different failure mode, might not exist anymore under
that name -- and because `A` itself didn't change, the ordinary incremental
rule ("leave unchanged modules alone") would leave that now-possibly-wrong
line sitting in `A`'s doc indefinitely. `index.md` and `system-diagram.md`
being "always regenerated in full" doesn't fix this either, because both
are compiled _from_ the "Depends on"/"Used by" lines already written in the
module docs -- if `A`'s doc is wrong, the diagram built from it is wrong in
exactly the same way, just re-rendered.

The fix is narrow, not a reason to re-trace `A` wholesale: after computing
the diff, for every `unchanged` module whose doc has a "Depends on" or
"Used by" line naming a module in `changed`, open just the specific call
site(s) between the two (not the rest of `A`) and confirm the line is still
accurate. If it's still correct, leave it alone. If it changed, edit only
that line (or that bullet) in `A`'s doc -- don't rewrite sections of `A`
that have nothing to do with `B`. This keeps the efficiency benefit of
incremental mode (you're still not re-reading all of `A`) while closing the
one specific gap where content-hash diffing can't see a real change.

## Regenerating the whole-system files

**Regenerate `index.md`, `system-diagram.md`, `system-diagram.html`,
`entry-points.md`, and `_graph.json` unconditionally**, even in incremental
mode, even if none of them individually "changed." All five describe the
_current full system_ -- a new or changed module can introduce a new edge,
route, or flow involving an otherwise-untouched module, and that must show
up. Regenerating these is cheap relative to re-tracing a module, so there's
no reason to try to diff them incrementally too. (`_graph.json` is a
re-parse of the other four once they're written, not an independent
regeneration step -- see SKILL.md's Phase 5 for the ordering.)

The part that isn't automatic: rebuilding these requires knowing every
current module's role, dependencies, and entry points -- including the ones
in `unchanged`, which Phase 4 didn't re-read this run. Get that information
by reading the _existing_ `modules/<slug>.md` file for each unchanged
module (updated already, if applicable, by the edges-into-a-changed-module
step above) rather than trying to recall it from earlier in a long
conversation, or re-deriving it from scratch, or -- worst case -- quietly
omitting unchanged modules from the new diagrams because they weren't
re-traced this run. An unchanged module still belongs in the full picture;
"unchanged" describes whether you re-verify it, not whether it exists.

**Write the updated manifest** with `scripts/state.py write`, including
hashes for every current module (changed, added, and unchanged all get
fresh/carried-forward entries) so the next run's diff is accurate.
`_modules.json` (see "The manifest" section above) was already refreshed at
the start of Phase 5, so slugs stay stable across runs too -- nothing
further to do for it here.

## Reporting back to the user

Whatever the outcome, say plainly in your final summary which mode ran (full
vs incremental), which modules were re-traced vs left alone, what (if
anything) got removed, and whether any edges-into-a-changed-module check
turned up a stale "Depends on"/"Used by" line worth calling out. This is
short to write and it's the difference between the user trusting an "up to
date" claim versus wondering whether the skill actually looked.
