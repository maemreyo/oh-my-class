# /// script
# requires-python = ">=3.12"
# ///
"""QA-02 load / performance test harness — entrypoint.

Drives the real gateway+worker pipeline at a configurable rate/burst,
measures p50/p95/p99 pack latency, run-success rate, and queue-depth
draining from the same run_events/Run/RunJob tables the OPS-03 dashboard
reads, asserts the ADR-034 SLOs, compares against a stored baseline, and
writes a perf report. Exits non-zero on SLO breach or a flagged regression.

── Usage ──
  smoke (CI-safe, fast, low volume):
    uv run python scripts/load_test.py --profile smoke --mock-llm

  full (5,000/day-equivalent — needs a real running fleet + real wall-clock
  time; NOT safe/runnable in an automated CI environment):
    uv run python scripts/load_test.py --profile full

See scripts/load_test_mock_llm_server.py's module docstring for exactly
what the --mock-llm stub does and does not prove.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    # Needed for `python scripts/load_test.py` (repo root isn't on sys.path
    # by default the way pytest's pythonpath=. gives it to us) — this script
    # imports services.gateway.* directly to query run_events/Run for metrics.
    sys.path.insert(0, _REPO_ROOT)

from load_test_assert import assert_slo
from load_test_baseline import (
    BaselineMetrics,
    compare_to_baseline,
    load_baseline,
    save_baseline,
)
from load_test_driver import run_load_plan
from load_test_metrics import compute_perf_report, wait_for_terminal_or_timeout
from load_test_mock_llm_server import run_mock_llm_server
from load_test_profiles import PROFILES, generate_request_plan
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

DEFAULT_DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"
DEFAULT_BASELINE_DIR = Path("scripts/load_test_baselines")


async def _run(args: argparse.Namespace) -> int:
    profile = PROFILES[args.profile]
    plan = generate_request_plan(profile, seed=args.seed)
    print(f"profile={profile.name} requests={len(plan)} duration={profile.duration_seconds:.0f}s")

    started_at = datetime.now(UTC)
    outcomes = await run_load_plan(
        base_url=args.base_url, plan=plan, gate_watch_seconds=args.gate_watch_seconds,
    )
    submitted_run_ids = [o.run_id for o in outcomes if o.run_id is not None]
    submission_failures = [o for o in outcomes if o.run_id is None]
    if submission_failures:
        print(f"warning: {len(submission_failures)}/{len(plan)} submissions failed outright")

    engine = create_async_engine(args.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    def _progress(elapsed: float, depth: int, terminal_count: int) -> None:
        print(
            f"  t={elapsed:6.1f}s queue_depth={depth:4d} "
            f"terminal={terminal_count}/{len(submitted_run_ids)}",
        )

    queue_timeseries = await wait_for_terminal_or_timeout(
        session_factory,
        submitted_run_ids,
        timeout_seconds=args.wait_timeout_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
        on_sample=_progress,
    )

    async with session_factory() as session:
        perf = await compute_perf_report(
            session, submitted_run_ids, queue_depth_timeseries=queue_timeseries,
        )
    await engine.dispose()
    finished_at = datetime.now(UTC)

    # Submission failures count against success rate even though they never
    # became a Run row — a request the gateway rejected outright is a failure,
    # not a run to silently drop from the denominator.
    if submission_failures:
        total_terminal = perf.total_terminal + len(submission_failures)
        success_rate = (perf.total_completed / total_terminal) if total_terminal else None
        perf = replace(
            perf,
            total_submitted=len(plan),
            total_terminal=total_terminal,
            success_rate=success_rate,
        )

    assertion = assert_slo(
        p95_latency_seconds=perf.p95_latency_seconds,
        success_rate=perf.success_rate,
        queue_depth_timeseries=perf.queue_depth_timeseries,
    )

    current_metrics = BaselineMetrics(
        p50_latency_seconds=perf.p50_latency_seconds,
        p95_latency_seconds=perf.p95_latency_seconds,
        p99_latency_seconds=perf.p99_latency_seconds,
        success_rate=perf.success_rate,
        avg_tokens_per_run=perf.avg_tokens_per_run,
    )
    baseline_dir = Path(args.baseline_dir)
    baseline = load_baseline(baseline_dir, profile.name)
    regressions = compare_to_baseline(current_metrics, baseline) if baseline else []
    if args.update_baseline:
        path = save_baseline(baseline_dir, profile.name, current_metrics)
        print(f"baseline updated: {path}")
    elif baseline is None:
        print(f"no baseline stored yet for profile={profile.name} (pass --update-baseline to create one)")

    from load_test_report import build_report_json, write_report

    report = build_report_json(
        profile_name=profile.name,
        perf=perf,
        assertion=assertion,
        regressions=regressions,
        llm_mode="mock" if args.mock_llm else "real",
        started_at=started_at,
        finished_at=finished_at,
    )
    paths = write_report(Path(args.output_dir), report)
    print()
    print(paths.text_path.read_text(encoding="utf-8"))
    print(f"report: {paths.json_path}")

    if args.assert_slo and not assertion.passed:
        return 1
    if regressions:
        return 1
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="smoke")
    parser.add_argument("--base-url", default="http://localhost:8001")
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    parser.add_argument("--output-dir", default=".scratch/load-test")
    parser.add_argument("--baseline-dir", default=str(DEFAULT_BASELINE_DIR))
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--gate-watch-seconds", type=float, default=120.0)
    parser.add_argument("--wait-timeout-seconds", type=float, default=180.0)
    parser.add_argument("--poll-interval-seconds", type=float, default=2.0)
    parser.add_argument(
        "--mock-llm",
        action="store_true",
        help="Start scripts/load_test_mock_llm_server.py locally for the duration of the run. "
        "Does not by itself point a *running* gateway at it — see that module's docstring.",
    )
    parser.add_argument(
        "--no-assert", dest="assert_slo", action="store_false",
        help="Still measure and report, but always exit 0 regardless of SLO breach.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.mock_llm:
        with run_mock_llm_server() as base_url:
            print(f"mock LLM server: {base_url} (point the gateway process's LLM_BASE_URL here)")
            exit_code = asyncio.run(_run(args))
    else:
        exit_code = asyncio.run(_run(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
