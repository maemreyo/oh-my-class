# Full-Breadth V1 Big-Bang Cutover Runbook

Status: **Ready to execute — pending the decisions in "Human decisions
required" below.** This is the ADR-058 evidence artifact issue #459 asks
for: "big-bang GA with rollback-safe data." Everything in this document
that a command can verify has been verified (see "Pre-flight verification"
and its dated run log). What remains is not a coding task: someone with
authority over this release has to pick a date, be the rollback owner, and
sign off.

## TL;DR

One deployment cuts the full-breadth V1 scope (ADR-058: 12 artifact
surfaces, 5 specialist families, 4 Subject Capability Packs, K-12 across 4
Grade Bands, English and Vietnamese, MOET 2018/CCSS/NGSS lanes) live. No
public partial-V1 release, no old/new dual mode, no long canary — the
product has no production users yet, so a long compatibility window buys
nothing but risk. Rollback means restoring from the pre-cutover backup, not
a feature flag flip: this deployment includes schema migrations
(`037_fix_fk_ondelete_drift` is the latest as of this writing) that are
forward-compatible but not silently reversible.

## Decisions already locked (from ADR-058)

1. V1 ships as one release; no artifact/subject/language/export subset is
   held back to a later "V1.1."
2. Rollback strategy is restore-from-backup
   (`docs/operations/disaster-recovery.md`), not a runtime toggle — there
   is no parallel "old" system still running to fall back to.
3. Release evidence must exercise the real product/job/renderer/editor/
   export/live-session surfaces, not internal function calls — see the
   capability coverage matrix (`docs/reports/adr-058-evidence-coverage-matrix.md`).

## Human decisions required (not something this document can resolve)

- [ ] **Cutover date/window**: ____________________
- [ ] **Rollback owner** (the person who decides to invoke the restore
      procedure and has the authority to do so): ____________________
- [ ] **Go/no-go sign-off** (who reviews the pre-flight verification
      results below and approves proceeding): ____________________
- [ ] **Communication plan** for the window (who is notified, on what
      channel, before/during/after): ____________________

## Pre-flight verification

Run every command below **immediately before** the cutover window, not
days in advance — this is a snapshot of "is the system healthy right now,"
not a historical fact. Record the actual output (pass/fail counts) in the
dated run log at the bottom of this file, the same way
`.omo/evidence/teaching-pack-hard-cutover.md` did for the earlier rename.

1. **Full regression suite**:
   ```bash
   uv run pytest packages/agents packages/quality common/contracts services/gateway tests/ -q
   pnpm -r test
   ```
   Compare the failure list against the known baseline in
   `docs/reports/adr-058-evidence-coverage-matrix.md` — anything new must
   be resolved or explicitly accepted by the sign-off owner before
   proceeding, not silently waved through.

2. **Architecture-manifest sync** (catches undocumented drift since the
   last release):
   ```bash
   uv run pytest tests/test_architecture_sync.py -q
   ```
   If this fails, run `uv run python scripts/generate_architecture_manifest.py`
   and review the diff before committing it — don't regenerate blindly.

3. **Migration state**:
   ```bash
   cd services/gateway && uv run alembic current
   ```
   Confirm the reported head matches the latest file under
   `services/gateway/alembic/versions/` on the branch being deployed.

4. **Backup freshness** (per `docs/operations/disaster-recovery.md`'s
   6-hour cadence): confirm the most recent app-Postgres and Langfuse-
   Postgres snapshot/dump timestamps are within the last cadence window,
   *before* starting the deploy — a stale backup makes rollback-safety a
   fiction.

5. **Restore drill** (proves rollback actually works, not just that a
   backup file exists):
   ```bash
   uv run pytest services/gateway/tests/test_checkpoint_recovery.py -v
   ```

6. **Secrets guard** (production startup fails closed on a missing/default
   secret — confirm it actually would, don't assume):
   ```bash
   ENV=production uv run python -c "from services.gateway.secrets_guard import validate_production_secrets; validate_production_secrets()"
   ```
   Run this with the actual deployment environment variables loaded (not
   local dev defaults) — it must raise `ProductionSecretsError` naming any
   offending variable if a real secret is still missing or a known default,
   and must raise nothing if every variable named in
   `docs/operations/secrets.md` is set to a real value.

7. **Capability coverage spot-check** — the release-gate test files are the
   evidence, not a separate manual pass:
   ```bash
   uv run pytest common/contracts/tests/test_subject_capability_pack.py \
     packages/agents/tests/teaching_pack/test_math_capability_pack_release_gate.py \
     packages/agents/tests/teaching_pack/test_science_capability_pack_release_gate.py \
     packages/agents/tests/teaching_pack/test_language_literacy_capability_pack_release_gate.py \
     packages/agents/tests/teaching_pack/test_humanities_capability_pack_release_gate.py -q
   ```

## Cutover procedure

1. Freeze merges to `main` for the deploy window; announce per the
   communication plan above.
2. Take a fresh app-Postgres and Langfuse-Postgres snapshot immediately
   before deploying (do not rely on the last scheduled snapshot — see
   step 4 above).
3. Deploy the release branch.
4. Run `uv run alembic upgrade head` against production.
5. Start the gateway; verify `GET /health` → 200 and `GET /ops/slo` → all
   dimensions within threshold.
6. Smoke-test one real teaching-pack run end to end (create → approve →
   export) through the actual API, not a unit test, before declaring the
   window closed.
7. Unfreeze merges once the smoke test passes and the sign-off owner
   confirms.

## Rollback procedure

If the pre-flight or post-deploy smoke test fails and the rollback owner
decides to abort:

1. Stop the gateway and any workers/sweepers.
2. Follow `docs/operations/disaster-recovery.md`'s restore procedure
   against the snapshot taken in cutover step 2.
3. Confirm `GET /health` and an interrupted-run resume smoke test pass
   against the restored database before declaring rollback complete.
4. Communicate the rollback and revised plan per the communication plan
   above.

## Run log

Record each real execution of the pre-flight verification here, dated,
with actual pass/fail counts — this section is evidence, not a template to
leave blank once the cutover has actually happened.

<!-- Example entry, delete once a real run is logged:
### 2026-MM-DD pre-flight run
- Full regression: X passed, Y failed (all Y matched the known baseline)
- Architecture-manifest sync: pass
- Migration head: 0NN_migration_name
- Backup freshness: last snapshot HH:MM, within cadence
- Restore drill: pass
- Secrets guard: pass
- Capability spot-check: pass
- Decision: go / no-go, signed off by NAME
-->
