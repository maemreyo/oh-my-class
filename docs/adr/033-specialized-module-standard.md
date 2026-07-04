# ADR-033: Specialized Module Standard ("đẳng cấp" modules)

## Status

**Proposed** (2026-07-03) — To grow world-class specialized modules without repeating the
"each module reinvents retry/enforcement" smell, every specialized capability (LLM sub-agent,
renderer plugin, exporter, quality layer, middleware, gate) conforms to one cross-cutting
standard. Detail lives in the issue set (MOD-*); new-module scope in RFCs.

## Decision

1. **Cross-cutting Module Standard (not a God-base-class).** Families keep their own registries
   (renderer plugin registry ADR-025, `AGENT_CAPABILITIES`, `BaseMiddleware`,
   `ports.py::QualityGate`, exporter modules), but every module must satisfy a 6-point checklist,
   enforced by ADR-032 gates:
   (1) typed I/O contract (Pydantic↔Zod parity); (2) capability declaration in its family
   registry (no stub/unimplemented bound); (3) guard + live-path behavioral tests; (4)
   `ObservabilityEvent` on entry/exit/failure; (5) fail-closed default; (6) manifest/version entry.
2. **Scaffolder.** `make new-module KIND=… NAME=…` emits a compliant skeleton (contract +
   registry entry + test stubs + observability) so modules start compliant by construction.
3. **Explicit registration + unified manifest.** Keep explicit registration (no auto-scan magic).
   Extend `scripts/verify_registry_drift.py` + `architecture.manifest.json` into one index across
   all families with a drift CI check (registered ⇒ has contract + tests + reachable; nothing
   implemented-but-unregistered).
4. **Contract versioning.** Additive = non-breaking; breaking = bump `schema_version` + boundary
   adapter + golden-fixture regression; stored snapshots re-render only via their pinned
   `renderer_version`.
5. **Fault isolation.** In-process, but per-module timeout + fail-closed error boundary + circuit
   breaker (LLM); Node exporter subprocesses already isolated. No microservice-per-module at
   mid-scale.
6. **New modules on this standard + AgentRuntime:** Researcher-upgrade (RFC-30), Accessibility
   (RFC-32), Localization (RFC-31), **Differentiation** (grade-tier + ELL first; IEP deferred),
   **Standards-alignment** (pluggable frameworks, seed CCSS + Vietnam MOET).

## Consequences

- New elite modules are cheap, uniform, observable, safe-by-default, and testable-by-construction.
- One manifest = one place to audit the whole capability surface.
- Reuses existing good patterns rather than a rewrite.

## Alternatives Considered

| Option | Pros | Cons |
|---|---|---|
| Standard + scaffolder, per-family registries (chosen) | Uniform discipline, respects family differences | A checklist to maintain |
| Single unified module base/runtime | One abstraction | Families are genuinely different; forces awkward fit |
| Auto-discovery (decorators/entry-points) | Less boilerplate | Hides what's active — violates "no magic" principle |
