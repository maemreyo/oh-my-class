# Tracing methodology: verify, don't summarize docs

This is the part of the skill that matters most. It's easy to produce
something that *looks* like a system trace by paraphrasing the README and
skimming file names. That is not what this skill is for, and it's actively
worse than no documentation, because it looks authoritative while carrying
forward whatever's already stale or wrong.

## The rule

Existing README files, docstrings, code comments, and any prior
`docs/system-trace` output are **claims to verify, not facts to report.**
Before a sentence goes into a module doc, it should pass this test: *did I
just confirm this by reading the function body / route table / schema
myself, or am I repeating something a comment or README said?* If it's the
second one, go open the actual code before writing the sentence.

This isn't paranoia for its own sake -- comments and READMEs drift from
reality constantly (the feature described was changed, the TODO was finished
two years ago and never removed, the docstring was copy-pasted from a
similar-but-different function). Code doesn't drift from itself. It's always
telling the truth about what it currently does, even when that truth is
messy.

**When docs and code disagree, the code wins -- and say so.** Add a line to
that module's "Notes / discrepancies" section describing what the old docs
claimed versus what the code actually does. This is often the single most
useful thing the output tells the user: it's the reason "trace the real
thing" beats "summarize what's already written."

## Reading order per module

Working in this order avoids both missing things and wasting effort:

1. **Public surface first.** Exported functions/classes, route or controller
   definitions, registered CLI commands, event/message handler
   registrations. This is what the module promises to the rest of the
   system -- everything else is implementation detail in service of this
   surface.
2. **Trace inward from each public entry point.** Read far enough into the
   function body to know what it actually does: what it calls (helpers,
   other modules, external services, the database, the filesystem, the
   network), what it returns, what side effects and error paths it has.
   Don't stop at the signature.
3. **Check hypothesized edges against reality.** `scripts/import_graph.py`
   told you module A imports module B -- now open the call site in A and
   read what it's actually used for. `import db_client` and then calling
   `db_client.execute()` on every request is a very different relationship
   from importing a single shared constant. Describe the real relationship
   in the module doc ("calls X's `save()` on every write to persist orders"),
   not just the fact that an edge exists.
4. **Note configuration and environment dependence.** Env vars read, config
   files loaded, feature flags checked -- these often explain *why* a module
   behaves differently across environments, which is exactly the kind of
   thing that's easy to get wrong from docs alone.
5. **Tests are excellent evidence, not a replacement for reading the code.**
   A module's test file is often the fastest way to confirm a real behavior
   or an edge case (what happens on empty input, what error is raised and
   when). Use it to corroborate what you read in the implementation, and
   flag it if a test's assumptions don't match what the implementation
   actually does.

## Scaling to large codebases

Reading every line of a 500-file module by hand doesn't scale, and this
skill would rather you trace 20 modules honestly at appropriate depth than
claim false completeness over all of them. Some ways to scale:

- **Prioritize by traffic, not by alphabetical order.** Use
  `scripts/import_graph.py --group-by-top-level`'s edge counts and
  `scripts/inventory.py`'s `largest_files_by_line_count` to find the files
  that are heavily referenced or unusually large -- read those in full first.
  Rarely-referenced leaf files can be skimmed (signature + docstring + a
  representative chunk of the body) unless skimming reveals they're more
  central than the heuristic suggested.
- **Use grep to jump straight to definitions and call sites** (e.g.
  `grep -rn "def handle_payment" .` or `grep -rn "PaymentGateway(" .`) rather
  than reading files top to bottom in sequence. `rg` (ripgrep) if it's
  installed, plain `grep -rn` otherwise -- both work fine for this.
- **State your confidence and coverage honestly.** It's fine for a module doc
  to say "this module has 40 files; the following N were read in depth
  because they were the most-referenced or largest; the remainder follow the
  same repository/handler pattern based on a sample of 5." That's an honest,
  useful claim. Don't imply exhaustive coverage you didn't actually do.
- **A module that's too big to trace at once can be split** into a couple of
  sub-module docs (see module-detection.md's sizing guidance) rather than
  either skipping it or writing something too shallow to be useful.

## What "how they interact" means concretely

The point of this skill isn't just a static dependency arrow between two
module names -- a real engineer wants to know the *nature* of the
interaction. For every significant edge between modules, try to capture:

- **Direction and trigger**: who calls whom, and when (on every request?
  once at startup? on a schedule? in response to an event?).
- **Synchronous vs asynchronous**: a direct function call blocks; a published
  event or queued job doesn't -- this materially changes how a system
  behaves under failure.
- **What crosses the boundary**: which data/parameters go across, and what
  comes back (or doesn't, for fire-and-forget interactions).
- **Failure behavior**: what happens if the callee errors or is unavailable
  -- is it caught, retried, propagated, ignored?

This level of detail is what makes the sequence-diagram flows in
`system-diagram.md` (see `references/output-templates.md`) worth having,
instead of a diagram that just repeats the import graph with boxes and
arrows.
