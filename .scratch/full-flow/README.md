# Full Flow Issues

Purpose: finish the complete oh-my-class run lifecycle so the web dashboard can drive a real core engine end-to-end.

## Review status - 2026-06-25

A strict review found that the current implementation is a useful scaffold, but the 10 slices are **not complete**. Treat every issue below as `ready-for-agent` remediation work, not as done work.

Cross-cutting blockers that affect multiple issues:

- Run-scoped endpoints must enforce teacher ownership/admin visibility. `GET /run/{id}`, SSE, artifacts, exports, approve, and reject currently trust only the run id.
- Artifact validation must use the canonical `ArtifactContent` contract (`artifact_type`, `title`, `sections`, `metadata`, `accessibility`) instead of the weaker `{type, content}` shape.
- SSE backend and frontend must agree on event names. Backend emits named events such as `gate_waiting`; the frontend currently waits for `interrupt` through `onmessage`.
- Quality and export checks must fail closed. Hardcoded judge passes, placeholder export tests, and renderer-only escaping are not enough.
- Tests must include real graph interrupt/resume and full-flow mocked-LLM integration. Green unit tests and preseeded mock state are not sufficient.

## Dependency order

1. Run lifecycle tracer
2. Run read model and ownership guard
3. Real progress stream
4. Blueprint gate from real planner output
5. Blueprint approval/rejection resume
6. Draft artifact generation
7. Artifact retrieval and web preview
8. Quality gates and healing loop
9. Content approval/regeneration resume
10. Export and finalize downloadable teaching pack

Agents should work in dependency order unless an issue states `None - can start immediately`. Each issue includes the current partial implementation, remaining blockers, and tests that must be upgraded from mock-only coverage to behavior coverage.
