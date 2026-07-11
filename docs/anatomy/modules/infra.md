# Module: infra

**Path:** `infra`
**Role:** Infrastructure configuration — Docker Compose manifests, Dockerfiles, and database initialization scripts for local dev and production deployment.

## Public interface

This module has no code API. It provides infrastructure-as-configuration consumed by `docker compose` and CI/CD.

### Docker Compose services (local dev: `docker-compose.yml`)

| Service | Image/Build | Port | Purpose |
|---------|-------------|------|---------|
| `db` | `postgres:16-alpine` | `5432:5432` | Application PostgreSQL + Langfuse DB |
| `redis` | `redis:7-alpine` | `6379:6379` | Caching, Langfuse queue |
| `gateway` | `Dockerfile.gateway` | `8001:8001` | FastAPI + embedded agent runtime |
| `web` | `Dockerfile.web` | `3000:3000` | Next.js dashboard |
| `langfuse-web` | `langfuse/langfuse:3` | `3100:3000` | Langfuse v3 observability UI |
| `langfuse-worker` | `langfuse/langfuse-worker:3` | — | Langfuse background worker (profile: `langfuse-worker`) |
| `clickhouse` | `clickhouse/clickhouse-server` | `127.0.0.1:8123`, `9000` | Langfuse v3 traces store |
| `minio` | `cgr.dev/chainguard/minio` | `9090:9000`, `9091:9001` | Langfuse v3 object storage |

### Dockerfiles

| File | Base | Purpose |
|------|------|---------|
| `infra/docker/Dockerfile.gateway` | `python:3.12-slim` | Gateway: installs `services/gateway/requirements.txt`, copies `packages/` + `common/`, runs uvicorn on `:8001` |
| `infra/docker/Dockerfile.web` | `node:22-alpine` | Web: pnpm install, builds `@oh-my-class/web`, runs `pnpm start` on `:3000` |
| `infra/docker/Dockerfile.proxy` | `ghcr.io/berriai/litellm:main-latest` | LiteLLM proxy: copies `config.yaml`, runs on `:4000` |

### Database initialization

`infra/compose/init-db.sh` — creates a `langfuse` database in the same PostgreSQL instance used by the app.

### Production overrides (`docker-compose.prod.yml`)

- Gateway: 2 replicas, 1GB memory limit, no exposed ports
- Web: 2 replicas
- DB: no port mapping, 2GB memory limit
- Redis: 512MB memory limit
- Langfuse: 1GB memory limit

## Internal structure

```
infra/
├── compose/
│   ├── docker-compose.yml        # Local dev compose (9 services)
│   ├── docker-compose.prod.yml   # Production overrides (replicas, memory limits)
│   └── init-db.sh                # Creates langfuse DB in PostgreSQL
└── docker/
    ├── Dockerfile.gateway         # Python 3.12-slim, uvicorn on :8001
    ├── Dockerfile.web             # Node 22-alpine, pnpm, Next.js on :3000
    └── Dockerfile.proxy           # LiteLLM proxy (optional, production-only)
```

## Depends on

| Target | What | Where cited |
|--------|------|-------------|
| `services/gateway` | Source code copied into gateway image | `Dockerfile.gateway:4-5` |
| `packages/*` | Source code copied into gateway + web images | `Dockerfile.gateway:5`; `Dockerfile.web:12` |
| `common/*` | Schema/contract source copied into images | `Dockerfile.gateway:6`; `Dockerfile.web:15` |
| `services/proxy/config.yaml` | LiteLLM config copied into proxy image | `Dockerfile.proxy:3` |

**Note:** These are filesystem-level COPY dependencies in Dockerfiles, not Python/TS import dependencies. The infra module has zero code imports.

**Phase 3 hypothesis "no outbound imports" — CONFIRMED.** Infra contains only Dockerfiles (shell), Compose YAML, and a bash init script. No Python or TypeScript code exists in this module.

## Used by

| Consumer | What consumed |
|----------|---------------|
| **Developers** | `docker compose up` for local development |
| **CI/CD** | `docker compose -f docker-compose.yml -f docker-compose.prod.yml` for deployment |
| **Makefile** | `make dev` references gateway port |

## Data & side effects

- **Ports exposed:** PostgreSQL 5432, Redis 6379, Gateway 8001, Web 3000, Langfuse 3100, ClickHouse 8123/9000, MinIO 9090/9091
- **Volumes:** `pgdata`, `langfuse_clickhouse_data`, `langfuse_clickhouse_logs`, `langfuse_minio_data`
- **Env vars consumed:** `REDIS_AUTH`, `PROD_DB_PASSWORD`, `LANGFUSE_NEXTAUTH_SECRET`, `LANGFUSE_SALT`, `LANGFUSE_ENCRYPTION_KEY`, `CLICKHOUSE_PASSWORD`, `MINIO_ROOT_PASSWORD`
- **Shared volumes:** PostgreSQL hosts both app DB (`oh_my_class`) and Langfuse DB (`langfuse`)

## Notes / discrepancies vs existing docs

- AGENTS.md §11 documents gateway port as `:8001` in Docker — **confirmed** by `docker-compose.yml` `gateway` service port mapping `8001:8001`.
- AGENTS.md §11 documents local dev port as `:8101` — this is in the Makefile (`LOCAL_GATEWAY_PORT := 8101`), not in compose. Compose always uses `8001:8001`. The `8101` port is only used when running `make dev` (direct uvicorn, not Docker).
- The LiteLLM proxy (`Dockerfile.proxy`) is defined but **not referenced in `docker-compose.yml`**. It's referenced only in `docker-compose.prod.yml` under the `proxy` service definition — suggesting it's an optional production-only add-on.
- ClickHouse and MinIO are Langfuse v3 dependencies, not directly used by the oh-my-class application code. They exist solely for Langfuse observability storage.
- `langfuse-worker` requires explicit `--profile langfuse-worker` to run (`profiles: [langfuse-worker]` in compose).

---
_Traced from source on 2026-07-11. Files examined in depth: all 6 files in infra/ (3 compose + 3 Dockerfiles). Zero code — pure infrastructure configuration._
