# Runbook: Content Recall (Post-Delivery)

## Symptom

- A delivered teaching pack is found to contain incorrect, harmful, or legally
  problematic content after it has been exported and shared with students.
- A teacher or admin reports that an approved artifact snapshot must be retracted.
- Quality review identifies a systematic error in a batch of generated content
  (e.g. a model regression affecting a specific content type or topic).

## Alert

No automated SLO alert fires for content recall — this is a manually triggered process
initiated by a teacher, admin, or trust-and-safety review.

Internal escalation path: trust-and-safety team → admin → on-call engineer.

## Diagnosis

1. Identify the affected run(s) and snapshot(s):
   ```sql
   SELECT r.run_id, r.teacher_id, r.status, s.snapshot_id, s.artifact_type, s.created_at
   FROM public.runs r
   JOIN public.artifact_snapshots s ON s.run_id = r.run_id
   WHERE r.run_id IN ('<run_id_1>', '<run_id_2>')
     AND s.status = 'approved'
   ORDER BY s.created_at;
   ```
2. Determine delivery scope: check whether exported HTML files were downloaded or
   shared (check export file timestamps and any delivery logs).
3. Identify the root cause:
   - Model output issue: check Langfuse traces for the affected run IDs.
   - Template/renderer issue: check the artifact JSON in `artifact_snapshots.content_json`.
   - Data input issue: check the original request in `run_contracts.contract_json`.
4. Assess whether the issue is isolated (one run) or systematic (multiple runs/teachers).

## Remediation

1. **Revoke approved snapshots** for the affected run:
   ```sql
   UPDATE public.artifact_snapshots
   SET status = 'recalled'
   WHERE snapshot_id IN ('<snapshot_id_1>', '<snapshot_id_2>');
   ```
   (Use the admin API endpoint if available: `POST /ops/snapshots/{snapshot_id}/recall`.)

2. **Delete or quarantine exported files** from the filesystem / object store:
   - Exported files live under `.scratch/pipeline-v2/artifacts/exports/{run_id}/`.
   - Move or delete the affected HTML files and revoke any sharing links.

3. **Notify affected teachers** via the notification system:
   - Use the admin notification endpoint to send a recall notice to the teacher's account.
   - Include the run ID, artifact type, and a brief reason.

4. **Mark the run for re-generation** if the content is needed:
   - Cancel the current run or create a new run for the same contract.
   - If the issue is a model regression, update model routing config before re-running.

5. **Systematic recall** (multiple runs): write a migration script that updates all
   affected snapshot rows and triggers notifications in bulk. Coordinate with the
   trust-and-safety team on the communication timeline.

## Escalation

- If the recall involves potential legal liability: escalate to legal and management
  immediately before any teacher communications.
- If the systematic root cause is a model regression: escalate to the ML team and
  pause the affected pipeline stage until resolved.
- If exported content has been widely distributed: follow the data incident response
  plan; record the incident in the incident log.

## Verify

1. Confirm affected snapshots are no longer in `approved` status:
   ```sql
   SELECT snapshot_id, status FROM public.artifact_snapshots
   WHERE snapshot_id IN ('<snapshot_id_1>', '<snapshot_id_2>');
   ```
   Expected: `status = 'recalled'` (or equivalent non-approved status).
2. Confirm exported files are no longer accessible (deleted or quarantined).
3. Confirm affected teachers received the recall notification (check notification table):
   ```sql
   SELECT teacher_id, payload, created_at FROM public.notifications
   WHERE payload->>'run_id' = '<run_id>'
   ORDER BY created_at DESC;
   ```
4. If re-generation was performed, confirm the new run completes and the replacement
   snapshots pass quality gate review before re-delivery.
