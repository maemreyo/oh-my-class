# Module: infra

**Path:** `infra`
**Role:** Docker Compose orchestration and Dockerfiles for the full development stack.

## Public interface

- `docker-compose.yml` — 8 services: db, redis, gateway, langfuse-web, langfuse-worker, clickhouse, minio, web
- `Dockerfile.gateway` — Python gateway container
- `Dockerfile.web` — Next.js web container
- `Dockerfile.proxy` — (legacy, not referenced in compose)

## Internal structure

- `compose/docker-compose.yml` — Full development stack
- `docker/Dockerfile.gateway` — Multi-stage Python build
- `docker/Dockerfile.web` — Multi-stage Next.js build

## Data model (docker-compose services)

| Service | Image | Ports | Depends on |
|---------|-------|-------|-----------|
| `db` | postgres:16-alpine | 5432 | — |
| `redis` | redis:7-alpine | 6379 | — |
| `gateway` | Built from infra/docker/Dockerfile.gateway | 8001 | db, redis, langfuse-web |
| `web` | Built from infra/docker/Dockerfile.web | 3000 | gateway |
| `langfuse-web` | langfuse/langfuse:3 | 3100 | db, clickhouse, redis, minio |
| `langfuse-worker` | langfuse/langfuse-worker:3 | — | db, clickhouse, redis, minio |
| `clickhouse` | clickhouse/clickhouse-server | 8123, 9000 | — |
| `minio` | cgr.dev/chainguard/minio | 9090, 9091 | — |

## Depends on

- **None** (infrastructure definition only)

## Used by

- **`tests`** — `tests/test_system_trace_refs.py` validates infra paths

---

_Traced from source on 2026-07-10. Files examined: all 6 files._
