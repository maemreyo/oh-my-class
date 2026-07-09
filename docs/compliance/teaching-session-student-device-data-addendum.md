# TeachingSession student-device data compliance addendum (TSP-01)

Status: addendum, scoped to TSP-01. Intended to merge into `PRIV-01`'s
eventual K-12 compliance mapping document rather than remain a permanently
separate doc (see `.scratch/scalability-elite-modules/issues/PRIV-01-k12-data-privacy-by-design.md`,
`Status: TODO`). Parent decision record: `docs/adr/046-teaching-session-platform-for-slide-deck-delivery.md`.

## Scope: what this addendum covers, and what it doesn't

This addendum covers data collected **directly from student devices during a
live TeachingSession** (join, in-class responses, reactions, pacing signals):
a different consent/data-flow story than `PRIV-01`'s teacher-submitted
`class_info.student_evidence` (diagnostic notes a teacher types about their
class before a run, persisted in `runs.class_info`). `PRIV-01`, when built,
is expected to own the umbrella K-12 mapping; this document should merge into
it rather than diverge permanently.

Out of scope for this addendum (covered elsewhere or by later TSP issues):
- Teacher-submitted `student_evidence` (`PRIV-01`).
- Join/role-token mechanics (`TSP-02`).
- Event transport and offline degradation (`TSP-03`).
- Response-collection UX and analytics dashboards (`TSP-05`).

## What is collected, and under which retention tier

A TeachingSession's retention tier (`services/gateway/teaching_session/models.py::RetentionTier`)
is the single control point for how identifying the data captured from
student devices during a session may be. It is chosen once, at session
creation, and cannot silently change (see "Tier immutability" below).

| Tier | What is stored | Identifiability |
|---|---|---|
| `none` | Nothing student-facing; the session runs ephemerally. | None |
| `aggregate` (**K-12 default**) | Class-level aggregates and lifecycle events (e.g. "62% answered B"). No raw per-student responses. | None |
| `pseudonymous` | Raw responses, keyed to a per-session pseudonym, never a real name/ID. | Indirect, session-scoped |
| `identifiable` | Raw responses tied to a real student identity. | Direct |

Data is additionally separated by **category**
(`SessionDataCategory`: events, aggregates, raw_responses, teacher_reflections,
ai_suggestions, exports), and `retention.allowed_data_categories_for_tier()`
is the single place that ties the two axes together — e.g. `raw_responses`
is never an allowed category under `none`/`aggregate`, which is what makes
"aggregate/minimal by default" a structural property rather than a policy
statement nobody enforces.

`teacher_reflections` and `ai_suggestions` are teacher-authored, not student
data, and are not gated by retention tier.

## Lawful basis and minimization

- **Default-minimized.** A session that does not explicitly select
  `pseudonymous`/`identifiable` at creation is `aggregate` — no raw,
  per-student, device-collected data is ever persisted by default. This
  matches FERPA's and PDPD's minimization expectations and COPPA's
  data-minimization principle for services directed at children.
- **Anonymous-first join is the default delivery shape** (ADR-046 decision
  3): a student's device only needs a room code/nickname, not an account.
  Identity-bearing retention tiers require the session to be bound to a
  real, org-scoped `class_id` (see "Class-scoping requirement" below) —
  never available for an anonymous open-join room, so there is no path from
  "walk-up classroom code" to "identifiable student record."
- **Lawful basis:** for `aggregate`/`none` tiers, processing is de-identified
  classroom analytics under the school's existing instructional-service
  agreement (FERPA "school official" exception; PDPD Art. 9's necessity for
  contract-performance basis). For `pseudonymous`/`identifiable` tiers, the
  school/teacher is the responsible party for obtaining any additional
  consent their policy requires (e.g. under COPPA, verifiable parental
  consent for services aimed at under-13s, typically satisfied at the school
  enrollment level under the FTC's school-consent provision) — this system
  does not itself collect parental consent; it *gates* identifiable capture
  behind a real class and an explicit, audited acknowledgment so that a
  school's existing consent basis has to actually be true before the data
  can flow.

## Class-scoping requirement (identity-bearing tiers)

`pseudonymous`/`identifiable` are only selectable when the session is bound
to a real `class_id` (`retention.validate_retention_selection`) — never for
an anonymous open-join room. This is deliberately a strict gate: it forces
identity-bearing capture into a context where a teacher already has an
ongoing pedagogical (and FERPA "legitimate educational interest") reason for
knowing which student is which, rather than allowing it in a walk-up/public
session.

**Known limitation:** `users` does not yet have an `organization_id` column
(tracked in `.scratch/multi-tenancy/organization-id-migration.md`), so
"org-scoped" is approximated today as "bound to a real, non-empty
`class_id`" — the same fail-closed approximation
`services/gateway/auth/ownership.py` uses elsewhere for cross-tenant checks.
Once that migration lands, this gate should be tightened to also verify the
class belongs to the requesting teacher's organization.

## Tier immutability and the identifiable-tier acknowledgment

- **Chosen once, locked at creation.** `TeachingSession.retention_tier` is
  guarded by a SQLAlchemy `@validates` hook
  (`_lock_retention_tier`) that allows exactly one assignment; any later
  attempt to change it to a different value raises. There is no code path in
  this slice (or planned in TSP-02..09) that escalates a session's tier
  mid-session — a session started as `aggregate` cannot quietly become
  `identifiable` partway through class.
- **Identifiable requires an explicit, audited acknowledgment.** Choosing
  `identifiable` requires `identifiable_acknowledged=True` at creation
  (`retention.validate_retention_selection`); `teaching_session.service.create_session`
  then persists a `SessionAuditEvent` row (`action="retention_tier_identifiable_acknowledged"`)
  in the same transaction as the session itself. This is TSP-01's own
  minimal seed of `PRIV-01`'s eventual data-access audit log (ADR-046
  amendment #25) — built now, shaped so `PRIV-01`'s broader audit trail can
  absorb it later rather than replace it. The audit event never stores
  student data, only who acknowledged what and when.

## Encryption, access, and audit

- Transport and at-rest encryption for TeachingSession data follow the same
  infrastructure as the rest of the gateway (Postgres + TLS); no new
  plaintext hop is introduced by this slice. A dedicated encryption/key-
  management review is `PRIV-01`'s scope, not re-litigated here.
- **Data-access audit:** `SessionAuditEvent` (`teaching_session_audit_events`
  table) is the persisted, session-scoped trail this slice ships. It is
  intentionally narrow (the identifiable-tier acknowledgment) rather than a
  general access log for every read — `PRIV-01`'s "who accessed which
  student-data-bearing run, when, via which action" data-access log is a
  strict superset of this table's shape and should extend it, not replace
  it.

## Retention windows and purge (future sweeper, predicate ships now)

`retention.is_prunable(session, now)` is a fail-closed, session-scoped purge
predicate: a session is only prunable once it has reached a terminal
lifecycle state (`ended`/`archived`/`expired`) **and** its tier's retention
window has elapsed since that terminal timestamp. More-identifying tiers get
*shorter* windows, matching this codebase's existing `student_evidence`
30-day rule (`services/gateway/retention.py`):

| Tier | Retention window after session ends |
|---|---|
| `identifiable` | 30 days |
| `pseudonymous` | 90 days |
| `aggregate` | 180 days |
| `none` | 0 days (nothing to retain) |

This predicate deliberately mirrors the shape of `OPS-07`'s not-yet-built
general-purpose `is_prunable(run, artifacts, now)` predicate
(`.scratch/scalability-elite-modules/issues/OPS-07-data-lifecycle-retention.md`,
`Status: TODO`) without depending on it, so that a future consolidation is a
refactor, not a rewrite. **This slice does not build the scheduled sweeper
that calls this predicate** — that is future work, tracked implicitly under
`OPS-07`'s eventual generalization or a TSP-specific follow-up.

## Future deletion/export requirements (not implemented in this slice)

Per TSP-01's acceptance criteria, this section documents intent without
building a privacy portal:

- **Right-to-delete:** a teacher/org-scoped request should be able to
  hard-delete a session's `pseudonymous`/`identifiable` raw responses (and,
  if requested, the whole session record) on demand, ahead of its retention
  window — extending the same "on-demand and complete" shape `PRIV-01`
  specifies for `student_evidence` (enumerate every store: Postgres rows,
  any object-storage exports, event log). Not built here.
- **Export:** teacher-initiated export of a session's aggregate/permitted
  data (per `SessionDataCategory` and the active retention tier) for
  reporting or evidence purposes. `TeachingSession`'s data categories already
  include `exports` as a distinct category so this has a place to attach to;
  the export mechanism itself is future work (see `TSP-05`/`TSP-08`).
- **Subject access:** a parent/guardian or eligible student's right to know
  what was collected about them (FERPA subject rights; PDPD Art. 9 data
  subject rights) should be answerable from the retention-tier + data-
  category model this slice defines, once an export/read path exists.

## Cross-border considerations

No cross-border transfer mechanism is introduced by this slice — session
data is stored in the same Postgres instance as the rest of the gateway's
data. If a future deployment serves Vietnam-resident students from
infrastructure outside Vietnam, Decree 13/PDPD's data-localization and
cross-border-transfer assessment requirements apply and should be evaluated
by `PRIV-01`, not assumed satisfied by this addendum.

## Regulatory mapping summary

| Requirement | FERPA | COPPA | Vietnam Decree 13 / PDPD | This slice's control |
|---|---|---|---|---|
| Minimization | Directory-info / legitimate-interest scoping | Data minimization for children's services | Art. 9 necessity principle | `aggregate` default tier; `allowed_data_categories_for_tier` |
| Consent / lawful basis | School-official exception | Verifiable parental consent (school-consent provision) | Consent or contract-performance basis | Identity-bearing tiers gated to a real `class_id`; school/teacher remains the consent-basis owner |
| No silent scope creep | — | — | — | Tier locked at creation (`@validates`) |
| Access logging | Recommended practice | — | Art. 9 accountability | `SessionAuditEvent` (identifiable-tier acknowledgment) |
| Retention limits | Recommended practice | COPPA retention-limitation rule | Art. 9 storage-limitation principle | `is_prunable` per-tier windows |
| Subject rights / deletion | Parent/eligible-student access & amendment rights | Parental review/deletion right | Art. 9 data subject rights | Documented above as future work; not yet implemented |

## References

- `docs/adr/046-teaching-session-platform-for-slide-deck-delivery.md` (decisions 1, 5, 18, 26).
- `services/gateway/teaching_session/` — `models.py`, `retention.py`, `status.py`, `service.py`.
- `.scratch/teaching-session-platform/issues/TSP-01-session-lifecycle-privacy-retention.md`.
- `.scratch/scalability-elite-modules/issues/PRIV-01-k12-data-privacy-by-design.md` (merge target).
- `.scratch/scalability-elite-modules/issues/OPS-07-data-lifecycle-retention.md` (shape mirrored, not depended on).
- `services/gateway/retention.py`, `services/gateway/purge.py` (existing retention/purge precedent for `student_evidence`).
