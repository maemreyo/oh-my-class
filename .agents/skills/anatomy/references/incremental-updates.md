# Handling a pre-existing output folder

This is Phase 0 of the workflow in SKILL.md, expanded. The goal: re-running
this skill on a codebase that's already been traced should be fast and
should only touch what actually changed, while still keeping `index.md` and
`system-diagram.md` fully correct for the *current* state of the whole
system.

## The manifest

`docs/system-trace/_manifest.json` records what was traced and a content
hash per module:

```json
{
  "version": 1,
  "source_root": "/abs/path/at/trace/time",
  "modules": {
    "api": {"hash": "sha256...", "file_count": 3},
    "services": {"hash": "sha256...", "file_count": 5}
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

## Decision tree

**1. Does `docs/system-trace/_manifest.json` exist?**

- **No, and the folder doesn't exist either** -> straightforward full trace.
  This is the common case for a first run.
- **No, but the folder exists with other content** (hand-written docs, or
  output from a much older version of this skill that predates the
  manifest) -> there's no reliable state to diff against. Do a full trace.
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
  abc123) -- nothing has changed, docs/system-trace is up to date."
- **Some changed/added/removed, ratio comfortably below the ~60% line** ->
  incremental update:
  - Re-trace only the modules in `changed` and `added` (full Phase 3/4
    tracing for those specifically).
  - Delete `modules/<slug>.md` for anything in `removed`.
  - Leave `modules/<slug>.md` untouched for everything in `unchanged` --
    don't re-read or rewrite those files. This is the whole point of the
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

**5. Regenerate `index.md` and `system-diagram.md` unconditionally**, even in
incremental mode, even if neither file's own content logically "changed."
These two files describe the *current full module set and its
relationships* -- a new or changed module can introduce a new edge to an
otherwise-untouched module (module C now calls into module A, which didn't
change itself), and that edge must show up. Regenerating these two files is
cheap relative to re-tracing a module, so there's no reason to try to diff
them incrementally too.

**6. Write the updated manifest** with `scripts/state.py write`, including
hashes for every current module (changed, added, and unchanged all get
fresh/carried-forward entries) so the next run's diff is accurate.

## Reporting back to the user

Whatever the outcome, say plainly in your final summary which mode ran (full
vs incremental), which modules were re-traced vs left alone, and what (if
anything) got removed. This is short to write and it's the difference
between the user trusting an "up to date" claim versus wondering whether the
skill actually looked.
