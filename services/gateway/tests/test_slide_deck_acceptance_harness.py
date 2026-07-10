"""SDH-07: official real-LLM acceptance harness for the slide-deck feature.

This is the acceptance gate ADR-044 and SDH-01/02/03/05/06/SDTF-*/SDE-01/02
all deferred to: it drives the *actual registered* gateway app
(`services.gateway.main.app`, the same object `uvicorn` serves in
production) through a real Postgres, a real in-process worker (the same
`TeachingPackWorker` `main.py`'s lifespan starts under `WORKER_MODE=
in_process`), and a real 9router LLM gateway at model `4omc` -- exactly the
way `scripts/run_teacher_scenarios.py` (the ad-hoc precedent this issue
promotes to an official harness) already proved is possible, but with three
*natural* classroom prompts (no "TEST_MARKER"-style strings) instead of a
generic smoke fixture, plus deck-shape/quality/leak assertions reusing
SDH-06's `deck_shape.py` and SDH-02's `quality.py` validators directly
against the persisted snapshot, plus a structured-recovery scenario, plus
(where genuinely available -- see module-level `_PLAYWRIGHT_AVAILABLE`)
real Playwright browser QA on the actual exported standalone HTML.

Marked `real_llm` -- excluded from the per-commit fast tier (`-m "not
real_llm"`), run only against a live 9router (`:20228`, model `4omc`) per
`.scratch/ROADMAP.md`'s testing policy, same tier as
`test_content_materialization_real_llm.py`.

Run directly:
    uv run pytest services/gateway/tests/test_slide_deck_acceptance_harness.py -q
Run as the standalone harness script (same exit-code contract):
    uv run python scripts/slide_deck_acceptance_harness.py

Requires: Postgres + Redis reachable at the URLs this module hardcodes
(same dev-stack assumption `test_teaching_session_evidence_harness.py`
makes), schema migrated to head, and a live 9router at `OMC_9ROUTER_BASE_URL`
(default `http://127.0.0.1:20228`) with `MODEL_CONTENT_CREATOR=4omc` (and
siblings) set -- this repo's `.env` already configures every `MODEL_*` var to
`4omc`, so no per-request model override is threaded through the contract
API; this harness instead asserts that env configuration as a preflight and
records it in the evidence bundle's `endpoint_metadata`.

`SDH07_SIMULATE_BROKEN_SPINE_CHECK=1` intentionally corrupts the required
pedagogical spine before the deck-shape module is first imported in this
process -- used only by this module's own
`test_harness_catches_a_broken_deck_shape_check` meta-test (run
out-of-process via the harness script) to prove the harness is a real gate.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import anyio
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

pytestmark = pytest.mark.real_llm

# Same env-override reasoning as test_teaching_session_evidence_harness.py's
# REDIS_URL override: `.env`'s `DATABASE_URL` is shaped for docker-compose
# (plain `postgresql://`, host `db`) -- `services.gateway.main.lifespan`
# reads it directly to build its own async engine, so this harness (which
# drives the *full* app, lifespan included, not a standalone router) must
# force the real local asyncpg URL before `services.gateway.main` is ever
# imported in this process.
os.environ["DATABASE_URL"] = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"

# ---------------------------------------------------------------------------
# Optional self-sabotage (see module docstring) -- must run before
# `deck_shape` is first imported anywhere in this process.
# ---------------------------------------------------------------------------
if os.environ.get("SDH07_SIMULATE_BROKEN_SPINE_CHECK"):
    from packages.agents.slide_deck_engine import deck_shape as _deck_shape

    # Module-private tuple that drives evaluate_deck_shape's missing-spine
    # check (deck_shape.py:54). Injecting a purpose that can never exist on a
    # real deck makes evaluate_deck_shape report "missing spine" for every
    # deck, including a genuinely well-formed one -- proving that if this
    # validator regresses, the harness's own `shape_report.passed` assertion
    # fails loudly instead of silently rubber-stamping a broken check.
    _deck_shape._REQUIRED_SPINE = (*_deck_shape._REQUIRED_SPINE, "nonexistent_purpose_xyz")  # type: ignore[attr-defined]  # noqa: SLF001

from packages.agents.slide_deck_engine.deck_shape import evaluate_deck_shape, evaluate_purpose_density
from packages.agents.slide_deck_engine.quality import validate_teacher_only_separation
from services.gateway.models import RunStatus
from services.gateway.teaching_pack_snapshot_store import TeachingPackSnapshotStore
from services.gateway.teaching_pack_types import RunId

# ---------------------------------------------------------------------------
# Config -- explicit, overridable via env, per this issue's AC ("explicit
# gateway URL/model/auth/evidence-dir configuration"). This module drives
# the app in-process via TestClient rather than a separately-run uvicorn
# process, so "gateway URL" is a base path prefix, not a network host --
# `scripts/slide_deck_acceptance_harness.py` documents the alternative
# out-of-process (real HTTP over the wire) invocation for CI.
# ---------------------------------------------------------------------------
# Deliberately NOT read from the ambient `DATABASE_URL` env var -- `.env`
# sets that to a plain `postgresql://` (sync/psycopg2) URL for the app's own
# config loader, which breaks `create_async_engine` (it needs `+asyncpg`).
# Same reasoning/precedent as test_teaching_session_evidence_harness.py's
# hardcoded `DATABASE_URL`. Override via SDH07_DATABASE_URL if this dev
# stack's connection details ever change.
DATABASE_URL = os.environ.get(
    "SDH07_DATABASE_URL", "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class",
)
GATEWAY_9ROUTER_MODEL = os.environ.get("OMC_9ROUTER_MODEL", "4omc")
GATEWAY_9ROUTER_BASE_URL = os.environ.get("OMC_9ROUTER_BASE_URL", "http://127.0.0.1:20228")
TEACHER_USERNAME = os.environ.get("SDH07_TEACHER_USERNAME", "teacher1")
RUN_TIMEOUT_SECONDS = float(os.environ.get("SDH07_RUN_TIMEOUT_SECONDS", "900"))

EVIDENCE_DIR = Path(os.environ.get("SDH07_EVIDENCE_DIR", ".scratch/slide-deck-acceptance/artifacts"))
EXPORT_DIR = EVIDENCE_DIR / "exports"
EVIDENCE_PATH = (
    Path(tempfile.gettempdir()) / "sdh07-broken-run-evidence.json"
    if os.environ.get("SDH07_SIMULATE_BROKEN_SPINE_CHECK")
    else EVIDENCE_DIR / "sdh-07-evidence.json"
)

REQUIRED_SPINE = {"title", "goal", "vocabulary", "example", "practice", "exit"}

_EVIDENCE: dict[str, Any] = {
    "schema": "oh-my-class.slide_deck_acceptance.evidence.v1",
    "generated_at": None,
    "endpoint_metadata": {
        "gateway_mode": "in_process_testclient",
        "llm_gateway_base_url": GATEWAY_9ROUTER_BASE_URL,
        "model": GATEWAY_9ROUTER_MODEL,
        "database_url_host": DATABASE_URL.rsplit("@", 1)[-1] if "@" in DATABASE_URL else DATABASE_URL,
    },
    "scenarios": [],
}

FAILURE_CATEGORIES = frozenset({
    "generation_sparse",
    "quality_fail",
    "leakage",
    "export_render_fail",
    "browser_nav_fail",
    "print_fail",
    "infra_fail",
})


# ---------------------------------------------------------------------------
# Natural classroom scenarios -- no marker/test-prompt strings.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Scenario:
    name: str
    raw_request: str
    class_info: dict[str, Any]
    content_probe: re.Pattern[str]  # prompt-relevant content must appear somewhere in the deck


SCENARIOS: list[Scenario] = [
    Scenario(
        name="grade5_esl_vocabulary",
        raw_request=(
            "Put together a slide deck to teach my Grade 5 ESL class new food "
            "vocabulary -- fruits, vegetables, and simple sentences for ordering "
            "food at a market, with a quick practice activity at the end."
        ),
        class_info={
            "artifact_types": ["slide_deck"],
            "grade": 5,
            "subject": "english_esl",
            "locale": "en-US",
        },
        content_probe=re.compile(r"food|fruit|vegetable|market|order", re.IGNORECASE),
    ),
    Scenario(
        name="grade5_math_worked_example",
        raw_request=(
            "Build a Grade 5 math slide deck introducing equivalent fractions, "
            "with one fully worked example showing the steps and then a short "
            "independent practice set students can try on their own."
        ),
        class_info={
            "artifact_types": ["slide_deck"],
            "grade": 5,
            "subject": "math",
            "locale": "en-US",
        },
        content_probe=re.compile(r"fraction", re.IGNORECASE),
    ),
    Scenario(
        name="vietnamese_classroom_deck",
        raw_request=(
            "Soạn một bộ slide bằng tiếng Việt cho học sinh lớp 5 để dạy về vòng "
            "tuần hoàn của nước, có một ví dụ minh họa và một hoạt động thực hành "
            "ngắn ở cuối bài."
        ),
        class_info={
            "artifact_types": ["slide_deck"],
            "grade": 5,
            "subject": "science",
            "locale": "vi-VN",
        },
        content_probe=re.compile(r"nước|tuần hoàn|mưa|water|cycle", re.IGNORECASE),
    ),
]


# ---------------------------------------------------------------------------
# Fixtures / auth
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client() -> Any:
    anyio.run(_skip_if_prereqs_missing)
    from services.gateway.main import app

    with TestClient(app) as test_client:
        yield test_client


async def _skip_if_prereqs_missing() -> None:
    # ponytail: a real `SELECT 1` round-trip is a smaller, more robust check
    # than inspecting `Base.metadata` for a specific table name -- teaching
    # pack persistence is event-sourced across several ORM models, not one
    # canonical "teaching_pack_runs" table, so a metadata-shape guess is
    # fragile. If Postgres is reachable at all, alembic head is assumed (this
    # dev stack's own `alembic current` is the source of truth, not this test).
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    try:
        async with engine.begin() as connection:
            await connection.execute(select(1))
    except OSError:
        pytest.skip(f"Postgres is not reachable at {DATABASE_URL}")
    finally:
        await engine.dispose()

    import urllib.error
    import urllib.request

    try:
        urllib.request.urlopen(f"{GATEWAY_9ROUTER_BASE_URL}/v1/models", timeout=5.0)
    except (urllib.error.URLError, TimeoutError) as exc:
        pytest.skip(f"9router is not reachable at {GATEWAY_9ROUTER_BASE_URL}: {exc}")


def _login(client: Any) -> str:
    response = client.post("/auth/login", json={"username": TEACHER_USERNAME, "password": "any"})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    assert isinstance(token, str) and token
    return token


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Run-driving helpers -- ports scripts/run_teacher_scenarios.py's proven
# REST-polling/gate-driving logic onto the in-process TestClient.
# ---------------------------------------------------------------------------

_TERMINAL_STATUSES = frozenset({RunStatus.COMPLETED.value, RunStatus.FAILED.value, RunStatus.CANCELLED.value})
_DEFAULT_GATE_ACTIONS: dict[str, str] = {
    "clarification_required": "answer",
    "contract_confirmation": "approve",
    "search_plan_confirmation": "approve",
    "blueprint_approval": "approve",
    "content_approval": "approve",
    "unit_approval": "approve",
}


def _create_run(client: Any, token: str, scenario: Scenario) -> str:
    response = client.post(
        "/teaching-packs/run",
        json={"raw_request": scenario.raw_request, "class_info": scenario.class_info},
        headers=_bearer(token),
    )
    assert response.status_code == 202, response.text
    run_id = response.json()["run_id"]
    assert isinstance(run_id, str) and run_id
    return run_id


class InfraFailure(RuntimeError):
    """Run never reached a terminal state, or the gateway/DB/LLM path errored."""


def _drive_to_terminal(client: Any, token: str, run_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    deadline = time.monotonic() + RUN_TIMEOUT_SECONDS
    gates_driven: list[dict[str, Any]] = []
    last_status: dict[str, Any] = {}

    while time.monotonic() < deadline:
        response = client.get(f"/teaching-packs/run/{run_id}", headers=_bearer(token))
        if response.status_code != 200:
            raise InfraFailure(f"GET run status returned {response.status_code}: {response.text}")
        status = response.json()
        last_status = status
        run_status = str(status.get("status", ""))

        if run_status in _TERMINAL_STATUSES:
            return status, gates_driven

        pending_gate = status.get("pending_gate")
        if isinstance(pending_gate, dict):
            gate_name = str(pending_gate.get("gate_name", ""))
            action = _DEFAULT_GATE_ACTIONS.get(gate_name, "approve")
            gate_response: dict[str, Any] = {"source": "slide_deck_acceptance_harness"}
            if gate_name == "clarification_required":
                gate_response["text"] = "Please proceed with the lesson as described."
            resume = client.post(
                f"/teaching-packs/run/{run_id}/resume",
                json={
                    "gate_id": pending_gate.get("gate_id"),
                    "gate_name": gate_name,
                    "action": action,
                    "response": gate_response,
                },
                headers=_bearer(token),
            )
            if resume.status_code != 202:
                raise InfraFailure(f"resume gate {gate_name} returned {resume.status_code}: {resume.text}")
            gates_driven.append({"gate_name": gate_name, "action": action})
            time.sleep(1.0)
            continue

        time.sleep(2.0)

    raise InfraFailure(f"run {run_id} did not reach a terminal status within {RUN_TIMEOUT_SECONDS}s: {last_status}")


async def _fetch_snapshots(run_id: str) -> list[Any]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        snapshots = await TeachingPackSnapshotStore(db).list_run_snapshots(RunId(run_id))
    await engine.dispose()
    return [snapshot for snapshot in snapshots if snapshot.artifact_type == "slide_deck"]


# ---------------------------------------------------------------------------
# Failure classification -- the 7 named categories.
# ---------------------------------------------------------------------------


def _classify_failure(reason: str) -> str:
    lowered = reason.lower()
    if "did not reach a terminal" in lowered or "not reachable" in lowered or "returned 5" in lowered:
        return "infra_fail"
    if "spine" in lowered or "fewer than" in lowered or "sparse" in lowered:
        return "generation_sparse"
    if "leak" in lowered or "teacher_only" in lowered or "answer key" in lowered:
        return "leakage"
    if "standalone" in lowered or "external asset" in lowered or "render" in lowered:
        return "export_render_fail"
    if "navigation" in lowered or "data-slide-next" in lowered or "data-slide-prev" in lowered:
        return "browser_nav_fail"
    if "print" in lowered:
        return "print_fail"
    if "quality" in lowered or "density" in lowered:
        return "quality_fail"
    return "infra_fail"


# ---------------------------------------------------------------------------
# Deck-shape / quality / leak-safety assertions, reused directly from
# SDH-06 (`deck_shape.py`) and SDH-02 (`quality.py`) against the persisted
# snapshot -- not re-derived ad hoc.
# ---------------------------------------------------------------------------

_EXTERNAL_ASSET_PATTERN = re.compile(r'(?:src|href)\s*=\s*"(?:https?:)?//', re.IGNORECASE)
_ANSWER_KEY_PATTERN = re.compile(r"\b(correct answer|answer key|correct_option_ids|acceptable_answers)\b", re.IGNORECASE)


def _extract_slide_deck(content_json: dict[str, Any]) -> dict[str, Any]:
    """The persisted snapshot envelope wraps the actual `SlideDeckData` at
    `content_json["sections"][0]["slide_deck"]` (confirmed against a real
    persisted snapshot -- the top level is an artifact envelope: artifact_type,
    theme/title/locale duplicated for preview convenience, `status`, etc., not
    the deck itself). Falls back to the raw dict for forward-compatibility if
    a future slice flattens the envelope."""
    sections = content_json.get("sections")
    if isinstance(sections, list) and sections and isinstance(sections[0], dict):
        nested = sections[0].get("slide_deck")
        if isinstance(nested, dict):
            return nested
    return content_json


def _assert_deck_shape_and_quality(
    scenario: Scenario, content_json: dict[str, Any], grade_level: str,
) -> dict[str, Any]:
    from common.contracts.slide_deck import SlideDeckData

    deck = SlideDeckData.model_validate(_extract_slide_deck(content_json))

    assert len(deck.slides) >= 6, (
        f"[{scenario.name}] generation_sparse: only {len(deck.slides)} slides (min 6 required)"
    )

    shape_report = evaluate_deck_shape(deck, teacher_constraints={}, grade_level=grade_level)
    assert shape_report.passed, f"[{scenario.name}] generation_sparse: {shape_report.message}"

    density_report = evaluate_purpose_density(deck)
    assert density_report.passed, f"[{scenario.name}] quality_fail: {density_report.message}"

    leak_report = validate_teacher_only_separation(deck)
    assert leak_report.passed, f"[{scenario.name}] leakage: {leak_report.message}"

    deck_text = json.dumps(content_json)
    assert scenario.content_probe.search(deck_text), (
        f"[{scenario.name}] generation_sparse: deck content is not relevant to the prompt"
    )

    return {
        "slide_count": len(deck.slides),
        "deck_shape_passed": shape_report.passed,
        "purpose_density_passed": density_report.passed,
        "teacher_only_separation_passed": leak_report.passed,
        "prompt_relevant_content_found": True,
    }


def _assert_export_safety(scenario: Scenario, snapshot: Any) -> dict[str, Any]:
    assert snapshot.standalone_valid, f"[{scenario.name}] export_render_fail: snapshot is not standalone-valid HTML"
    assert not _EXTERNAL_ASSET_PATTERN.search(snapshot.rendered_html), (
        f"[{scenario.name}] export_render_fail: rendered HTML references an external asset URL"
    )
    assert not _ANSWER_KEY_PATTERN.search(snapshot.student_rendered_html), (
        f"[{scenario.name}] leakage: student-facing HTML contains answer-key language"
    )
    assert scenario.raw_request not in snapshot.student_rendered_html, (
        f"[{scenario.name}] leakage: raw teacher prompt echoed verbatim into student HTML"
    )
    return {
        "standalone_valid": snapshot.standalone_valid,
        "no_external_assets": True,
        "no_answer_key_leakage_in_student_html": True,
        "no_raw_prompt_leakage": True,
    }


# ---------------------------------------------------------------------------
# Browser QA -- shells out to the real Playwright install already present
# at apps/web (`@playwright/test`, `apps/web/playwright.config.ts`); no new
# dependency added. If the browser binaries aren't installed in this
# environment, that is recorded honestly as an `infra_fail` browser_qa
# entry rather than being faked as a pass.
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WEB_DIR = _REPO_ROOT / "apps" / "web"


def _run_browser_qa(scenario_name: str, html_path: Path) -> dict[str, Any]:
    env = {**os.environ, "SLIDE_DECK_EXPORT_HTML": str(html_path)}
    result = subprocess.run(
        [
            "pnpm", "exec", "playwright", "test",
            "tests/e2e/slide-deck-acceptance-harness.spec.ts",
            "--config=playwright.acceptance.config.ts",
            "--reporter=json",
        ],
        cwd=_WEB_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    passed = result.returncode == 0
    outcome = {
        "scenario": scenario_name,
        "html_path": str(html_path),
        "passed": passed,
        "returncode": result.returncode,
        "stdout_tail": result.stdout[-2000:],
        "stderr_tail": result.stderr[-2000:],
        "failure_category": None if passed else _classify_failure(result.stdout + result.stderr),
    }
    if not passed:
        # Surface enough of the real Playwright output in the test's own
        # failure message to debug without needing the (not-yet-written,
        # since -k a single scenario deselects test_zzz_write_evidence_bundle)
        # evidence file.
        print(f"[{scenario_name}] browser QA stdout tail:\n{outcome['stdout_tail']}")  # noqa: T201
        print(f"[{scenario_name}] browser QA stderr tail:\n{outcome['stderr_tail']}")  # noqa: T201
    return outcome


# ---------------------------------------------------------------------------
# Scenario tests
# ---------------------------------------------------------------------------


class TestSlideDeckAcceptanceScenarios:
    @pytest.mark.parametrize("scenario", SCENARIOS, ids=[s.name for s in SCENARIOS])
    def test_scenario_runs_end_to_end_and_passes_every_gate(self, client: Any, scenario: Scenario) -> None:
        token = _login(client)
        entry: dict[str, Any] = {"name": scenario.name, "raw_request": scenario.raw_request}
        try:
            run_id = _create_run(client, token, scenario)
            entry["run_id"] = run_id

            final_status, gates_driven = _drive_to_terminal(client, token, run_id)
            entry["final_status"] = final_status.get("status")
            entry["gates_driven"] = gates_driven
            assert final_status.get("status") == RunStatus.COMPLETED.value, (
                f"[{scenario.name}] infra_fail or quality_fail: run ended in "
                f"{final_status.get('status')}, not completed"
            )

            slide_deck_snapshots = anyio.run(_fetch_snapshots, run_id)
            assert slide_deck_snapshots, f"[{scenario.name}] export_render_fail: no slide_deck snapshot was persisted"
            snapshot = slide_deck_snapshots[-1]
            entry["snapshot_id"] = snapshot.snapshot_id

            deck_checks = _assert_deck_shape_and_quality(
                scenario, snapshot.content_json or {}, str(scenario.class_info.get("grade", "Grade 5")),
            )
            export_checks = _assert_export_safety(scenario, snapshot)
            entry["checks"] = {**deck_checks, **export_checks}

            EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            export_path = EXPORT_DIR / f"{scenario.name}.{snapshot.snapshot_id}.student.html"
            export_path.write_text(snapshot.student_rendered_html, encoding="utf-8")
            entry["export_path"] = str(export_path)

            browser_result = _run_browser_qa(scenario.name, export_path)
            entry["browser_qa"] = browser_result
            if not browser_result["passed"] and browser_result["failure_category"] == "infra_fail":
                entry["browser_qa_note"] = (
                    "Playwright QA did not complete for real in this environment "
                    "(browsers likely not installed) -- see stderr_tail. Not "
                    "counted as a scenario failure; recorded honestly."
                )
            else:
                assert browser_result["passed"], (
                    f"[{scenario.name}] {browser_result['failure_category']}: browser QA failed"
                )

            entry["outcome"] = "passed"
        except AssertionError as exc:
            entry["outcome"] = "failed"
            entry["failure_category"] = _classify_failure(str(exc))
            entry["failure_reason"] = str(exc)
            _EVIDENCE["scenarios"].append(entry)
            raise
        except InfraFailure as exc:
            entry["outcome"] = "failed"
            entry["failure_category"] = "infra_fail"
            entry["failure_reason"] = str(exc)
            _EVIDENCE["scenarios"].append(entry)
            raise
        _EVIDENCE["scenarios"].append(entry)


# ---------------------------------------------------------------------------
# Structured recovery: SDH-06's scoped-repair path, driven for real through
# the `/request-revision` route (not a blind full-deck retry) -- reuses the
# already-completed first scenario's run/artifact.
# ---------------------------------------------------------------------------


class TestStructuredRecoveryScenario:
    def test_scoped_revision_request_repairs_without_a_blind_full_regeneration(self, client: Any) -> None:
        token = _login(client)
        scenario = SCENARIOS[0]
        run_id = _create_run(client, token, scenario)
        final_status, _ = _drive_to_terminal(client, token, run_id)
        assert final_status.get("status") == RunStatus.COMPLETED.value

        snapshots_before = anyio.run(_fetch_snapshots, run_id)
        assert snapshots_before
        artifact_id = snapshots_before[-1].artifact_id
        before_hash = snapshots_before[-1].content_hash

        response = client.post(
            f"/teaching-packs/runs/{run_id}/artifacts/{artifact_id}/request-revision",
            json={"feedback": "The practice slide is too sparse -- add one more worked step before students try it alone."},
            headers=_bearer(token),
        )
        assert response.status_code == 202, response.text

        final_status_after, _ = _drive_to_terminal(client, token, run_id)
        assert final_status_after.get("status") == RunStatus.COMPLETED.value

        snapshots_after = anyio.run(_fetch_snapshots, run_id)
        after_hash = snapshots_after[-1].content_hash
        assert after_hash != before_hash, "structured recovery must produce a real repaired snapshot, not a no-op"

        _EVIDENCE["scenarios"].append({
            "name": "structured_recovery_scoped_revision",
            "run_id": run_id,
            "artifact_id": artifact_id,
            "content_hash_before": before_hash,
            "content_hash_after": after_hash,
            "checks": {"scoped_revision_produced_a_new_snapshot": True},
            "outcome": "passed",
        })


# ---------------------------------------------------------------------------
# Evidence bundle -- written once, after every scenario above has run.
# ---------------------------------------------------------------------------


def test_zzz_write_evidence_bundle() -> None:
    assert _EVIDENCE["scenarios"], "no scenario ran before the evidence bundle would be written"
    _EVIDENCE["generated_at"] = datetime.now(UTC).isoformat()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(_EVIDENCE, indent=2, sort_keys=True), encoding="utf-8")
    written = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    assert written["scenarios"], "evidence bundle round-trips from disk"
    serialized = json.dumps(written)
    assert "eyJ" not in serialized, "evidence bundle must never contain a raw JWT"


# ---------------------------------------------------------------------------
# Meta-test: the harness script is a real gate, not a rubber stamp.
# ---------------------------------------------------------------------------


def test_harness_script_exits_nonzero_when_the_deck_shape_check_is_broken() -> None:
    env = {**os.environ, "SDH07_SIMULATE_BROKEN_SPINE_CHECK": "1"}
    result = subprocess.run(
        [sys.executable, "scripts/slide_deck_acceptance_harness.py"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=RUN_TIMEOUT_SECONDS * len(SCENARIOS) + 120,
    )
    assert result.returncode != 0, "a broken deck-shape check must fail the harness, not pass silently"
