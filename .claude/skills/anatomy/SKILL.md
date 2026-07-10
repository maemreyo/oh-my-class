---
name: anatomy
description: >-
  Traces a codebase from its source code, not stale docs, and writes or
  updates architecture docs under docs/anatomy/ -- module docs, an index,
  diagrams, and an entry-points inventory. Use whenever the user asks to
  trace, map, document, or reverse-engineer a codebase's architecture; wants
  an architecture, system, or dependency diagram of a codebase, service, or
  repo; wants to understand how modules, services, or packages interact; asks
  to generate or refresh architecture/onboarding docs (docs/anatomy or
  docs/architecture); or wants a full inventory of every endpoint, command, or
  background job. Also triggers on re-runs against an existing docs/anatomy
  (or older docs/system-trace) output to update only what changed, and for
  narrow questions ("where does X live", "what would changing Y break")
  against an existing trace. Works for any language or shape: monolith,
  monorepo, microservices, or library. NOT for explaining or diagramming a
  single function, file, class, or snippet in isolation.
---

# Anatomy

## Why this exists

Existing documentation drifts from the code it describes -- features change,
comments don't get updated, READMEs get copy-pasted between projects. A
documentation generator that summarizes what's already written just launders
that drift into something that _looks_ newly verified. This skill instead
treats the source code as the only ground truth and existing docs as claims
to check against it, then writes down what it actually finds -- including
where the old docs were wrong. See `references/tracing-methodology.md` for
the full reasoning; it's worth reading before the tracing phase (Phase 4)
because it shapes how you read code, not just what you write down afterward.

## Output contract

Unless the user specifies a different location, write to `docs/anatomy/` at
the repository root:

```
docs/anatomy/
├── index.md              overview, tech stack, module table, entry points, links out
├── system-diagram.md     Mermaid: optional system-context + module graph + key-flow sequences
├── system-diagram.html   same content, standalone and interactive -- opens in any browser
├── entry-points.md       every HTTP route / CLI command / queue consumer / cron job, in one place
├── data-model.md         ERD-style data model -- only written if the project actually has a datastore
├── deployment.md         deployment/infra topology -- only written if compose/k8s manifests exist
├── modules/
│   └── <module-slug>.md  one file per module (see output-templates.md)
├── _manifest.json        internal state enabling incremental updates
├── _modules.json         internal state: Phase 2's slug -> path mapping, persisted
└── _graph.json           machine-readable snapshot of the whole graph (see graph_export.py)
```

Exact file content/structure: `references/output-templates.md`. Don't
improvise the structure from scratch -- the templates exist so every run
(and every different codebase) produces a consistent, cross-linked set of
files, which is part of what makes the output trustworthy rather than just a
one-off writeup. `data-model.md` and `deployment.md` are conditional --
`output-templates.md` has the criteria for when to write them and when to
skip them outright.

If the user names a different output path or asks to scope the trace to a
subdirectory (e.g. "just trace the backend/ folder"), honor that -- the
manifest and phases below still apply, just rooted wherever they said.

If you're picking up a codebase that was previously traced by an older
version of this skill, its output may still be sitting in `docs/system-trace/`
-- the default location this skill used to write to. Phase 0 checks for that
and helps migrate rather than silently starting a second, orphaned copy.

## Workflow

### Phase 0 -- Check for a pre-existing output folder

Before doing anything else, check whether the output root already exists
(and specifically whether `_manifest.json` is in it). This determines
whether the rest of the run is a **full trace**, an **incremental
update**, or -- if the user's request is a narrow, specific question rather
than a request to generate/refresh documentation -- a **fast-path answer**
that reads the existing output without re-running the workflow at all. Full
decision tree, manifest schema, and the reasoning behind content-hash-based
diffing: `references/incremental-updates.md`. Read it now if `docs/anatomy/`
(or wherever the user pointed) already has anything in it -- don't guess at
update logic inline.

**Fast path first, if it applies.** If `_manifest.json` exists and the
user's message is a specific question ("where does X live", "what would
changing Y break", "which module handles the `/orders` route") rather than
an instruction to trace/document/refresh, check
`references/incremental-updates.md`'s "Fast path" section before starting
any of Phases 1-7 -- a fresh-enough existing trace can usually answer this
directly from `index.md` plus the relevant `modules/<slug>.md`, which is
both faster and lower-risk than redoing work that's already been done. This
is still a judgment call, not a rule to apply blindly: if the freshness
check comes back stale for the relevant module, or the question doesn't map
cleanly onto anything already traced, fall through to an ordinary
incremental (or full) run below instead of forcing an answer from
information that's known to be out of date.

If nothing exists at `docs/anatomy/`, also check for a `docs/system-trace/`
folder with a `_manifest.json` in it before assuming this is a clean first
run -- that's the older default location this skill used to write to.
Finding one there means a prior trace already exists, just under a name
this version no longer defaults to; see `references/incremental-updates.md`'s
"Migrating from an older docs/system-trace output" section for how to handle
that (offer to migrate) instead of silently starting a fresh full trace next
to an orphaned old one.

If it's a clean full trace (nothing exists anywhere), skip ahead to Phase 1.

### Phase 1 -- Inventory the codebase

Run the inventory script rather than manually `find`/`ls`-ing your way
around -- it's faster and gives you a structured starting point:

```bash
python3 scripts/inventory.py <repo_root> --max-depth 3
```

This returns: total file count, a language histogram, detected manifest
files (package.json, pyproject.toml, go.mod, Cargo.toml, pom.xml, etc. --
parsed for a few key fields where possible), `ci_config` (best-effort parse
of `.github/workflows/*.yml`/`.circleci/config.yml` -- the actual
build/test/lint commands CI runs, which is stronger ground truth for
`index.md`'s "How to build/test" line than a guessed-at package.json script
name), a bounded directory tree with file counts, top-level directories,
the largest source files by line count (useful later for prioritization),
and any `ambiguous_dirs_found` (dir names like `packages` or `vendor` that
could be real modules or vendored dependencies -- worth a direct look
before deciding which).

Use this to understand: what language(s)/stack this is, how the project is
built/run and tested (from the manifests and `ci_config`), and what the
candidate module-root directories are.

### Phase 2 -- Decide module boundaries

Turn the candidate directories from Phase 1 into an explicit module list: a
slug -> relative-path mapping. This is a judgment call that depends on the
project's shape (monorepo, microservices, layered monolith, library) --
`references/module-detection.md` covers heuristics and worked conventions
for common frameworks, sizing guidance (prefer ~5-40 modules total, not one
file per class), and how to handle entry points and infra-as-code that don't
fit neatly into "just another module."

Write this mapping down as an actual `modules.json` file (not just
mentally) before moving on -- Phase 3's `--modules` flag and the
incremental-update machinery in Phase 0/6 both read it from disk, not from
context:

```json
{ "api": "src/api", "services": "src/services", "...": "..." }
```

If this is an incremental update, check `<output_root>/_modules.json` (the
previous run's persisted mapping, written at the start of Phase 5) before
inventing fresh slugs: for any path that still maps to the same directory,
reuse its existing slug rather than deriving a new one. A module's slug is
its filename, its `_graph.json` key, and -- for the multi-repo-stitching
case `_graph.json` exists to enable -- a join key another repo's trace
might reference; letting it churn between runs for a module that didn't
meaningfully change breaks all three for no reason.

### Phase 2.5 -- Choose a trace depth: deep vs quick-scan

Now that you have a module count and a sense of scale from Phases 1-2,
decide (or ask the user to decide) between **deep** mode -- the default,
every module fully traced and every edge confirmed -- and **quick-scan**
mode, which trades completeness for speed on a genuinely large codebase by
tracing hotspots in full and marking the rest explicitly "unconfirmed"
rather than silently inferring them at the same confidence as everything
else. `references/tracing-methodology.md`'s "Choosing a trace depth"
section has the full reasoning, what counts as large enough to bring this
up, and exactly how "unconfirmed" gets marked in both the module docs and
the diagrams. Read it now if you haven't already.

For a small-to-medium codebase (comfortably under the "tens of modules,
hundreds of files" threshold), skip the question and default to deep mode
without asking -- there's no real tradeoff to present. For a large one,
ask; don't silently pick a mode on the user's behalf the way earlier
versions of this skill used to.

If this is an **incremental update** (Phase 0 determined that already),
this choice only applies to modules in `changed`/`added` this run --
`unchanged` modules keep whatever depth they were traced at previously,
recorded in their own doc's coverage line.

### Phase 3 -- Build interaction hypotheses

```bash
python3 scripts/import_graph.py <repo_root> --group-by-top-level --modules modules.json
python3 scripts/external_calls.py <repo_root> --modules modules.json
```

Pass `--modules modules.json` (the Phase 2 slug -> relative-path mapping,
saved to an actual file) to both -- without it, edges get grouped by the
first path segment under the repo root, which is wrong for any project with
a wrapping directory before its real module dirs (`src/api`, `src/services`,
`app/controllers`, ... -- see `references/module-detection.md`'s "layered
monolith" shape) since every file's first segment is then the same wrapper
and cross-module edges disappear entirely. `--modules` is optional only
because Phase 2 might not be done yet the very first time you look at a
codebase; by the time Phase 3 actually runs, it normally is.

`import_graph.py` extracts import/require/use statements per file via
per-language regexes and rolls them up into module-to-module edges with
counts (e.g. `api -> services: 12`). Treat this strictly as a **hypothesis
to verify**, not an answer -- it cannot know whether an import is actually
used, used once or constantly, or dead. It tells you fast where to look
across a codebase too large to grep through by hand; it does not tell you
what's really happening at each edge. That verification happens in Phase 4.

`import_graph.py` only sees edges that go through an import statement in
the same language, which makes it structurally blind to the interactions
that often dominate a microservices or event-driven system: an HTTP call
from one service to another, a gRPC stub invocation, a message published to
a queue and consumed somewhere else, a cron job, a webhook registration --
none of these show up as an import anywhere, and without a script looking
for them they depend entirely on Claude happening to notice while reading a
module in Phase 4. `external_calls.py` closes that gap: it greps for common
patterns of HTTP clients, gRPC stubs, queue publish/subscribe calls (matched
by topic/event-name string, so a publisher in one module and a subscriber in
another surface as a hypothesized pair even with zero shared imports), cron
decorators/files, and webhook route registrations, across languages. Same
caveat as `import_graph.py` -- a hypothesis generator, not ground truth, and
it will miss anything wired through a framework or pattern it doesn't
recognize. Run it on every project, not just ones that look like
microservices -- plenty of "monoliths" still call out to a payment gateway,
send webhooks, or run a cron job tucked away in an infra folder.

### Phase 4 -- Trace and verify each module

This is the core of the skill and the part that most needs care. For each
module in your Phase 2 list (in incremental mode: for each module in the
diff's `changed` + `added` sets only -- see Phase 0/6; in quick-scan mode,
per Phase 2.5: hotspot modules get the full treatment below, the rest get
the lighter "unconfirmed" treatment described in
`references/tracing-methodology.md`):

1. Read its public surface first, then trace inward from there.
2. Confirm or correct every Phase 3 hypothesis edge -- both the
   `import_graph.py` kind and the `external_calls.py` kind -- by opening
   the actual call site.
3. Never write a claim into a module doc that you haven't confirmed by
   reading code -- if an existing README/comment says something, check it
   against the implementation, and flag it in the doc if they disagree.
   Cite the file:line you confirmed it at on every "Depends on"/"Used by"
   line, not only on discrepancies -- see `references/output-templates.md`.
4. Scale your depth to the module's size -- read everything for a small
   module, prioritize by reference-count/size for a huge one, and say
   plainly what you covered versus sampled. (This is about depth _within_
   a module you're tracing at full discipline -- whether every module gets
   that treatment at all is Phase 2.5's separate deep-vs-quick-scan
   decision.)

Full methodology, reading order, how to describe an interaction's real
nature (sync vs async, trigger, failure behavior) rather than just its
existence, and how to handle wiring that's resolved at runtime instead of at
import time (DI containers, plugin registries, `importlib`/reflection --
none of Phase 3's scripts can see these, and they're easy to silently miss):
`references/tracing-methodology.md`. Read this before starting Phase 4 if
you haven't already -- it changes how you read, not just what you write.

While you're in a module's public surface, keep a running note of every
route, CLI command, queue consumer, and cron job it exposes. Phase 5 rolls
these up across the whole system into `entry-points.md`, and it's
considerably cheaper to jot them down here than to reopen every module doc
afterward hunting for them again.

**Before moving to Phase 5, derive "Used by" by transposing "Depends on."**
A module's own code can only tell you what it calls out to -- it can never
tell you who calls into it, because that information doesn't live in the
module itself. So once every module in scope has confirmed "Depends on"
edges (all modules for a full trace; `changed`/`added` modules for
incremental, combined with the "Depends on" data already sitting in
`unchanged` modules' existing docs), build the reverse mapping: if X's
confirmed "Depends on" includes Y, then Y's "Used by" includes X. This is
bookkeeping over data you already have, not new reading -- but it's easy to
skip by accident if each module doc gets written in isolation right after
that module's own Phase 4 pass, since "who uses me" simply isn't visible
from inside the module being read. `references/tracing-methodology.md` has
the fuller version of this under "Reading order per module."

### Phase 5 -- Write the outputs

Before writing any module docs, copy Phase 2's `modules.json` into the
output root as `<output_root>/_modules.json` (create `<output_root>` now if
this is a first run and nothing's been written there yet). This has to
happen this early, not in Phase 6 with the rest of the manifest, because
`graph_export.py` at the end of this phase reads it back -- writing it
later would leave `graph_export.py` with no path data on a first run, and
stale path data (missing this run's added/changed modules) on an
incremental one.

Write each module's `modules/<slug>.md` first, then run
`scripts/rollup.py <output_root>` (once module docs exist -- see below),
then the whole-system files in this order: `entry-points.md`, `index.md`,
`system-diagram.md`, `system-diagram.html`, and -- only if they actually
apply to this project -- `data-model.md` and `deployment.md`. Follow
`references/output-templates.md` exactly for structure (adapt section
content to what actually applies to each module or project, but keep the
overall shape consistent). Every edge in `system-diagram.md`/`.html` and
every "Depends on"/"Used by" line in a module doc should be traceable to
something you actually confirmed in Phase 4 -- run `scripts/verify_diagram.py`,
`scripts/verify_entry_points.py`, and `scripts/verify_health_signals.py`
(see below) to check this mechanically before considering the phase done,
rather than only eyeballing it.

`index.md`'s "Architecture narrative" and "Codebase health signals"
sections are new-ish and easy to shortchange -- don't skip them or reduce
them to boilerplate. The narrative is a few sentences of synthesis in your
own words (dominant pattern, where complexity concentrates, anything
surprising versus the project's own claims about itself) written _after_
Phase 4's module docs exist, not drafted speculatively beforehand. The
health signals section is populated from `scripts/rollup.py`'s output
(most-connected modules, orphan candidates, dependency cycles, trace
coverage) -- run it once, don't hand-count any of this by re-reading every
module doc yourself. See `references/output-templates.md`'s `index.md`
template for both.

`data-model.md` and `deployment.md` are conditional, not automatic -- skip
either outright (don't write an empty or apologetic stub) if the project
has no real datastore or no container/orchestration manifests to draw from.
`references/output-templates.md` has the criteria for each.

`system-diagram.html` is a standalone, interactive rendering of the same
graph and flows in `system-diagram.md`, built by filling in
`assets/diagram-template.html` -- not improvised from scratch each run (see
`references/output-templates.md` for exactly how to fill it in). The reason
for keeping both formats: `system-diagram.md`'s Mermaid renders natively on
GitHub/GitLab, but is inert code-block text anywhere else (a plain editor,
Slack, a browser without a Markdown-plus-Mermaid viewer); the `.html` file
opens and renders in any browser with no dependency on the viewer. Build
both from the same module/edge/flow data you assembled for Phase 4 rather
than writing the Mermaid and the HTML data independently -- that's what
keeps them from quietly drifting apart from each other over successive runs.

In incremental mode: only `changed`/`added` modules get their
`modules/<slug>.md` rewritten; `removed` modules get their file deleted;
`unchanged` modules are left alone -- with one narrow exception. If an
`unchanged` module's existing doc has a "Depends on" or "Used by" line
pointing at a module that's in this run's `changed` set, re-open just that
specific call site (not the whole module) and confirm the line is still
accurate. The module itself didn't change, but the thing it depends on did,
and that's precisely the case the content-hash diff can't catch on its own
-- see `references/incremental-updates.md`'s "Edges into a changed module"
section for why this matters and how narrow the fix should stay.
`index.md`, `system-diagram.md`, `system-diagram.html`, and
`entry-points.md` are always regenerated in full regardless of mode -- see
`references/incremental-updates.md` for why, and for how to carry forward
correct information for unchanged modules without re-tracing them.

**Before leaving Phase 5, run the consistency checks:**

```bash
python3 scripts/verify_diagram.py <output_root>
python3 scripts/verify_entry_points.py <output_root>
python3 scripts/verify_health_signals.py <output_root>
```

`verify_diagram.py` mechanically cross-references `system-diagram.md`'s
module graph against every `modules/*.md`'s "Depends on"/"Used by"
sections, catching exactly the kind of drift "cross-check the diagrams
against the module docs" asks you to do by eye -- a missing "Used by"
line, a diagram edge nothing backs up, a module doc whose "Depends on" and
the corresponding module's "Used by" disagree with each other.
`verify_entry_points.py` does the same check for `entry-points.md` against
each module's "Public interface" section -- the exact same
lifted-from-elsewhere relationship, and the exact same drift risk, just a
different pair of files. `verify_health_signals.py` checks the third such
relationship: it re-runs `rollup.py`'s computation fresh and compares it
against what `index.md`'s "Codebase health signals" section actually says
-- catching the case where that section got hand-approximated in prose
instead of copied from `rollup.py`'s output as instructed above (a wrong
most-connected ranking, a "none found" for cycles/orphans that isn't
true, or a trace-coverage claim that outruns what the module docs' own
footers say). Run all three regardless of mode (full or incremental),
since they check the final state of the output, not what changed this
run. If any flags something, open the module(s) or section involved and
fix whichever side is wrong -- don't just delete or reword the flagged
line to make it quiet. An empty result from all three means the diagram,
entry-points.md, index.md's health signals, and the module docs all agree
with each other; it doesn't mean any of it is correct against the actual
source code, which is what Phase 4 is for.

Once all three checks are clean, export the structured snapshot:

```bash
python3 scripts/graph_export.py <output_root> --write
```

This writes `<output_root>/_graph.json` -- a machine-readable snapshot of
the same module/edge/entry-point graph the rest of Phase 5 just wrote as
prose, for another tool (a CI freshness check, a different repo's run of
this skill doing multi-repo stitching, an unrelated agent) to consume
without re-parsing Markdown. Run it last, after the verify scripts, not
instead of them -- it re-parses their already-written output and inherits
whatever drift they'd have caught. It only reads what's already on disk;
it doesn't re-verify anything against source. Regenerate it every run,
same as `index.md` and the diagrams, regardless of full vs incremental
mode -- see `references/output-templates.md`'s "_graph.json" section for
the schema and known limitations.

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

`<output_root>/_modules.json` was already written at the start of Phase 5
(it has to exist before `graph_export.py` runs at the end of that phase) --
nothing further to do for it here. Between the two, `_manifest.json` and
`_modules.json` give a future run everything it needs: what was traced and
its content hash (for the diff), and where each module lives (for slug
continuity and for `_graph.json`'s `path` field).

### Phase 7 -- Report back

Tell the user, briefly: which mode ran (full vs incremental, and deep vs
quick-scan if quick-scan was used or offered) and why, which modules were
touched vs left alone, anything removed, whether `data-model.md` and
`deployment.md` were written or skipped (and why, if skipped), and -- this
is often the most useful part -- any discrepancies you found between the
old docs and what the code actually does, including anything wired at
runtime (DI containers, plugin registries, reflection-based loading) that
Phase 3's scripts couldn't see and you had to track down by hand. If
`scripts/rollup.py` surfaced anything worth a human's attention beyond
what's already in `index.md` (a suspiciously central module, an orphan that
looks like real dead code, a cycle), call it out explicitly rather than
trusting the user to notice it in the file. Point them at `index.md` as the
entry point, mention `system-diagram.html` as the version to open directly
in a browser for the interactive view, and note that `_graph.json` was
(re)written if anyone downstream -- another tool, a CI check, a future
multi-repo run -- wants the same information in a structured form instead
of parsing Markdown.

## A note on languages the user writes in

Write the skill's own output (module docs, index, diagrams) in English by
default, since that's the most common convention for technical docs and this
skill is used across many projects -- but if the codebase's own comments/docs
are strongly and consistently in another language, or the user explicitly
asks for a different output language, follow that instead. Your
conversation with the user, separately, should always be in whatever
language they're using.

## Scripts reference

All scripts are stdlib-only Python (3.8+), no installs required:

- `scripts/inventory.py` -- Phase 1, structural overview; also does
  best-effort parsing of `docker-compose.yml`/`.yaml` when present (services,
  ports, `depends_on`), which feeds `deployment.md`, and best-effort parsing
  of `.github/workflows/*.yml`/`.circleci/config.yml` (`ci_config`), which
  is stronger ground truth for `index.md`'s "How to build/test" line than a
  guessed-at manifest script name
- `scripts/import_graph.py` -- Phase 3, same-language import/require/use
  hypothesis; pass `--modules modules.json` for accurate module-boundary
  grouping instead of a first-path-segment guess
- `scripts/external_calls.py` -- Phase 3, cross-service/network hypothesis:
  HTTP clients, gRPC stubs, queue publish/subscribe, cron, webhooks -- the
  interactions `import_graph.py` structurally can't see; also takes
  `--modules modules.json` for the same reason
- `scripts/state.py` -- Phase 0/6, manifest hash/diff/write for incremental
  updates (subcommands: `hash-modules`, `diff`, `write`, `git-commit`)
- `scripts/rollup.py` -- end of Phase 5 (once module docs exist), aggregates
  `modules/*.md` into `index.md`'s "Codebase health signals": most-connected
  modules, orphan candidates, dependency cycles, trace coverage
- `scripts/verify_diagram.py` -- end of Phase 5, mechanically cross-checks
  `system-diagram.md`'s edges against every module doc's "Depends on"/"Used
  by" sections instead of relying on an eyeballed cross-check
- `scripts/verify_entry_points.py` -- end of Phase 5, the same cross-check
  applied to `entry-points.md` against every module doc's "Public interface"
  section
- `scripts/verify_health_signals.py` -- end of Phase 5, cross-checks
  `index.md`'s "Codebase health signals" prose against a fresh
  `rollup.py` computation over `modules/*.md`, catching drift between what
  the section says and what the numbers actually are
- `scripts/graph_export.py` -- end of Phase 5, after all three verify scripts;
  re-parses `modules/*.md` and `entry-points.md` into `_graph.json`, a
  single structured artifact of the whole module/edge/entry-point/
  health-signal graph for another tool (or a future/multi-repo run of this
  skill) to consume without parsing Markdown -- pass `--write` to persist it

Run any of them with no arguments (or read the top-of-file docstring) to see
usage details.

## Reference files

- `references/module-detection.md` -- how to draw module boundaries for
  different project shapes; read during Phase 2
- `references/tracing-methodology.md` -- the verification discipline,
  scaling strategy, and how to handle runtime-resolved wiring; read before
  Phase 4
- `references/output-templates.md` -- exact structure for every output file
  type, including when the optional ones apply and how to fill in the HTML
  diagram; read during Phase 5
- `references/incremental-updates.md` -- the full decision tree and manifest
  schema for handling a pre-existing output folder, including migrating from
  an older `docs/system-trace` output and verifying edges into changed
  modules; read during Phase 0 (and Phase 6 when writing the manifest back)

## Assets

- `assets/diagram-template.html` -- the standalone interactive diagram that
  Phase 5 fills in and writes out as `system-diagram.html`. Don't improvise
  this file's HTML/CSS/JS from scratch each run -- fill in its data
  placeholder instead, the same way `output-templates.md` governs every
  other output file's structure. See `references/output-templates.md` for
  the exact data schema and how to do the substitution safely.
