# Runbook: Gate-Timeout Backlog (24h TTL)

## Symptom

- Gate interrupts remain in `ACTIVE` status beyond 24 hours without a teacher response.
- `gate_backlog` SLO dimension exceeds `OMC_SLO_MAX_GATE_BACKLOG` (default 0).
- Teachers report that runs are paused and awaiting review but no notification was received.
- `gate_interrupts` table contains rows with `status = 'active'` and
  `created_at < NOW() - INTERVAL '24 hours'`.

## Alert

SLO breach fires via `dispatch_slo_alerts` in `services/gateway/slo_alerting.py` when
`gate_backlog > max_gate_backlog`.
Alert key: `global:gate_backlog`.
Delivered to `OMC_SLO_SLACK_WEBHOOK_URL` / `OMC_SLO_ZALO_WEBHOOK_URL`.

## Diagnosis

1. Query stale active gates:
   ```sql
   SELECT gate_id, run_id, gate_name, status, created_at, expires_at
   FROM public.gate_interrupts
   WHERE status = 'active'
     AND created_at < NOW() - INTERVAL '24 hours'
   ORDER BY created_at;
   ```
2. Confirm the sweeper is running the escalation path:
   ```
   grep "sweep_escalated_gates" <gateway log> | tail -20
   ```
   `sweep_escalated_gates` in `services/gateway/recovery_sweeper.py` uses
   `DEFAULT_GATE_TIMEOUT_HOURS = 24` as the cutoff.
3. Check whether the teacher received gate-open notifications. Look in `notifications`
   table or notification delivery logs.
4. Verify `GateInterrupt.created_at` vs `GateInterrupt.expires_at` — `expires_at` may
   be `NULL` if the gate was opened without an explicit expiry, relying on the sweeper.

## Remediation

1. **Automatic path**: `sweep_escalated_gates` runs on its periodic interval. It sets
   `status = 'EXPIRED'` for all active gates older than `timeout_hours` (default 24).
   The pipeline then treats an expired gate as an auto-escalation and continues or
   terminates the run based on the gate's escalation policy.

2. **Manual immediate escalation** of a specific gate:
   ```sql
   UPDATE public.gate_interrupts
   SET status = 'expired'
   WHERE gate_id = '<gate_id>' AND status = 'active';
   ```
   Then trigger the run to resume if applicable:
   ```
   POST /teaching-packs/runs/{run_id}/resume
   ```

3. If the teacher is reachable but missed the notification, resend the gate-open
   notification via the admin notification endpoint and extend the deadline manually
   (update `expires_at`).

4. If the teacher is unreachable, use admin authority to respond to the gate on their
   behalf via `POST /ops/gate/{gate_id}/respond`.

## Escalation

- If more than 5 gates are stuck and sweeper is running, investigate whether the
  escalation policy downstream is blocking run resumption.
- Contact the teacher's institution if the teacher account is inactive.
- If `sweep_escalated_gates` is not triggering, restart the gateway (sweeper runs in
  the lifespan background task).

## Verify

1. Confirm no active gates older than 24h remain:
   ```sql
   SELECT COUNT(*) FROM public.gate_interrupts
   WHERE status = 'active'
     AND created_at < NOW() - INTERVAL '24 hours';
   ```
   Expected: 0.
2. Confirm `gate_backlog` SLO recovers: `GET /ops/slo` → `gate_backlog = 0`.
3. Confirm affected runs have advanced beyond the gate (new events in `run_events`
   with a stage after the gate step).
