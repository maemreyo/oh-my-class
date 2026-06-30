---
title: Fail-closed production secrets validation
status: done
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Prevent booting production with development default secrets. Today there is no startup guard; dev defaults (`POSTGRES_PASSWORD=omc_dev`, `REDIS_AUTH=omc_redis_secret`, `LANGFUSE_ENCRYPTION_KEY=000…000`, `LANGFUSE_NEXTAUTH_SECRET`, `CLICKHOUSE_PASSWORD`, `MINIO_ROOT_PASSWORD`) would silently run in prod.

- A startup settings-validator: when `ENV=production`, refuse to boot if any secret equals its known dev default or is empty/all-zero, listing every offending variable.
- Keep the env-var interface; document secret-manager (Vault/cloud) injection as the recommended source; `.env.production` requires explicit overrides and commits no real secrets.
- Reject an all-zero/default `LANGFUSE_ENCRYPTION_KEY`; document a rotation procedure.

## Acceptance criteria

- [x] In `ENV=production`, startup hard-fails (clear, aggregated message) if any tracked secret is a known default / empty / all-zero.
- [x] In dev/staging, defaults are allowed (no behavior change).
- [x] The env-var interface is unchanged; docs describe secret-manager injection and required `.env.production` overrides.
- [x] `LANGFUSE_ENCRYPTION_KEY` all-zero/default is rejected in prod; rotation is documented.

## Detailed test suite

- [x] `services/gateway/tests/test_secrets_guard.py`: `ENV=production` + a default `POSTGRES_PASSWORD` → startup raises listing the offending var; overriding all secrets boots cleanly.
- [x] same file: `ENV=development` with defaults boots without error.
- [x] same file: all-zero `LANGFUSE_ENCRYPTION_KEY` in prod is rejected.
- [x] Run `uv run pytest services/gateway/tests/test_secrets_guard.py -v`.

## Verification

- `uv run pytest services/gateway/tests/test_secrets_guard.py -q` → 6 passed.

## Blocked by

None - can start immediately
