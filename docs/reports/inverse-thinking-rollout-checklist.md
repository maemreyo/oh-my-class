# Inverse Thinking rollout checklist

## Dev validation

- Enable `features.inverse_thinking_v1` only in local/dev config.
- Run focused contract, methodology, quality, renderer, web editor, and E2E release-flow tests.
- Verify exported HTML remains standalone with no external assets.

## Staging validation

- Enable the flag for staging teachers only.
- Confirm mocked and sandboxed LLM runs produce canonical inverse-thinking packs before projection.
- Validate quality-gate warnings and critical failures appear in run metadata.

## Beta teacher enablement

- Enable by explicit beta cohort or teacher allow-list.
- Provide the structured editor and methodology inspector before broad release.
- Track approval and reject rates per teacher action.

## Fallback and escalation behavior

- No silent downgrade from failed inverse-thinking generation to a standard lesson.
- Escalate after repair exhaustion and preserve the failing case-field feedback.
- Keep standard generation working when `features.inverse_thinking_v1` is disabled.

## Metrics to monitor

- Methodology, creative frame, projection, feature flag, quality gate, repair attempt, warning category, teacher action, export pass/fail.
- Approval/reject rate, repair exhaustion rate, and export failure rate.

## No silent downgrade

- Any inverse-thinking request with a disabled flag or failed quality gate must block, repair, or escalate.
- Standard lesson generation is allowed only when the teacher did not request inverse thinking.
