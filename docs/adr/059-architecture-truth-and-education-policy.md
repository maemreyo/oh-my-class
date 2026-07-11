# ADR-059: Architecture Truth and Education Policy Authority

## Status

**Accepted** (2026-07-11)

## Context

Generated architecture documentation and runtime contracts are release claims. A
stale trace or a free-text grade label can make a green build describe a system
that does not actually run.

## Decision

1. `make check-architecture` is the blocking local and CI command for the
   runtime architecture manifest, anatomy module hashes, and anatomy source
   references.
2. `docs/anatomy/_manifest.json` is refreshed whenever a traced module changes.
   The architecture gate reports the stale module and the `/anatomy` refresh
   action.
3. `RunContract` is the runtime policy boundary. It pins
   `education_policy.v1`, normalizes a teacher grade into one canonical K-12
   band (`k_2`, `grades_3_5`, `grades_6_8`, or `grades_9_12`), and rejects an
   ambiguous or out-of-range grade through the clarification gate.
4. Target language and instruction language are separate contract fields.
5. Legacy strategy-knowledge and flashcard grade bands are adapters from the
   canonical policy. Missing K-2 strategy knowledge yields no eligible binding;
   it never defaults to another grade band.

## Consequences

- Architecture and policy drift fail before release rather than relying on
  manual review.
- Existing human labels such as `Grade 5` remain accepted at the gateway
  boundary; persisted run contracts use the canonical value.
- New policy consumers import the canonical vocabulary instead of introducing
  free-text grade-band branching.

## References

- Epic #460, issues #461 and #462
- ADR-053 Content Orchestrator, Specialists, and Capability Packs
- ADR-058 Full-Breadth V1 Release, Evidence, and Big-Bang Cutover
