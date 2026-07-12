"""Queue-depth autoscaler for the standalone worker fleet (#119 OPS-06).

No Kubernetes/KEDA exists in this repo (`infra/` is Docker Compose only, see
`infra/compose/`) -- so this polls `count_claimable_run_jobs`
(`services/gateway/queue_depth.py`) on an interval and drives
`docker compose up -d --scale worker=<n>` against the `worker` service
(`infra/compose/docker-compose.yml`), the same mechanism the compose file
already uses for `gateway`/`web` replica counts in
`infra/compose/docker-compose.prod.yml`.

Run it out-of-band from the fleet itself (systemd timer, cron, or a CI
schedule) with `python -m services.gateway.autoscaler --interval-seconds 30`,
or `--once` for a single pass (e.g. from a scheduler). It does not need to be
containerized: driving `docker compose` from inside a container would need a
mounted docker socket (a real privilege escalation) for no benefit here.

Ceiling math (ADR-034 §4 "ceilinged by provider rate limits"): the fleet's
aggregate in-flight LLM request budget is `replicas * WORKER_CONCURRENCY`.
`PROVIDER_MAX_CONCURRENT_REQUESTS` is that budget's cap -- set it to the
target provider's actual concurrent-request/rate-limit headroom (OPS-01's
fallback provider). `effective_ceiling` divides it by `WORKER_CONCURRENCY` so
scaling never pushes aggregate concurrency past that budget regardless of how
many jobs are backlogged.
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
from dataclasses import dataclass
from math import ceil

import anyio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.queue_depth import count_claimable_run_jobs

logger = logging.getLogger("services.gateway.autoscaler")

COMPOSE_FILES = ("infra/compose/docker-compose.yml", "infra/compose/docker-compose.prod.yml")
WORKER_SERVICE = "worker"


@dataclass(frozen=True, slots=True)
class AutoscaleConfig:
    floor_replicas: int
    max_replicas: int
    jobs_per_worker: int
    worker_concurrency: int
    provider_max_concurrent_requests: int
    breaker_providers: tuple[str, ...]
    redis_url: str | None

    @classmethod
    def from_env(cls) -> AutoscaleConfig:
        providers_raw = os.getenv("AUTOSCALE_BREAKER_PROVIDERS", "")
        return cls(
            floor_replicas=int(os.getenv("WORKER_FLOOR_REPLICAS", "1")),
            max_replicas=int(os.getenv("WORKER_MAX_REPLICAS", "5")),
            jobs_per_worker=int(os.getenv("AUTOSCALE_JOBS_PER_WORKER", "3")),
            worker_concurrency=int(os.getenv("WORKER_CONCURRENCY", "1")),
            provider_max_concurrent_requests=int(os.getenv("PROVIDER_MAX_CONCURRENT_REQUESTS", "40")),
            breaker_providers=tuple(p.strip() for p in providers_raw.split(",") if p.strip()),
            redis_url=os.getenv("REDIS_URL"),
        )


def effective_ceiling(config: AutoscaleConfig) -> int:
    """Replica ceiling after applying the provider-rate-limit budget on top
    of the configured max. Never below the floor, so a misconfigured
    (too-small) provider budget can't starve the fleet under the floor."""
    provider_ceiling = max(1, config.provider_max_concurrent_requests // max(1, config.worker_concurrency))
    return max(config.floor_replicas, min(config.max_replicas, provider_ceiling))


def compute_desired_replicas(queue_depth: int, config: AutoscaleConfig, *, breaker_open: bool) -> int:
    """Scale up toward backlog, down to the floor when drained, clamped by
    `effective_ceiling`. When a provider breaker is open, don't scale up past
    whatever's already running -- pushing more replicas at a dead provider
    just wastes claims/leases (ADR-034 §4: "must not keep scaling up into a
    dead provider")."""
    ceiling = effective_ceiling(config)
    if queue_depth <= 0:
        return config.floor_replicas
    wanted = ceil(queue_depth / max(1, config.jobs_per_worker))
    desired = max(config.floor_replicas, min(ceiling, wanted))
    if breaker_open:
        desired = config.floor_replicas
    return desired


def any_provider_breaker_open(providers: tuple[str, ...], redis_url: str | None) -> bool:
    """Best-effort: reads breaker state Redis-hash-per-provider
    (`cb:provider:<name>`, the same key shape
    `common.contracts.provider_circuit_breaker.ProviderCircuitBreaker` writes
    when given a store).

    # ponytail: production `packages/llm_client/circuit_breaker.py` never
    # wires `_provider_store` to Redis today, so breaker state is
    # in-memory-per-process and this will read nothing until that's wired
    # (separate gap, not this issue's scope). Fails open (treats
    # unreachable/missing state as closed) rather than block scaling on an
    # absent signal -- upgrade path: wire `_provider_store` to
    # `RedisBreakerStore` in gateway/worker startup, then this becomes a real
    # cross-process check with no code change here.
    """
    if not providers or not redis_url:
        return False
    from packages.agents.healing.redis_breaker_store import RedisBreakerStore

    try:
        store = RedisBreakerStore.from_url(redis_url)
        for provider in providers:
            state = store.get(f"cb:provider:{provider}")
            if state is not None and str(state.get("state")) == "open":
                return True
    except OSError:
        logger.warning("autoscaler: breaker store unreachable, treating as closed", exc_info=True)
        return False
    return False


async def compute_target_replicas(session_factory: async_sessionmaker, config: AutoscaleConfig) -> int:
    async with session_factory() as session:
        queue_depth = await count_claimable_run_jobs(session)
    breaker_open = any_provider_breaker_open(config.breaker_providers, config.redis_url)
    return compute_desired_replicas(queue_depth, config, breaker_open=breaker_open)


def apply_scale(replicas: int, *, dry_run: bool) -> None:
    args = [
        "docker", "compose",
        *[arg for f in COMPOSE_FILES for arg in ("-f", f)],
        "--profile", "worker",
        "up", "-d", "--scale", f"{WORKER_SERVICE}={replicas}", "--no-recreate",
    ]
    logger.info("autoscaler: target replicas=%d (%s)", replicas, "dry-run" if dry_run else "applying")
    if dry_run:
        return
    subprocess.run(args, check=True)  # noqa: S603


async def run_once(database_url: str, config: AutoscaleConfig, *, dry_run: bool) -> int:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        replicas = await compute_target_replicas(session_factory, config)
    finally:
        await engine.dispose()
    apply_scale(replicas, dry_run=dry_run)
    return replicas


async def main_async() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Run a single pass and exit.")
    parser.add_argument("--interval-seconds", type=float, default=30.0)
    parser.add_argument("--dry-run", action="store_true", help="Compute and log, don't scale.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    database_url = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class",
    )
    config = AutoscaleConfig.from_env()

    if args.once:
        await run_once(database_url, config, dry_run=args.dry_run)
        return

    while True:
        await run_once(database_url, config, dry_run=args.dry_run)
        await anyio.sleep(args.interval_seconds)


def main() -> None:
    anyio.run(main_async)


if __name__ == "__main__":
    main()
