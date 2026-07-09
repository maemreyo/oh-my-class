---
name: anatomy
description: >-
  Traces a codebase from its actual source code, never from existing
  README/docs/comments which may be stale or simply wrong, and produces or
  updates accurate system documentation as a set of files: one file per
  module, an index file, and a system-diagram.md with Mermaid diagrams of
  how modules interact. Use this whenever the user asks to trace, map,
  document, or reverse-engineer a codebase architecture; wants to
  understand or record how modules, services, or packages interact; asks to
  generate, refresh, or update architecture docs, onboarding docs, or a
  folder like docs/system-trace or docs/architecture; or wants written
  documentation built directly from code rather than from what is already
  written about it. Also triggers when re-running against a codebase that
  already has a docs/system-trace output from before, since this skill
  detects that and updates only what changed instead of starting over.
  Works for any language or project shape: monolith, monorepo,
  microservices, or library.
---

# Anatomy

## Why this exists

Existing documentation drifts from the code it describes -- features change,
comments don't get updated, READMEs get copy-pasted between projects. A
documentation generator that summarizes what's already written just launders
that drift into something that *looks* newly verified. This skill instead
treats the source code as the only ground truth and existing docs as claims
to check against it, then writes down what it actually finds -- including
where the old docs were wrong. See `references/tracing-methodology.md` for
the full reasoning; it's worth reading before the tracing phase (Phase 4)
because it shapes how you read code, not just what you write down afterward.

## Output contract

Unless the user specifies a different location, write to `docs/system-trace/`
at the repository root:

```
docs/system-trace/
├── index.md              overview, module table, entry points, links out
├── system-diagram.md     Mermaid architecture diagram + key-flow sequences
├── modules/
│   └── <module-slug>.md  one file per module (see output-templates.md)
└── _manifest.json        internal state enabling incremental updates
```

Exact file content/structure: `references/output-templates.md`. Don't
improvise the structure from scratch -- the templates exist so every run
(and every different codebase) produces a consistent, cross-linked set of
files, which is part of what makes the output trustworthy rather than just a
one-off writeup.

If the user names a different output path or asks to scope the trace to a
subdirectory (e.g. "just trace the backend/ folder"), honor that -- the
manifest and phases below still apply, just rooted wherever they said.

## Workflow

### Phase 0 -- Check for a pre-existing output folder

Before doing anything else, check whether the output root already exists
(and specifically whether `_manifest.json` is in it). This determines
whether the rest of the run is a **full trace** or an **incremental
update**. Full decision tree, manifest schema, and the reasoning behind
content-hash-based diffing: `references/incremental-updates.md`. Read it now
if `docs/system-trace/` (or wherever the user pointed) already has anything
in it -- don't guess at update logic inline.

If it's a clean full trace (nothing exists yet), skip ahead to Phase 1.

### Phase 1 -- Inventory the codebase

Run the inventory script rather than manually `find`/`ls`-ing your way
around -- it's faster and gives you a structured starting point:

```bash
python3 scripts/inventory.py <repo_root> --max-depth 3
```

This returns: total file count, a language histogram, detected manifest
files (package.json, pyproject.toml, go.mod, Cargo.toml, pom.xml, etc. --
parsed for a few key fields where possible), a bounded directory tree with
file counts, top-level directories, the largest source files by line count
(useful later for prioritization), and any `ambiguous_dirs_found` (dir names
like `packages` or `vendor` that could be real modules or vendored
dependencies -- worth a direct look before deciding which).

Use this to understand: what language(s)/stack this is, how the project is
built/run (from the manifests), and what the candidate module-root
directories are.

### Phase 2 -- Decide module boundaries

Turn the candidate directories from Phase 1 into an explicit module list: a
slug -> relative-path mapping. This is a judgment call that depends on the
project's shape (monorepo, microservices, layered monolith, library) --
`references/module-detection.md` covers heuristics and worked conventions
for common frameworks, sizing guidance (prefer ~5-40 modules total, not one
file per class), and how to handle entry points and infra-as-code that don't
fit neatly into "just another module."

Write this mapping down (even just mentally structured, or as a scratch
JSON) before moving on -- Phase 3 and the incremental-update machinery in
Phase 0/6 both consume it as `modules.json`:
```json
{"api": "src/api", "services": "src/services", "...": "..."}
```

### Phase 3 -- Build an interaction hypothesis

```bash
python3 scripts/import_graph.py <repo_root> --group-by-top-level
```

This extracts import/require/use statements per file via per-language
regexes and rolls them up into top-level-directory edges with counts (e.g.
`api -> services: 12`). Treat this strictly as a **hypothesis to verify**,
not an answer -- it cannot know whether an import is actually used, used
once or constantly, or dead. It tells you fast where to look across a
codebase too large to grep through by hand; it does not tell you what's
really happening at each edge. That verification happens in Phase 4.

### Phase 4 -- Trace and verify each module

This is the core of the skill and the part that most needs care. For each
module in your Phase 2 list (in incremental mode: for each module in the
diff's `changed` + `added` sets only -- see Phase 0/6):

1. Read its public surface first, then trace inward from there.
2. Confirm or correct every Phase 3 hypothesis edge by opening the actual
   call site.
3. Never write a claim into a module doc that you haven't confirmed by
   reading code -- if an existing README/comment says something, check it
   against the implementation, and flag it in the doc if they disagree.
4. Scale your depth to the module's size -- read everything for a small
   module, prioritize by reference-count/size for a huge one, and say
   plainly what you covered versus sampled.

Full methodology, reading order, and how to describe an interaction's real
nature (sync vs async, trigger, failure behavior) rather than just its
existence: `references/tracing-methodology.md`. Read this before starting
Phase 4 if you haven't already -- it changes how you read, not just what you
write.

### Phase 5 -- Write the outputs

Write each module's `modules/<slug>.md`, then `index.md`, then
`system-diagram.md`, following `references/output-templates.md` exactly for
structure (adapt section content to what actually applies to each module,
but keep the overall shape consistent). Every edge in `system-diagram.md`
and every "Depends on"/"Used by" line in a module doc should be traceable to
something you actually confirmed in Phase 4 -- cross-check the diagram
against the module docs before considering this phase done.

In incremental mode: only `changed`/`added` modules get their
`modules/<slug>.md` rewritten; `removed` modules get their file deleted;
`unchanged` modules are left alone entirely. `index.md` and
`system-diagram.md` are always regenerated in full regardless of mode --
see `references/incremental-updates.md` for why.

### Phase 6 -- Update the manifest

```bash
python3 scripts/state.py hash-modules <repo_root> modules.json > fresh_hashes.json
python3 scripts/state.py git-commit <repo_root>   # null if not a git repo
python3 scripts/state.py write <output_root>/_manifest.json manifest_data.json
```

`manifest_data.json` should contain `{"version": 1, "source_root": ...,
"modules": <fresh_hashes.json content>}`; `source_commit` gets merged in from
the git-commit call. See `references/incremental-updates.md` for the exact
schema if anything is unclear.

### Phase 7 -- Report back

Tell the user, briefly: which mode ran (full vs incremental) and why, which
modules were touched vs left alone, anything removed, and -- this is often
the most useful part -- any discrepancies you found between the old docs and
what the code actually does. Point them at `index.md` as the entry point.

## A note on languages the user writes in

Write the skill's own output (module docs, index, diagrams) in English by
default, since that's the most common convention for technical docs and this
skill is used across many projects -- but if the codebase's own comments/docs
are strongly and consistently in another language, or the user explicitly
asks for a different output language, follow that instead. Your
conversation with the user, separately, should always be in whatever
language they're using.

## Scripts reference

All three scripts are stdlib-only Python (3.8+), no installs required:

- `scripts/inventory.py` -- Phase 1, structural overview
- `scripts/import_graph.py` -- Phase 3, heuristic interaction hypothesis
- `scripts/state.py` -- Phase 0/6, manifest hash/diff/write for incremental
  updates (subcommands: `hash-modules`, `diff`, `write`, `git-commit`)

Run any of them with no arguments (or read the top-of-file docstring) to see
usage details.

## Reference files

- `references/module-detection.md` -- how to draw module boundaries for
  different project shapes; read during Phase 2
- `references/tracing-methodology.md` -- the verification discipline and
  scaling strategy; read before Phase 4
- `references/output-templates.md` -- exact structure for all three output
  file types; read during Phase 5
- `references/incremental-updates.md` -- the full decision tree and manifest
  schema for handling a pre-existing output folder; read during Phase 0 (and
  Phase 6 when writing the manifest back)
