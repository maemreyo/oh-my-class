# ADR-046: TeachingSession Platform for Slide Deck Delivery

## Status

**Proposed** (2026-07-07) — Defines the future `TeachingSession` platform direction for delivering slide decks in live, review, homework, flipped, and catch-up modes. This ADR does not expand the current slide-deck production-hardening scope; it records the platform decisions needed when live teaching/session work begins.

## Context

ADR-045 establishes slide decks as a static/exportable artifact now and a teaching-session-ready foundation later. The next platform layer is the runtime that turns a deck snapshot into a classroom experience: teacher control, projector/display surface, student companion views, response collection, pacing, analytics, branch actions, recovery, retention, and post-lesson recommendations.

K-12 classroom software must balance usefulness with privacy, reliability, low friction, and teacher control. Live teaching also has stricter UX constraints than normal dashboards: the teacher has little time, network may be unreliable, and no raw AI output should reach students without teacher approval.

## Decision

1. **TeachingSession is a hybrid privacy-first persisted event.** A session has lifecycle state and an event log, but persistence levels are explicit. Default retention is aggregate/minimal, not raw per-student response storage.
2. **Sessions bind to immutable deck snapshots.** A session references `deck_id`, `snapshot_id`, and stable slide/block/interaction IDs. Session state is an overlay and does not mutate generated deck content.
3. **Student join is anonymous-first hybrid.** The default classroom join path is room code plus optional nickname/seat/group. Authenticated roster mode is optional for schools that need identifiable tracking.
4. **Navigation is delivery-mode policy.** Live mode is teacher-controlled by default with optional backtracking. Review, homework, flipped, and catch-up modes may be student-paced. Display preferences are separate from delivery mode.
5. **Student response storage is tiered.** Supported retention levels should include none, aggregate, pseudonymous, and identifiable. Default is aggregate/concept-level for K-12. Raw/free-text/identifiable data requires explicit policy.
6. **Teacher live UI is a teaching cockpit.** Live UI should prioritize current activity, next action, pacing, class-level signal, and one-tap branch options. It should not be a dense analytics dashboard during teaching.
7. **Branching is precomputed-first.** Reteach, hint, simpler example, and challenge branches should be precomputed and quality-gated where possible. On-the-fly AI generation is teacher-facing, async, auditable, and teacher-approved before students see it.
8. **Platform is offline-first presentation and online-enhanced session.** Standalone presentation/print must work offline. Live sync, student companion, and response collection are progressive online enhancements with clear degraded states.
9. **Sessions use a multi-device role model.** Roles include controller, display, student, and observer. Co-teacher control is future work requiring explicit handoff/lock rules.
10. **Student responses are structured-first and free-text gated.** Quick checks should default to structured response types. Free text is allowed only in explicit modes such as short answer or exit ticket and must pass PII/safety filtering before storage or analytics.
11. **Analytics are policy-tiered and class-concept default.** Live cockpit shows class-level actionable signals. Group or individual drill-down requires identity/retention policy. Ranking students is not a default behavior.
12. **Session state uses significant event log plus derived read models.** Important events such as session start, slide change, interaction open, aggregate update, branch selection, annotation, and session end are append-only. UI reads derived state for speed.
13. **Sync is SSE-first hybrid.** Server-sent events broadcast current session state. Student responses/actions use REST POST with idempotency keys. Polling is a fallback; WebSocket is reserved for future high-frequency collaboration.
14. **Recovery uses reconnect plus event-log resume.** Clients reconnect using session ID and role token, fetch current derived state, and resume events from last event ID where possible. Offline standalone presentation can continue without live sync.
15. **Permissions use teacher auth plus scoped session role tokens.** Teacher ownership/auth mints role-scoped tokens for controller, display, student, and observer. Tokens expire and cannot unlock teacher-only data outside permitted roles.
16. **Observer is supported before co-teacher.** Read-only observers can view authorized session state. Multiple controllers/co-teachers require future conflict-resolution rules.
17. **Live AI is teacher-only by default.** AI suggestions may help teachers choose hints/reteach/branches, but raw AI output must not stream directly to students. Teacher approval and safety/quality gates are required before display.
18. **Retention is tiered by data type and visible to teachers/admins.** Raw responses have the shortest or no retention by default. Aggregates/reflections may last longer. Future deletion/export support should follow policy.
19. **Analytics feedback loop is teacher-confirmed.** Post-lesson summaries may recommend reteach decks, worksheets, homework, or next-lesson adjustments, but the teacher approves before generation or assignment.
20. **Real evidence is required before platform claims.** Future session work must be validated with real deck snapshots, real gateway/model flow where generation is involved, real session-role behavior, and evidence bundles that report privacy/retention/sync modes.

### Amendment (2026-07-07) — implementation-level decisions from design interview

The decisions above set the platform's shape; the following fill in concrete mechanics that were left open, resolved through a 50-question design interview. None of these change decisions 1-20; they specify *how*.

21. **The STUDENT role is a JWT claim, never a persistent identity.** No `STUDENT` value is added to the `Role` enum and no row is created in `users` for a student. Session role tokens (decision 15) are minted through the existing `jwt_handler.py` signing path with a `role=STUDENT` claim scoped to `session_id`/`room_code` and a short expiry — reusing existing crypto/verification code without ever creating a durable student account, keeping decision 3 (anonymous-first) true by construction.
22. **Room join is QR-primary with a numeric fallback, both rate-limited.** The default join affordance is a projected QR code (zero typing, zero typos); a 6-digit numeric code (Kahoot/Quizizz-familiar) is the fallback for devices without a camera. Both paths reuse the webhook rate-limiter pattern (`services/gateway/routers/webhooks.py`'s sliding-window model), keyed by IP + room code, and the code's validity is bounded to the session's lifetime — the attack window is bounded by short TTL and rate-limiting together, not by keyspace size alone.
23. **Live broadcast sync uses Redis Pub/Sub**, not an extension of the single-listener in-memory event bus. Redis already runs in this stack (LiteLLM cache, `redis_breaker_store.py`); a session-id-keyed channel lets any gateway instance publish and any instance's SSE handler relay to its locally connected students, which the in-memory bus cannot do across multiple instances. Any new Redis-backed path here must carry its own live-path-proof test per ADR-032 — `redis_breaker_store.py` existing with zero callers is the cautionary example not to repeat.
24. **Session state is Redis-hot with a Postgres write-behind event log and replay-based recovery.** Redis holds live state (current slide, roster, tallies) for speed; Postgres durably logs events asynchronously. On Redis restart/failover, a session reconstructs current state by replaying the last N events from Postgres — this is what makes decision 14's "event-log resume" concrete, not just aspirational.
25. **TSP's own retention/purge mechanism ships now, shaped like `OPS-07`'s (not yet built) pattern, without waiting for it.** `OPS-07` (general run/artifact pruning) and `PRIV-01` (K-12 privacy-by-design compliance mapping) are both `Status: TODO` in a different, unscheduled track. TSP implements a session-scoped `is_prunable()`-style predicate (fail-closed default-deny, scheduled-sweeper cadence) now, deliberately mirroring `OPS-07`'s shape so a future consolidation is a refactor, not a rewrite. TSP separately authors its own FERPA/COPPA/Vietnam Decree-13 (PDPD) compliance addendum now — scoped to session data collected directly from student devices (a different consent/data-flow story than `PRIV-01`'s teacher-submitted `student_evidence`) — structured to merge into `PRIV-01`'s eventual compliance doc rather than diverging permanently.
26. **Retention-tier escalation (decision 5/18) is an explicit, logged, per-session teacher choice, gated to real classes.** The tier (none/aggregate/pseudonymous/identifiable) is picked once at session creation, cannot silently escalate mid-session, and choosing `identifiable` requires an explicit on-screen acknowledgment that is written to the data-access audit trail. `pseudonymous`/`identifiable` tiers are only available when the session is bound to a real, org-scoped `class_id` (reusing existing ownership/organization infrastructure) — never for an anonymous, open-join room.
27. **v1 ships the `live` delivery mode only; the `delivery_mode` field is declared in the schema for all five modes now.** `homework`/`review`/`flipped`/`catch-up` are async-assignment shaped (no SSE, no room code) and are explicitly out of v1 scope — but reserving the field now avoids a breaking schema change when they're built.
28. **Branching (decision 7) is precomputed-first with a teacher-gated on-demand escape hatch.** Precomputed remedial/extension slides (generated during deck authoring, already registry/density-validated) are the zero-latency default the cockpit surfaces. A teacher-triggered "generate a new suggestion" action reuses ADR-047's AI-rewrite pipeline (same confirmation-before-display gate) for the cases a precomputed branch doesn't fit — real-time LLM calls mid-class, unmediated by teacher approval, remain out of scope.
29. **Two related session-adjacent features are explicitly scoped, not open-ended:** (a) live annotation/whiteboard overlay in the cockpit is **ephemeral only** in v1 — no save/persist path; (b) non-competitive gamification (private per-student points/streaks, or whole-class collective points — never a public individual leaderboard) is opt-in per teacher preference, consistent with the non-competitive framing already established in the effectiveness-loop dashboard. See TSP-04 and TSP-05 for the amended acceptance criteria.

## Consequences

- The platform can evolve from standalone decks into live classroom delivery without sacrificing privacy or offline reliability.
- Privacy and retention are first-class design inputs, not afterthoughts.
- The teacher remains the gate for live AI and post-lesson content generation.
- Event logs and role tokens add implementation complexity but make recovery, audit, evidence, and analytics reliable.
- The current slide-deck hardening release is not blocked by session runtime; the session platform is a separate future track.

## Alternatives Considered

| Option | Pros | Cons |
|---|---|---|
| Ephemeral live room only | Lowest storage/privacy burden | Weak post-lesson reflection, recovery, analytics, and evidence |
| Persist all raw responses by default | Rich analytics | Poor K-12 privacy default; high compliance risk |
| Account login required for every student | Strong identity | High classroom friction; excludes low-setup usage |
| WebSocket-first realtime | Full duplex | More infra complexity before needed; SSE/REST fit initial classroom flow |
| Direct AI-to-student tutoring | Powerful | High safety, privacy, and quality risk; separate future product |
| Static deck only | Simple | Prevents slide deck from becoming a classroom teaching core |

## References

- ADR-019 Learning Outcome Effectiveness Loop
- ADR-028 Full REST Operability for Teaching-Pack Runs
- ADR-034 Scale and Operations Platform
- ADR-045 Slide Deck as Teaching Session Foundation
- `packages/agents/teaching_pack/graph.py`
- `services/gateway/routers/teaching_packs.py`
- `services/gateway/events.py`
- `services/gateway/recovery_sweeper.py`
- ADR-047 Slide Deck Editor and AI-Assisted Revision
- `services/gateway/auth/jwt_handler.py`, `services/gateway/auth/ownership.py`
- `services/gateway/routers/webhooks.py` (rate-limiter pattern reused for room-code join)
- `packages/agents/healing/redis_breaker_store.py` (cautionary precedent: Redis-backed code with zero callers)
- `.scratch/scalability-elite-modules/issues/OPS-07-data-lifecycle-retention.md`, `PRIV-01-k12-data-privacy-by-design.md` (shape mirrored, not blocked on)
- `.scratch/teaching-session-platform/issues/` (TSP-01..11)
