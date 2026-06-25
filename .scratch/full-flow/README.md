# Full Flow Issues

Purpose: finish the complete oh-my-class run lifecycle so the web dashboard can drive a real core engine end-to-end.

Dependency order:

1. Run lifecycle tracer
2. Run read model
3. Real progress stream
4. Blueprint gate from real planner output
5. Blueprint approval/rejection resume
6. Draft artifact generation
7. Artifact retrieval and web preview
8. Quality gates and healing loop
9. Content approval/regeneration resume
10. Export and finalize downloadable teaching pack

Each issue is `ready-for-agent` and includes its required test suite. Agents should work in dependency order unless an issue states `None - can start immediately`.
