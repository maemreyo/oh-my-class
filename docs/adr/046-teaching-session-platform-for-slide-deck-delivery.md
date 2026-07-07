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
