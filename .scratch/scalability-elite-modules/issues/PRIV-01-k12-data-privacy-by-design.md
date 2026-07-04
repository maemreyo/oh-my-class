# [PRIV-01] K-12 data privacy (privacy-by-design)

Status: TODO
Labels: privacy, security
ADR: 034
Depends on: OPS-07, OPS-09

## Context

The system ingests **student data** on the input side. `diagnose_then_generate` mode accepts
`class_info.student_evidence` (`common/contracts/run_contract.py:55`,
`student_evidence: JsonObject | None`), which flows through the pipeline
(`packages/agents/teaching_pack/nodes.py`, `services/gateway/run_contract_setup.py`,
`services/gateway/research_engine.py`, `services/gateway/research_safety.py`) and is persisted in
`runs.class_info` (JSON column, `services/gateway/models.py:91`).

Existing controls are **output-side and partial**:
- The compliance gate blocks PII in **generated output** (`packages/quality/compliance_policy.py`).
- Retention has a `student_evidence` class (30 days, `services/gateway/retention.py:19,40`) and
  purge redacts a fixed PII key set (`services/gateway/purge.py:27` —
  `name, student_name, email, score, class_id, student_id, ...`; `purge_student_evidence`
  redacts evidence past its window, line 79).
- `TeacherAuditLogMiddleware` logs only `teacher_decision`
  (`packages/agents/middleware/safety/teacher_audit_log.py:30-35`) — not a data-access trail.

The **gap** is privacy-by-design over the **input + storage** of student data: minimization,
pseudonymization, guaranteeing student PII is never logged/traced/over-persisted, encryption at
rest and in transit, a right-to-delete honoring teacher/org scope, a real data-access audit, and
a documented regulatory mapping. Market is US K-12 (**FERPA/COPPA**) and Vietnam
(**Decree 13 / PDPD**).

## Scope

- [ ] **Minimize + pseudonymize** `student_evidence` at ingestion
      (`run_contract_setup.py` / the nodes that consume it): strip/reject direct identifiers not
      needed for diagnosis; replace identifiers with per-run pseudonyms so the pipeline reasons
      over evidence without carrying raw student PII. Store only the minimized/pseudonymized form
      in `runs.class_info`; keep any mapping (if required) separate and short-lived.
- [ ] **Never logged / traced / over-persisted**: audit every path that could emit
      `student_evidence` — application logs, Langfuse traces (ADR-034 observability), error
      messages, event payloads — and redact/exclude it. Add a guard test that fails if
      `student_evidence` (or its identifier fields) appears in a log record, trace payload, or
      `run_events` row. Ties to OPS-12's "no secrets in logs" logging hygiene.
- [ ] **Encryption at rest**: student data at rest in Postgres and in object storage (OPS-05) is
      encrypted (DB-level/disk encryption + object-storage SSE at minimum; document whether
      column/field-level encryption is warranted for `student_evidence`). Document the key
      management story.
- [ ] **Encryption in transit**: TLS enforced for client↔gateway and gateway↔{DB, object
      storage, providers}; document/verify no plaintext hop carries student data.
- [ ] **Retention + right-to-delete** (extends OPS-07): a teacher/org-scoped delete that
      hard-removes a student's evidence on request across `runs.class_info`, object storage,
      checkpoints, and `run_events`, honoring OPS-09 org scoping. Build on existing
      `purge_student_evidence` / retention windows but make it *on-demand and complete*, not only
      time-based. Verify the redaction key set (`purge.py:27`) is complete vs the identifiers the
      pipeline actually ingests.
- [ ] **Data-access audit trail**: extend `TeacherAuditLogMiddleware` (or add a sibling) into a
      real **data-access log** — who (teacher/admin/system) accessed which student-data-bearing
      run, when, and via which action — persisted (not just `logging.info`) and org-scoped, so
      access to student data is auditable for compliance. Do not log the data itself, only the
      access event.
- [ ] **Compliance mapping document**: a doc mapping each control above to **FERPA**, **COPPA**,
      and **Vietnam Decree 13 (PDPD)** requirements (lawful basis, minimization, retention,
      subject rights/right-to-delete, access logging, cross-border considerations). Place under
      `docs/` and reference from the ADR.

## Acceptance

- Ingested `student_evidence` is minimized + pseudonymized before persistence; raw direct
  identifiers are not stored in `runs.class_info` — proven by a test on the ingestion path.
- A guard test proves `student_evidence` / student identifiers never appear in logs, Langfuse
  traces, error messages, or `run_events`.
- Student data at rest (Postgres + object storage) is encrypted, and all transport hops carrying
  it use TLS — documented and verified.
- A right-to-delete request removes a student's evidence across DB, object storage, checkpoints,
  and events within scope, honoring OPS-09 org boundaries — proven by a live-path test.
- The data-access trail persists an auditable access record (actor, run, action, time) without
  storing the underlying student data.
- The FERPA/COPPA/Decree-13 mapping doc exists and covers minimization, retention, subject
  rights, access logging, and cross-border handling.

## References

- `common/contracts/run_contract.py:55` — `student_evidence: JsonObject | None`.
- `packages/agents/teaching_pack/nodes.py`, `services/gateway/run_contract_setup.py`,
  `services/gateway/research_engine.py`, `services/gateway/research_safety.py` — evidence flow.
- `services/gateway/models.py:91` — `runs.class_info` JSON (where evidence is persisted).
- `packages/quality/compliance_policy.py` — output-side PII gate (existing).
- `services/gateway/retention.py:19,40,69-71` — `student_evidence` retention class.
- `services/gateway/purge.py:27,79` — PII redaction key set + `purge_student_evidence`.
- `packages/agents/middleware/safety/teacher_audit_log.py:12-35` — `teacher_decision`-only log.
- OPS-05 (object storage — encryption at rest target), OPS-07 (retention/lifecycle),
  OPS-09 (org scoping for right-to-delete), OPS-12 (logging hygiene).
- ADR-034 decision 10.

## Implementation notes

- Privacy-by-design = default-minimized: the ingestion boundary should be the *only* place raw
  identifiers exist, and only long enough to pseudonymize. Everything downstream sees pseudonyms.
- Right-to-delete must be **complete**: enumerate every store that can hold student data
  (Postgres `class_info`, object storage, LangGraph checkpoints, `run_events`) so a delete leaves
  no residue. Reuse purge machinery but drive it on-demand and scope it by teacher/org (OPS-09).
- The redaction key set in `purge.py:27` is a denylist — cross-check it against the actual
  identifier fields the pipeline ingests so nothing slips through; prefer an allowlist of
  retained fields where feasible.
- Keep the data-access trail *about* access, never *containing* the data — otherwise the audit log
  becomes a new PII store.
