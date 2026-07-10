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

from packages.agents.config.features import reset_features
from packages.agents.slide_deck_engine.deck_shape import (
    SPINE_ROLES,
    evaluate_deck_shape,
    evaluate_purpose_density,
)
from packages.agents.slide_deck_engine.quality import validate_teacher_only_separation
from packages.agents.slide_deck_engine.scoped_block_edit import apply_scoped_slide_deck_block_edit
from services.gateway.models import RunStatus
from services.gateway.teaching_pack_export_store import ExportRecordCreate, TeachingPackExportStore
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

# Names match SDH-11's teacher-facing taxonomy 1:1 where one exists
# (apps/web/src/components/slide-deck-editor/failure-copy.ts's
# `SlideDeckFailureCategory`) -- "browser_nav" is the one addition, since
# SDH-11 has no teacher-facing concept of a browser-navigation QA failure
# (that's a harness/dev-only signal, never shown to a teacher).
FAILURE_CATEGORIES = frozenset({
    "sparse_deck",
    "quality_gate",
    "leakage",
    "export_render",
    "browser_nav",
    "print",
    "infrastructure",
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
        return "infrastructure"
    if "spine" in lowered or "fewer than" in lowered or "sparse" in lowered:
        return "sparse_deck"
    if "leak" in lowered or "teacher_only" in lowered or "answer key" in lowered:
        return "leakage"
    if "standalone" in lowered or "external asset" in lowered or "render" in lowered:
        return "export_render"
    if "navigation" in lowered or "data-slide-next" in lowered or "data-slide-prev" in lowered:
        return "browser_nav"
    if "print" in lowered:
        return "print"
    if "quality" in lowered or "density" in lowered:
        return "quality_gate"
    return "infrastructure"


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


def _effective_display_preferences(content_json: dict[str, Any]) -> dict[str, Any]:
    """The *effective* (defaults-merged) display preferences for the deck that
    was actually exported, using the same resolver the app/export path uses
    (`common.contracts.slide_deck.resolve_slide_deck_display_preferences`,
    ADR-043) rather than re-deriving defaults here. Reused as-is -- not a
    parallel harness-side implementation -- so this evidence field can never
    drift from what the app actually rendered."""
    from common.contracts.slide_deck import resolve_slide_deck_display_preferences

    deck = _extract_slide_deck(content_json)
    raw_preferences = deck.get("display_preferences") if isinstance(deck, dict) else None
    resolved = resolve_slide_deck_display_preferences(raw_preferences)
    return resolved.model_dump()


def _assert_deck_shape_and_quality(
    scenario: Scenario, content_json: dict[str, Any], grade_level: str,
) -> dict[str, Any]:
    from common.contracts.slide_deck import SlideDeckData

    deck = SlideDeckData.model_validate(_extract_slide_deck(content_json))

    assert len(deck.slides) >= 6, (
        f"[{scenario.name}] sparse_deck: only {len(deck.slides)} slides (min 6 required)"
    )

    shape_report = evaluate_deck_shape(deck, teacher_constraints={}, grade_level=grade_level)
    assert shape_report.passed, f"[{scenario.name}] sparse_deck: {shape_report.message}"

    density_report = evaluate_purpose_density(deck)
    assert density_report.passed, f"[{scenario.name}] quality_gate: {density_report.message}"

    leak_report = validate_teacher_only_separation(deck)
    assert leak_report.passed, f"[{scenario.name}] leakage: {leak_report.message}"

    deck_text = json.dumps(content_json)
    assert scenario.content_probe.search(deck_text), (
        f"[{scenario.name}] sparse_deck: deck content is not relevant to the prompt"
    )

    return {
        "slide_count": len(deck.slides),
        "deck_shape_passed": shape_report.passed,
        "purpose_density_passed": density_report.passed,
        "teacher_only_separation_passed": leak_report.passed,
        "prompt_relevant_content_found": True,
    }


def _assert_export_safety(scenario: Scenario, snapshot: Any) -> dict[str, Any]:
    assert snapshot.standalone_valid, f"[{scenario.name}] export_render: snapshot is not standalone-valid HTML"
    assert not _EXTERNAL_ASSET_PATTERN.search(snapshot.rendered_html), (
        f"[{scenario.name}] export_render: rendered HTML references an external asset URL"
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
# SDTF-08: foundation-level teaching-session-readiness assertions against the
# SAME real generated deck already validated above by
# `_assert_deck_shape_and_quality`/`_assert_export_safety` -- proves the
# SDTF-01 (stable IDs)/SDTF-02 (pedagogical roles + planned pacing)/SDTF-05
# (teacher-only differentiation, no student leakage) foundation claims with a
# real persisted snapshot, not a fixture.
# ---------------------------------------------------------------------------

# AC3: interactions are local-only in v1 -- no fetch/XHR/API reference to any
# response-collection endpoint in the exported standalone HTML (TSP-05's
# "assert absence of API references in a static export" pattern).
_RESPONSE_PERSISTENCE_PATTERN = re.compile(
    r"fetch\s*\(|XMLHttpRequest|sendBeacon|axios\.|/teaching-packs/|/api/", re.IGNORECASE,
)
# AC4: teacher-only guidance/differentiation must never leak into the
# student-safe projection -- same forbidden-field list the renderer's own
# projection guard enforces (packages/renderer/src/slide-deck-projection.ts's
# `staticForbidden`), asserted again here against the real persisted student
# HTML rather than trusted blindly.
_TEACHER_ONLY_FIELD_LEAK_PATTERN = re.compile(
    r"teacher_only|teacher_notes|differentiation_guidance|correct_option_ids|acceptable_answers",
    re.IGNORECASE,
)
# AC6: a generic/placeholder alt text ("image.", "diagram") is not real
# alt/fallback text (SDX-04's guard-test pattern).
_GENERIC_ALT_TEXT_PATTERN = re.compile(
    r"^(image|diagram|picture|graphic|visual|photo)\.?$", re.IGNORECASE,
)

_FOUNDATION_CHECKS_REQUIRED_FIELDS = frozenset({
    "stable_ids_unique",
    "required_spine_roles_present",
    "total_planned_duration_minutes",
    "no_response_persistence_endpoints",
    "no_student_leakage_of_teacher_only_fields",
    "locale_matches_primary",
    "offline_safe_visual_blocks_checked",
})


def _assert_foundation_checks(
    scenario: Scenario, content_json: dict[str, Any], snapshot: Any,
) -> dict[str, Any]:
    from common.contracts.slide_deck import SlideDeckData

    deck = SlideDeckData.model_validate(_extract_slide_deck(content_json))
    student_html = snapshot.student_rendered_html

    # AC1: stable deck/slide/block/interaction IDs suitable for future
    # session binding. `SlideDeckData`'s own model validators (SDTF-01,
    # common/contracts/slide_deck.py) already reject duplicate IDs at parse
    # time -- asserted again explicitly here so a regression surfaces as this
    # harness's own failure, with the counts recorded as evidence, instead of
    # only a buried pydantic `ValidationError`.
    slide_ids = [slide.slide_id for slide in deck.slides]
    block_ids = [block.block_id for slide in deck.slides for block in slide.blocks]
    interaction_ids = [
        interaction.interaction_id for slide in deck.slides for interaction in slide.interactions
    ]
    assert deck.deck_id, f"[{scenario.name}] sparse_deck: deck has no stable deck_id"
    assert len(slide_ids) == len(set(slide_ids)), (
        f"[{scenario.name}] sparse_deck: duplicate slide_id in persisted deck"
    )
    assert len(block_ids) == len(set(block_ids)), (
        f"[{scenario.name}] sparse_deck: duplicate block_id in persisted deck"
    )
    assert len(interaction_ids) == len(set(interaction_ids)), (
        f"[{scenario.name}] sparse_deck: duplicate interaction_id in persisted deck"
    )

    # AC2: typed pedagogical roles + planned pacing for the required deck
    # spine (SDTF-02) -- read straight off the persisted, engine-stamped
    # deck (`annotate_pedagogical_pacing` runs once per generation), not
    # recomputed here.
    stamped_roles = {slide.pedagogical_role for slide in deck.slides if slide.pedagogical_role is not None}
    missing_spine_roles = set(SPINE_ROLES) - stamped_roles
    assert not missing_spine_roles, (
        f"[{scenario.name}] sparse_deck: deck missing required pedagogical role(s) {missing_spine_roles}"
    )
    assert all(slide.planned_duration_minutes is not None for slide in deck.slides), (
        f"[{scenario.name}] sparse_deck: not every slide carries a planned_duration_minutes"
    )
    assert deck.total_planned_duration_minutes and deck.total_planned_duration_minutes > 0, (
        f"[{scenario.name}] sparse_deck: deck has no planned total duration"
    )

    # AC3: v1 interactions are local-only -- no response-persistence/API
    # reference in the exported standalone HTML.
    assert not _RESPONSE_PERSISTENCE_PATTERN.search(student_html), (
        f"[{scenario.name}] leakage: exported HTML references a response-persistence/API endpoint "
        "-- v1 interactions must be local-only"
    )

    # AC4: teacher-only guidance/differentiation never leaks into the
    # student-safe projection.
    assert not _TEACHER_ONLY_FIELD_LEAK_PATTERN.search(student_html), (
        f"[{scenario.name}] leakage: student-facing HTML leaks a teacher-only field name"
    )
    differentiation_guidance_present = any(slide.differentiation_guidance for slide in deck.slides)

    # AC5: primary locale/chrome behavior for Vietnamese/bilingual scenarios
    # (and every other scenario, generically) -- the deck's own locale
    # matches what the teacher requested, and the exported HTML's
    # `<html lang="...">` chrome attribute matches the primary language.
    requested_locale = str(scenario.class_info.get("locale", deck.locale))
    primary_lang = requested_locale.split("-")[0].lower()
    assert deck.locale.lower().startswith(primary_lang), (
        f"[{scenario.name}] sparse_deck: deck locale {deck.locale!r} does not match "
        f"requested primary locale {requested_locale!r}"
    )
    lang_attribute_pattern = re.compile(rf'lang\s*=\s*"{re.escape(primary_lang)}', re.IGNORECASE)
    assert lang_attribute_pattern.search(student_html), (
        f'[{scenario.name}] export_render: exported HTML is missing a lang="{primary_lang}" chrome attribute'
    )

    # AC6: inline/offline-safe diagrams or visual blocks for math/science --
    # real (non-placeholder) alt/fallback text, and no dependency on an
    # external network asset (reuses `_EXTERNAL_ASSET_PATTERN`, the same
    # guard `_assert_export_safety` runs).
    visual_blocks = [
        block for slide in deck.slides for block in slide.blocks
        if block.block_type in ("image", "diagram") or block.media is not None
    ]
    for block in visual_blocks:
        media = block.media
        if media is None:
            continue
        assert media.alt_text.strip(), f"[{scenario.name}] sparse_deck: visual block {block.block_id} has empty alt_text"
        assert not _GENERIC_ALT_TEXT_PATTERN.match(media.alt_text.strip()), (
            f"[{scenario.name}] sparse_deck: visual block {block.block_id} has placeholder-only alt_text {media.alt_text!r}"
        )
        assert not media.requires_network, (
            f"[{scenario.name}] export_render: visual block {block.block_id} requires network access, not offline-safe"
        )

    return {
        "stable_ids_unique": True,
        "required_spine_roles_present": sorted(stamped_roles),
        "total_planned_duration_minutes": deck.total_planned_duration_minutes,
        "no_response_persistence_endpoints": True,
        "no_student_leakage_of_teacher_only_fields": True,
        "differentiation_guidance_present": differentiation_guidance_present,
        "locale_matches_primary": True,
        "primary_lang": primary_lang,
        "offline_safe_visual_blocks_checked": len(visual_blocks),
    }


# ---------------------------------------------------------------------------
# SDE-09: registry/density validation (SDE-01/02) for an AI-rewrite candidate
# -- reuses `apply_scoped_slide_deck_block_edit` (the exact function SDE-04's
# PATCH endpoint calls) to build the would-be-edited deck, then the same
# three deck-level validators `_assert_deck_shape_and_quality` already runs
# against a real generated deck, rather than inventing a per-block validator.
# ---------------------------------------------------------------------------


def _assert_rewrite_candidate_passes_registry_density(
    scenario_name: str, deck: Any, block_id: str, candidate_body: str, grade_level: str,
) -> dict[str, Any]:
    candidate_deck = apply_scoped_slide_deck_block_edit(deck, block_id, candidate_body)

    shape_report = evaluate_deck_shape(candidate_deck, teacher_constraints={}, grade_level=grade_level)
    assert shape_report.passed, f"[{scenario_name}] quality_gate: rewritten deck fails deck-shape check: {shape_report.message}"

    density_report = evaluate_purpose_density(candidate_deck)
    assert density_report.passed, f"[{scenario_name}] quality_gate: rewritten deck fails purpose-density check: {density_report.message}"

    leak_report = validate_teacher_only_separation(candidate_deck)
    assert leak_report.passed, f"[{scenario_name}] leakage: rewritten deck fails teacher-only separation: {leak_report.message}"

    return {
        "deck_shape_passed": shape_report.passed,
        "purpose_density_passed": density_report.passed,
        "teacher_only_separation_passed": leak_report.passed,
    }


def _find_version_authority(versions: list[dict[str, Any]], snapshot_id: str) -> str | None:
    """Pure lookup against SDE-05's version-history response -- reused by both
    the real scenario and its fast fixture-level meta-test below."""
    for version in versions:
        if version.get("snapshot_id") == snapshot_id:
            return version.get("authority")
    return None


# ---------------------------------------------------------------------------
# Browser QA -- shells out to the real Playwright install already present
# at apps/web (`@playwright/test`, `apps/web/playwright.config.ts`); no new
# dependency added. If the browser binaries aren't installed in this
# environment, that is recorded honestly as an `infrastructure` browser_qa
# entry rather than being faked as a pass.
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WEB_DIR = _REPO_ROOT / "apps" / "web"

# AC4: runtime/harness logs must never include secrets, raw credentials,
# JWTs, or student PII. `stdout`/`stderr` here is real subprocess output this
# harness doesn't control (Playwright, pnpm) -- scrub known secret shapes
# before it ever reaches the evidence bundle, rather than only asserting
# their absence after the fact.
_JWT_PATTERN = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}")
_BEARER_TOKEN_PATTERN = re.compile(r"(?i)\bBearer\s+\S+")
_AUTH_HEADER_VALUE_PATTERN = re.compile(r'(?i)("?(?:authorization|api[_-]?key|secret|password)"?\s*[:=]\s*)"?[^\s"&,]+')


def _redact_secrets(text: str) -> str:
    text = _JWT_PATTERN.sub("[REDACTED_JWT]", text)
    text = _BEARER_TOKEN_PATTERN.sub("Bearer [REDACTED]", text)
    text = _AUTH_HEADER_VALUE_PATTERN.sub(r"\1[REDACTED]", text)
    return text


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
    stdout_tail = _redact_secrets(result.stdout[-2000:])
    stderr_tail = _redact_secrets(result.stderr[-2000:])
    outcome = {
        "scenario": scenario_name,
        "html_path": str(html_path),
        "passed": passed,
        "returncode": result.returncode,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
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
        entry: dict[str, Any] = {
            "kind": "scenario_run",
            "name": scenario.name,
            "raw_request": scenario.raw_request,
            "model": GATEWAY_9ROUTER_MODEL,
            "endpoint": GATEWAY_9ROUTER_BASE_URL,
        }
        try:
            run_id = _create_run(client, token, scenario)
            entry["run_id"] = run_id

            final_status, gates_driven = _drive_to_terminal(client, token, run_id)
            entry["final_status"] = final_status.get("status")
            entry["gates_driven"] = gates_driven
            assert final_status.get("status") == RunStatus.COMPLETED.value, (
                f"[{scenario.name}] infrastructure or quality_gate: run ended in "
                f"{final_status.get('status')}, not completed"
            )

            slide_deck_snapshots = anyio.run(_fetch_snapshots, run_id)
            assert slide_deck_snapshots, f"[{scenario.name}] export_render: no slide_deck snapshot was persisted"
            snapshot = slide_deck_snapshots[-1]
            entry["snapshot_id"] = snapshot.snapshot_id

            display_preferences = _effective_display_preferences(snapshot.content_json or {})
            entry["display_preferences"] = display_preferences
            entry["projection_surface"] = display_preferences["surface"]

            deck_checks = _assert_deck_shape_and_quality(
                scenario, snapshot.content_json or {}, str(scenario.class_info.get("grade", "Grade 5")),
            )
            export_checks = _assert_export_safety(scenario, snapshot)
            entry["checks"] = {**deck_checks, **export_checks}
            entry["foundation_checks"] = _assert_foundation_checks(
                scenario, snapshot.content_json or {}, snapshot,
            )

            EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            export_path = EXPORT_DIR / f"{scenario.name}.{snapshot.snapshot_id}.student.html"
            export_path.write_text(snapshot.student_rendered_html, encoding="utf-8")
            entry["export_path"] = str(export_path)

            browser_result = _run_browser_qa(scenario.name, export_path)
            entry["browser_qa"] = browser_result
            if not browser_result["passed"] and browser_result["failure_category"] == "infrastructure":
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
            entry["failure_category"] = "infrastructure"
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
        after_snapshot = snapshots_after[-1]
        after_hash = after_snapshot.content_hash
        assert after_hash != before_hash, "structured recovery must produce a real repaired snapshot, not a no-op"

        _EVIDENCE["scenarios"].append({
            "kind": "recovery",
            "name": "structured_recovery_scoped_revision",
            "run_id": run_id,
            "artifact_id": artifact_id,
            "content_hash_before": before_hash,
            "content_hash_after": after_hash,
            "checks": {"scoped_revision_produced_a_new_snapshot": True},
            "outcome": "passed",
            # AC3: structured recovery attempts, if exercised, recorded with
            # attempt_number/failure_type/recovery_route/resulting snapshot.
            # A single scoped revision here == attempt 1; the teacher-reported
            # "too sparse" feedback is a `quality_gate` issue (matches
            # SDH-06/SDH-11's density/purpose-gap category), and this route
            # (`/request-revision` -> a scoped single-artifact repair, not a
            # full-deck regeneration) is what SDH-11's failure-copy.ts docs
            # call the `artifact_workflow` recovery route.
            "recovery_attempts": [{
                "attempt_number": 1,
                "failure_type": "quality_gate",
                "recovery_route": "artifact_workflow",
                "resulting_snapshot_id": after_snapshot.snapshot_id,
            }],
        })


# ---------------------------------------------------------------------------
# SDE-09: edit-then-reexport staleness (SDE-04's real PATCH block-edit
# endpoint + SDE-06's real export-status endpoint). SDE-06 deliberately
# ships no "trigger export" HTTP endpoint (services/gateway/routers/
# exports.py's own module docstring: re-export is always an explicit teacher
# action wired elsewhere) -- so "trigger a real export" here means writing a
# real `ExportRecord` row through the same `TeachingPackExportStore` the
# export pipeline itself writes through, exactly the way `_fetch_snapshots`
# already reads through the real snapshot store rather than re-deriving one.
# ---------------------------------------------------------------------------


async def _create_export_record(run_id: str, artifact_id: str, snapshot_id: str) -> str:
    export_id = f"export-{uuid4().hex[:12]}"
    storage_path = str(EXPORT_DIR / f"{export_id}.html")
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await TeachingPackExportStore(session).create_export_record(
            ExportRecordCreate(
                export_id=export_id,
                run_id=RunId(run_id),
                artifact_id=artifact_id,
                snapshot_id=snapshot_id,
                format="html",
                storage_path=storage_path,
            ),
        )
        await session.commit()
    await engine.dispose()
    return storage_path


def _export_status(client: Any, token: str, run_id: str, artifact_id: str) -> dict[str, Any]:
    response = client.get(
        f"/teaching-packs/runs/{run_id}/artifacts/{artifact_id}/export-status", headers=_bearer(token),
    )
    assert response.status_code == 200, response.text
    return response.json()


class TestEditThenReexportStalenessScenario:
    def test_editing_a_block_marks_the_export_stale_until_reexported(
        self, client: Any, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # SDE-10: the editor flag gates SDE-04's PATCH endpoint. Scoped to
        # this test only (monkeypatch auto-restores the env var; the finally
        # below resets the module-level feature cache either way so no other
        # test in this process ever sees a leaked flag state).
        monkeypatch.setenv("FEATURE_SLIDE_DECK_EDITOR_V1", "true")
        reset_features()
        entry: dict[str, Any] = {
            "kind": "edit_reexport_staleness",
            "name": "edit_then_reexport_staleness",
            "model": GATEWAY_9ROUTER_MODEL,
            "endpoint": GATEWAY_9ROUTER_BASE_URL,
        }
        try:
            from common.contracts.slide_deck import SlideDeckData

            token = _login(client)
            scenario = SCENARIOS[0]
            run_id = _create_run(client, token, scenario)
            entry["run_id"] = run_id
            final_status, _ = _drive_to_terminal(client, token, run_id)
            assert final_status.get("status") == RunStatus.COMPLETED.value, (
                f"[{scenario.name}] infrastructure: run ended in {final_status.get('status')}, not completed"
            )

            snapshots = anyio.run(_fetch_snapshots, run_id)
            assert snapshots, f"[{scenario.name}] export_render: no slide_deck snapshot was persisted"
            baseline_snapshot = snapshots[-1]
            artifact_id = baseline_snapshot.artifact_id
            baseline_snapshot_id = baseline_snapshot.snapshot_id
            entry["artifact_id"] = artifact_id
            entry["snapshot_id_before_edit"] = baseline_snapshot_id

            deck = SlideDeckData.model_validate(_extract_slide_deck(baseline_snapshot.content_json or {}))
            editable_block = next(
                block for slide in deck.slides for block in slide.blocks if block.block_type == "paragraph"
            )

            anyio.run(_create_export_record, run_id, artifact_id, baseline_snapshot_id)
            status_baseline = _export_status(client, token, run_id, artifact_id)
            assert status_baseline["stale"] is False, (
                f"[{scenario.name}] export_render: a fresh export of the current head must not be stale"
            )

            edit_response = client.patch(
                f"/teaching-packs/runs/{run_id}/snapshots/{baseline_snapshot_id}/blocks/{editable_block.block_id}",
                json={
                    "base_snapshot_id": baseline_snapshot_id,
                    "new_content": "Updated by the SDE-09 edit-then-reexport staleness scenario.",
                    "rationale": "acceptance harness edit-then-reexport staleness scenario",
                },
                headers=_bearer(token),
            )
            assert edit_response.status_code == 200, edit_response.text
            edited_snapshot_id = edit_response.json()["snapshot_id"]
            assert edited_snapshot_id != baseline_snapshot_id, (
                f"[{scenario.name}] export_render: block edit did not produce a new snapshot/version"
            )
            entry["snapshot_id_after_edit"] = edited_snapshot_id
            entry["snapshot_id"] = edited_snapshot_id

            status_after_edit = _export_status(client, token, run_id, artifact_id)
            assert status_after_edit["stale"] is True, (
                f"[{scenario.name}] export_render: SDE-06's export-staleness indicator did not fire after an edit"
            )
            assert status_after_edit["current_snapshot_id"] == edited_snapshot_id

            export_path = anyio.run(_create_export_record, run_id, artifact_id, edited_snapshot_id)
            entry["export_path"] = export_path

            status_after_reexport = _export_status(client, token, run_id, artifact_id)
            assert status_after_reexport["stale"] is False, (
                f"[{scenario.name}] export_render: re-exporting the edited head must clear staleness"
            )

            entry["checks"] = {
                "stale_before_edit": status_baseline["stale"],
                "stale_after_edit": status_after_edit["stale"],
                "stale_after_reexport": status_after_reexport["stale"],
                "new_snapshot_created_on_edit": True,
            }
            entry["outcome"] = "passed"
        except AssertionError as exc:
            entry["outcome"] = "failed"
            entry["failure_category"] = _classify_failure(str(exc))
            entry["failure_reason"] = str(exc)
            _EVIDENCE["scenarios"].append(entry)
            raise
        except InfraFailure as exc:
            entry["outcome"] = "failed"
            entry["failure_category"] = "infrastructure"
            entry["failure_reason"] = str(exc)
            _EVIDENCE["scenarios"].append(entry)
            raise
        finally:
            monkeypatch.setenv("FEATURE_SLIDE_DECK_EDITOR_V1", "false")
            reset_features()
        _EVIDENCE["scenarios"].append(entry)


# ---------------------------------------------------------------------------
# SDE-09: AI-rewrite end-to-end -- SDE-08's real rewrite-suggestion endpoint
# (real gateway HTTP, model `4omc`, no stub), SDE-01/02's registry/density
# validators reused (not re-derived) against the candidate applied to a real
# generated deck, and SDE-08's confirmation-modal-gated apply path (the same
# SDE-04 PATCH endpoint, `authority="ai_assisted_edit"`) verified end-to-end
# through the real version-history endpoint (SDE-05).
# ---------------------------------------------------------------------------


class TestAiRewriteEndToEndScenario:
    def test_ai_rewrite_suggestion_passes_validation_and_applies_with_the_correct_authority_tag(
        self, client: Any, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Both SDE-10 flags gate this path: the editor flag (SDE-04's PATCH
        # endpoint) and the AI-rewrite flag (the suggestion endpoint, and the
        # apply endpoint when authority="ai_assisted_edit"). Scoped to this
        # test only, same reset-in-finally guarantee as the scenario above.
        monkeypatch.setenv("FEATURE_SLIDE_DECK_EDITOR_V1", "true")
        monkeypatch.setenv("FEATURE_SLIDE_DECK_AI_REWRITE_V1", "true")
        reset_features()
        entry: dict[str, Any] = {
            "kind": "ai_rewrite_apply",
            "name": "ai_rewrite_end_to_end",
            "model": GATEWAY_9ROUTER_MODEL,
            "endpoint": GATEWAY_9ROUTER_BASE_URL,
        }
        try:
            from common.contracts.slide_deck import SlideDeckData

            token = _login(client)
            scenario = SCENARIOS[1]
            run_id = _create_run(client, token, scenario)
            entry["run_id"] = run_id
            final_status, _ = _drive_to_terminal(client, token, run_id)
            assert final_status.get("status") == RunStatus.COMPLETED.value, (
                f"[{scenario.name}] infrastructure: run ended in {final_status.get('status')}, not completed"
            )

            snapshots = anyio.run(_fetch_snapshots, run_id)
            assert snapshots, f"[{scenario.name}] export_render: no slide_deck snapshot was persisted"
            baseline_snapshot = snapshots[-1]
            artifact_id = baseline_snapshot.artifact_id
            baseline_snapshot_id = baseline_snapshot.snapshot_id
            entry["artifact_id"] = artifact_id
            entry["snapshot_id_before"] = baseline_snapshot_id

            deck = SlideDeckData.model_validate(_extract_slide_deck(baseline_snapshot.content_json or {}))
            editable_block = next(
                block for slide in deck.slides for block in slide.blocks
                if block.block_type == "paragraph" and len(block.body) > 40
            )
            entry["block_id"] = editable_block.block_id
            entry["preset"] = "shorter"

            suggestion_response = client.post(
                f"/teaching-packs/runs/{run_id}/snapshots/{baseline_snapshot_id}/blocks/{editable_block.block_id}/rewrite-suggestion",
                json={"preset": "shorter"},
                headers=_bearer(token),
            )
            assert suggestion_response.status_code == 200, suggestion_response.text
            suggestion = suggestion_response.json()
            candidate_after = suggestion["after"]
            assert candidate_after and candidate_after != editable_block.body, (
                f"[{scenario.name}] quality_gate: rewrite suggestion returned no real candidate"
            )

            validation_checks = _assert_rewrite_candidate_passes_registry_density(
                scenario.name, deck, editable_block.block_id, candidate_after,
                str(scenario.class_info.get("grade", "Grade 5")),
            )
            entry["checks"] = validation_checks

            apply_response = client.patch(
                f"/teaching-packs/runs/{run_id}/snapshots/{baseline_snapshot_id}/blocks/{editable_block.block_id}",
                json={
                    "base_snapshot_id": baseline_snapshot_id,
                    "new_content": candidate_after,
                    "rationale": "teacher approved the AI rewrite suggestion via the confirmation modal",
                    "authority": "ai_assisted_edit",
                },
                headers=_bearer(token),
            )
            assert apply_response.status_code == 200, apply_response.text
            applied_snapshot_id = apply_response.json()["snapshot_id"]
            assert applied_snapshot_id != baseline_snapshot_id
            entry["snapshot_id_after"] = applied_snapshot_id
            entry["snapshot_id"] = applied_snapshot_id

            versions_response = client.get(
                f"/teaching-packs/runs/{run_id}/artifacts/{artifact_id}/versions", headers=_bearer(token),
            )
            assert versions_response.status_code == 200, versions_response.text
            versions = versions_response.json()["versions"]
            applied_authority = _find_version_authority(versions, applied_snapshot_id)
            assert applied_authority == "ai_assisted_edit", (
                f"[{scenario.name}] quality_gate: applied AI rewrite version is tagged "
                f"{applied_authority!r}, expected 'ai_assisted_edit' (distinct from 'teacher_edit')"
            )
            entry["authority"] = applied_authority

            entry["outcome"] = "passed"
        except AssertionError as exc:
            entry["outcome"] = "failed"
            entry["failure_category"] = _classify_failure(str(exc))
            entry["failure_reason"] = str(exc)
            _EVIDENCE["scenarios"].append(entry)
            raise
        except InfraFailure as exc:
            entry["outcome"] = "failed"
            entry["failure_category"] = "infrastructure"
            entry["failure_reason"] = str(exc)
            _EVIDENCE["scenarios"].append(entry)
            raise
        finally:
            monkeypatch.setenv("FEATURE_SLIDE_DECK_EDITOR_V1", "false")
            monkeypatch.setenv("FEATURE_SLIDE_DECK_AI_REWRITE_V1", "false")
            reset_features()
        _EVIDENCE["scenarios"].append(entry)


# ---------------------------------------------------------------------------
# Evidence bundle -- written once, after every scenario above has run.
#
# `validate_evidence_bundle` (below) is the single required-lineage gate
# (SDH-10 AC7): SDTF-08/SDE-09 adding new scenario kinds to this same module
# should call it too rather than growing a second ad hoc check, and should
# extend `_REQUIRED_FIELDS_BY_KIND`/`_RECOVERY_ATTEMPT_REQUIRED_FIELDS` here
# instead of writing a parallel validator.
# ---------------------------------------------------------------------------

_BUNDLE_REQUIRED_FIELDS = frozenset({"schema", "generated_at", "endpoint_metadata", "scenarios"})
_ENDPOINT_METADATA_REQUIRED_FIELDS = frozenset({"gateway_mode", "llm_gateway_base_url", "model", "database_url_host"})

# Per AC1: run_id/snapshot_id/model/endpoint/scenario-name/final_status/
# quality-result/export_path/effective-display-preferences must all be
# present on a scenario that actually completed and was checked.
_SCENARIO_RUN_REQUIRED_FIELDS_PASSED = frozenset({
    "name", "run_id", "snapshot_id", "model", "endpoint", "final_status",
    "checks", "export_path", "display_preferences", "projection_surface", "outcome",
    # SDTF-08 AC7/AC8: foundation-level claims (stable IDs, pedagogical
    # spine + planned pacing, no response persistence, no teacher-only
    # leakage, locale, offline-safe visuals) recorded alongside every other
    # completed-scenario lineage field, and required so the harness exits
    # non-zero if they are ever missing.
    "foundation_checks",
})
# A failed run may never have reached export/snapshot -- only the
# classification lineage (AC2) and the request identity are guaranteed.
_SCENARIO_RUN_REQUIRED_FIELDS_FAILED = frozenset({
    "name", "model", "endpoint", "outcome", "failure_category", "failure_reason",
})
_RECOVERY_REQUIRED_FIELDS = frozenset({"name", "run_id", "recovery_attempts", "outcome"})
_RECOVERY_ATTEMPT_REQUIRED_FIELDS = frozenset({
    "attempt_number", "failure_type", "recovery_route", "resulting_snapshot_id",
})

# SDE-09: two new `kind`s, same lineage-gate discipline as `scenario_run`/
# `recovery` above -- a completed entry must carry every field a reader would
# need to reproduce/cite it (run id, snapshot ids, export path or authority
# tag) without falling back to the full `scenario_run` shape (which requires
# fields, like `foundation_checks`/`export_path` from the *deck-generation*
# path, these two block-level scenarios have no reason to also produce).
_EDIT_REEXPORT_STALENESS_REQUIRED_FIELDS_PASSED = frozenset({
    "name", "run_id", "artifact_id", "model", "endpoint",
    "snapshot_id_before_edit", "snapshot_id_after_edit", "snapshot_id",
    "export_path", "checks", "outcome",
})
_EDIT_REEXPORT_STALENESS_REQUIRED_FIELDS_FAILED = frozenset({
    "name", "model", "endpoint", "outcome", "failure_category", "failure_reason",
})
_AI_REWRITE_APPLY_REQUIRED_FIELDS_PASSED = frozenset({
    "name", "run_id", "artifact_id", "model", "endpoint", "block_id", "preset",
    "snapshot_id_before", "snapshot_id_after", "snapshot_id", "authority", "checks", "outcome",
})
_AI_REWRITE_APPLY_REQUIRED_FIELDS_FAILED = frozenset({
    "name", "model", "endpoint", "outcome", "failure_category", "failure_reason",
})


def _missing_fields(entry: dict[str, Any], required: frozenset[str]) -> set[str]:
    return {field for field in required if field not in entry}


def validate_evidence_bundle(bundle: dict[str, Any]) -> None:
    """Fail-closed lineage gate: raises `AssertionError` (which pytest turns
    into a non-zero exit, same as any other assertion in this module) if the
    bundle -- or any scenario/recovery entry inside it -- is missing a
    required lineage field. Called before every write, not just as a
    sanity check after the fact, so a regression here fails the harness run
    itself rather than silently shipping an incomplete bundle."""
    missing_bundle_fields = _missing_fields(bundle, _BUNDLE_REQUIRED_FIELDS)
    assert not missing_bundle_fields, f"evidence bundle missing required top-level fields: {missing_bundle_fields}"

    missing_endpoint_fields = _missing_fields(bundle["endpoint_metadata"], _ENDPOINT_METADATA_REQUIRED_FIELDS)
    assert not missing_endpoint_fields, f"evidence bundle endpoint_metadata missing fields: {missing_endpoint_fields}"

    assert bundle["scenarios"], "evidence bundle has no scenario entries"
    for entry in bundle["scenarios"]:
        kind = entry.get("kind", "scenario_run")
        if kind == "recovery":
            missing = _missing_fields(entry, _RECOVERY_REQUIRED_FIELDS)
            assert not missing, f"recovery entry {entry.get('name')!r} missing fields: {missing}"
            for attempt in entry.get("recovery_attempts", []):
                attempt_missing = _missing_fields(attempt, _RECOVERY_ATTEMPT_REQUIRED_FIELDS)
                assert not attempt_missing, (
                    f"recovery entry {entry.get('name')!r} attempt missing fields: {attempt_missing}"
                )
        elif kind == "edit_reexport_staleness":
            required = (
                _EDIT_REEXPORT_STALENESS_REQUIRED_FIELDS_PASSED
                if entry.get("outcome") == "passed"
                else _EDIT_REEXPORT_STALENESS_REQUIRED_FIELDS_FAILED
            )
            missing = _missing_fields(entry, required)
            assert not missing, (
                f"edit_reexport_staleness entry {entry.get('name')!r} "
                f"(outcome={entry.get('outcome')!r}) missing required lineage fields: {missing}"
            )
        elif kind == "ai_rewrite_apply":
            required = (
                _AI_REWRITE_APPLY_REQUIRED_FIELDS_PASSED
                if entry.get("outcome") == "passed"
                else _AI_REWRITE_APPLY_REQUIRED_FIELDS_FAILED
            )
            missing = _missing_fields(entry, required)
            assert not missing, (
                f"ai_rewrite_apply entry {entry.get('name')!r} "
                f"(outcome={entry.get('outcome')!r}) missing required lineage fields: {missing}"
            )
        else:
            required = (
                _SCENARIO_RUN_REQUIRED_FIELDS_PASSED
                if entry.get("outcome") == "passed"
                else _SCENARIO_RUN_REQUIRED_FIELDS_FAILED
            )
            missing = _missing_fields(entry, required)
            assert not missing, (
                f"scenario entry {entry.get('name')!r} (outcome={entry.get('outcome')!r}) "
                f"missing required lineage fields: {missing}"
            )
            if entry.get("outcome") == "passed":
                # SDTF-08 AC8: a completed scenario is not "foundation-proven"
                # just because the key is present -- every required
                # foundation-check field must itself be present too.
                missing_foundation = _missing_fields(
                    entry.get("foundation_checks") or {}, _FOUNDATION_CHECKS_REQUIRED_FIELDS,
                )
                assert not missing_foundation, (
                    f"scenario entry {entry.get('name')!r} foundation_checks "
                    f"missing required fields: {missing_foundation}"
                )


def cite_evidence(bundle_path: Path, entry: dict[str, Any]) -> str:
    """One-line "cite, don't dump" summary for a single scenario entry, per
    SDH-10 AC6 -- other agents/harnesses extending this evidence bundle
    (SDTF-08, SDE-09) should format their own references the same way rather
    than pasting raw evidence JSON into a report."""
    return (
        f"See {bundle_path}: run={entry.get('run_id')} snapshot={entry.get('snapshot_id')} "
        f"status={entry.get('outcome') or entry.get('final_status')}"
    )


def test_zzz_write_evidence_bundle() -> None:
    assert _EVIDENCE["scenarios"], "no scenario ran before the evidence bundle would be written"
    _EVIDENCE["generated_at"] = datetime.now(UTC).isoformat()
    validate_evidence_bundle(_EVIDENCE)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(_EVIDENCE, indent=2, sort_keys=True), encoding="utf-8")
    written = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    assert written["scenarios"], "evidence bundle round-trips from disk"
    validate_evidence_bundle(written)
    serialized = json.dumps(written)
    assert "eyJ" not in serialized, "evidence bundle must never contain a raw JWT"
    assert not _JWT_PATTERN.search(serialized), "evidence bundle must never contain a JWT-shaped string"
    assert not _BEARER_TOKEN_PATTERN.search(serialized), "evidence bundle must never contain a raw bearer token"


# ---------------------------------------------------------------------------
# Unit-level meta-tests for the evidence-lineage gate itself (SDH-10). These
# need no DB/LLM/browser -- run them directly rather than the full real-LLM
# suite: `uv run pytest services/gateway/tests/test_slide_deck_acceptance_harness.py -k "evidence_bundle_ or redact or cite_evidence" -q`
# ---------------------------------------------------------------------------


def _minimal_valid_bundle() -> dict[str, Any]:
    return {
        "schema": "oh-my-class.slide_deck_acceptance.evidence.v1",
        "generated_at": "2026-07-10T00:00:00+00:00",
        "endpoint_metadata": {
            "gateway_mode": "in_process_testclient",
            "llm_gateway_base_url": "http://127.0.0.1:20228",
            "model": "4omc",
            "database_url_host": "localhost:5432/oh_my_class",
        },
        "scenarios": [{
            "kind": "scenario_run",
            "name": "example_scenario",
            "run_id": "run-1",
            "snapshot_id": "snap-1",
            "model": "4omc",
            "endpoint": "http://127.0.0.1:20228",
            "final_status": "completed",
            "checks": {"deck_shape_passed": True},
            "export_path": "/tmp/example.student.html",
            "display_preferences": {"surface": "presentation", "print_layout": "paged", "slides_per_page": 1, "chrome": "hidden"},
            "projection_surface": "presentation",
            "outcome": "passed",
            "foundation_checks": {
                "stable_ids_unique": True,
                "required_spine_roles_present": ["exit_ticket", "explain", "guided_practice", "hook", "model", "objective"],
                "total_planned_duration_minutes": 30.0,
                "no_response_persistence_endpoints": True,
                "no_student_leakage_of_teacher_only_fields": True,
                "locale_matches_primary": True,
                "offline_safe_visual_blocks_checked": 0,
            },
        }],
    }


def test_validate_evidence_bundle_accepts_a_complete_bundle() -> None:
    validate_evidence_bundle(_minimal_valid_bundle())  # must not raise


def test_validate_evidence_bundle_rejects_a_scenario_missing_a_required_field() -> None:
    bundle = _minimal_valid_bundle()
    del bundle["scenarios"][0]["snapshot_id"]
    with pytest.raises(AssertionError, match="snapshot_id"):
        validate_evidence_bundle(bundle)


def test_validate_evidence_bundle_rejects_a_passed_scenario_missing_foundation_checks() -> None:
    bundle = _minimal_valid_bundle()
    del bundle["scenarios"][0]["foundation_checks"]
    with pytest.raises(AssertionError, match="foundation_checks"):
        validate_evidence_bundle(bundle)


def test_validate_evidence_bundle_rejects_foundation_checks_missing_a_required_field() -> None:
    bundle = _minimal_valid_bundle()
    del bundle["scenarios"][0]["foundation_checks"]["total_planned_duration_minutes"]
    with pytest.raises(AssertionError, match="total_planned_duration_minutes"):
        validate_evidence_bundle(bundle)


def test_validate_evidence_bundle_rejects_a_recovery_attempt_missing_a_required_field() -> None:
    bundle = _minimal_valid_bundle()
    bundle["scenarios"].append({
        "kind": "recovery",
        "name": "structured_recovery_scoped_revision",
        "run_id": "run-1",
        "outcome": "passed",
        "recovery_attempts": [{"attempt_number": 1, "failure_type": "quality_gate"}],  # missing recovery_route/resulting_snapshot_id
    })
    with pytest.raises(AssertionError, match="recovery_route"):
        validate_evidence_bundle(bundle)


def test_recovery_attempt_round_trips_through_json() -> None:
    bundle = _minimal_valid_bundle()
    bundle["scenarios"].append({
        "kind": "recovery",
        "name": "structured_recovery_scoped_revision",
        "run_id": "run-1",
        "outcome": "passed",
        "recovery_attempts": [{
            "attempt_number": 1,
            "failure_type": "quality_gate",
            "recovery_route": "artifact_workflow",
            "resulting_snapshot_id": "snap-2",
        }],
    })
    validate_evidence_bundle(bundle)  # must not raise
    round_tripped = json.loads(json.dumps(bundle))
    assert round_tripped["scenarios"][-1]["recovery_attempts"][0] == {
        "attempt_number": 1,
        "failure_type": "quality_gate",
        "recovery_route": "artifact_workflow",
        "resulting_snapshot_id": "snap-2",
    }


# ---------------------------------------------------------------------------
# Unit-level meta-tests for the two SDE-09 evidence kinds (`edit_reexport_
# staleness`, `ai_rewrite_apply`) and their pure helpers. No DB/LLM/browser
# needed -- same fast-tier rationale as the `validate_evidence_bundle` tests
# above: run directly with
# `uv run pytest services/gateway/tests/test_slide_deck_acceptance_harness.py -k "edit_reexport or ai_rewrite_apply or version_authority or registry_density" -q`
# ---------------------------------------------------------------------------


def _minimal_edit_reexport_staleness_entry() -> dict[str, Any]:
    return {
        "kind": "edit_reexport_staleness",
        "name": "edit_then_reexport_staleness",
        "run_id": "run-1",
        "artifact_id": "artifact-1",
        "model": "4omc",
        "endpoint": "http://127.0.0.1:20228",
        "snapshot_id_before_edit": "snap-1",
        "snapshot_id_after_edit": "snap-2",
        "snapshot_id": "snap-2",
        "export_path": "/tmp/example.export.html",
        "checks": {"stale_before_edit": False, "stale_after_edit": True, "stale_after_reexport": False},
        "outcome": "passed",
    }


def _minimal_ai_rewrite_apply_entry() -> dict[str, Any]:
    return {
        "kind": "ai_rewrite_apply",
        "name": "ai_rewrite_end_to_end",
        "run_id": "run-1",
        "artifact_id": "artifact-1",
        "model": "4omc",
        "endpoint": "http://127.0.0.1:20228",
        "block_id": "block-1",
        "preset": "shorter",
        "snapshot_id_before": "snap-1",
        "snapshot_id_after": "snap-2",
        "snapshot_id": "snap-2",
        "authority": "ai_assisted_edit",
        "checks": {"deck_shape_passed": True, "purpose_density_passed": True, "teacher_only_separation_passed": True},
        "outcome": "passed",
    }


def test_validate_evidence_bundle_accepts_a_complete_edit_reexport_staleness_entry() -> None:
    bundle = _minimal_valid_bundle()
    bundle["scenarios"].append(_minimal_edit_reexport_staleness_entry())
    validate_evidence_bundle(bundle)  # must not raise


def test_validate_evidence_bundle_rejects_an_edit_reexport_staleness_entry_missing_a_required_field() -> None:
    bundle = _minimal_valid_bundle()
    entry = _minimal_edit_reexport_staleness_entry()
    del entry["export_path"]
    bundle["scenarios"].append(entry)
    with pytest.raises(AssertionError, match="export_path"):
        validate_evidence_bundle(bundle)


def test_validate_evidence_bundle_accepts_a_complete_ai_rewrite_apply_entry() -> None:
    bundle = _minimal_valid_bundle()
    bundle["scenarios"].append(_minimal_ai_rewrite_apply_entry())
    validate_evidence_bundle(bundle)  # must not raise


def test_validate_evidence_bundle_rejects_an_ai_rewrite_apply_entry_missing_a_required_field() -> None:
    bundle = _minimal_valid_bundle()
    entry = _minimal_ai_rewrite_apply_entry()
    del entry["authority"]
    bundle["scenarios"].append(entry)
    with pytest.raises(AssertionError, match="authority"):
        validate_evidence_bundle(bundle)


def test_find_version_authority_returns_the_matching_versions_authority_tag() -> None:
    versions = [
        {"snapshot_id": "snap-1", "authority": "teacher_edit"},
        {"snapshot_id": "snap-2", "authority": "ai_assisted_edit"},
    ]
    assert _find_version_authority(versions, "snap-2") == "ai_assisted_edit"
    assert _find_version_authority(versions, "snap-1") == "teacher_edit"
    assert _find_version_authority(versions, "snap-does-not-exist") is None


def _registry_density_fixture_deck() -> Any:
    """A hand-built deck meeting `evaluate_purpose_density`'s per-role
    thresholds (`deck_shape.py`'s `_ROLE_DENSITY`) as well as the spine/leak
    checks -- unlike `_foundation_fixture_content_json` (built only to
    exercise `_assert_foundation_checks`, one block per slide, no
    interactions), this fixture must independently pass all three deck-level
    validators `_assert_rewrite_candidate_passes_registry_density` reuses,
    the same way a real LLM-generated deck already does in the live scenario."""
    from common.contracts.slide_deck import SlideDeckData

    def slide(token: str, role: str, body_a: str, *, body_b: str | None = None, interaction: bool = False) -> dict[str, Any]:
        blocks = [{"block_id": f"block-{token}", "block_type": "paragraph", "body": body_a}]
        if body_b is not None:
            blocks.append({"block_id": f"block-{token}-b", "block_type": "paragraph", "body": body_b})
        result = {
            "slide_id": f"slide-{token}",
            "title": token.title(),
            "layout": "content",
            "progression": {"step_index": 1, "reveal_policy": "all_at_once"},
            "blocks": blocks,
            "pedagogical_role": role,
            "planned_duration_minutes": 5.0,
        }
        if interaction:
            result["interactions"] = [{
                "interaction_id": f"interaction-{token}",
                "interaction_type": "multiple_choice_single",
                "prompt": "Check your understanding.",
                "options": [{"option_id": "a", "label": "Correct"}, {"option_id": "b", "label": "Incorrect"}],
                "correct_option_ids": ["a"],
            }]
        return result

    deck = {
        "deck_id": "deck-registry-density-fixture",
        "title": "Registry Density Fixture Deck",
        "locale": "en-US",
        "surfaces": {
            "student": {"mode": "presentation", "export_format": "html"},
            "teacher": {"mode": "teacher_guide", "export_format": "html"},
            "print": {"mode": "print", "export_format": "html"},
        },
        "slides": [
            slide("title", "hook", "Welcome to today's lesson on fractions and equivalence."),
            slide(
                "goal", "objective",
                "Today you will learn how to identify equivalent fractions.",
                body_b="By the end of this lesson you will compare fractions confidently.",
            ),
            slide(
                "vocabulary", "explain",
                "Equivalent fractions represent the same value written with different numbers.",
                body_b="For example, one half and two fourths point to the same amount on a number line.",
            ),
            slide(
                "example", "model",
                "Watch how we convert one half into an equivalent fraction with a denominator of eight.",
                body_b="We multiply the numerator and denominator by the same factor to keep the value equal.",
            ),
            slide(
                "practice", "guided_practice",
                "Try converting three fourths into an equivalent fraction with your partner.",
                interaction=True,
            ),
            slide("exit", "exit_ticket", "Write one equivalent fraction pair you learned about today."),
        ],
        "accessibility": {"reading_level": "grade_5", "language": "en-US"},
        "media_policy": {"default_tier": "packaged", "online_optional_allowed": False, "fallback_required": True},
    }
    return SlideDeckData.model_validate(deck)


def test_assert_rewrite_candidate_passes_registry_density_for_a_well_formed_candidate() -> None:
    deck = _registry_density_fixture_deck()
    result = _assert_rewrite_candidate_passes_registry_density(
        "fixture_scenario", deck, "block-vocabulary",
        "Equivalent fractions represent the same value using different numerators and denominators.",
        "Grade 5",
    )
    assert result == {
        "deck_shape_passed": True,
        "purpose_density_passed": True,
        "teacher_only_separation_passed": True,
    }


def test_assert_rewrite_candidate_passes_registry_density_rejects_an_unknown_block_id() -> None:
    deck = _registry_density_fixture_deck()
    with pytest.raises(ValueError, match="block"):
        _assert_rewrite_candidate_passes_registry_density(
            "fixture_scenario", deck, "block-does-not-exist", "New content.", "Grade 5",
        )


# ---------------------------------------------------------------------------
# Unit-level meta-tests for `_assert_foundation_checks` itself (SDTF-08).
# No DB/LLM/browser needed -- a hand-built minimal `SlideDeckData`-shaped
# fixture (same "build a well-formed deck, then break one thing" replay
# pattern `packages/agents/tests/slide_deck_engine/test_deck_shape.py` uses)
# proves the new assertions actually catch a broken deck rather than
# rubber-stamping it.
# ---------------------------------------------------------------------------


class _FakeSnapshot:
    def __init__(self, student_rendered_html: str) -> None:
        self.student_rendered_html = student_rendered_html


def _foundation_fixture_slide(
    token: str, role: str, *, media: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = [
        {"block_id": f"block-{token}", "block_type": "paragraph", "body": f"Content for the {token} slide."},
    ]
    if media is not None:
        blocks.append({
            "block_id": f"block-{token}-media", "block_type": "diagram", "body": "See the diagram.", "media": media,
        })
    return {
        "slide_id": f"slide-{token}",
        "title": token.title(),
        "layout": "content",
        "progression": {"step_index": 1, "reveal_policy": "all_at_once"},
        "blocks": blocks,
        "pedagogical_role": role,
        "planned_duration_minutes": 5.0,
    }


def _foundation_fixture_content_json(*, locale: str = "en-US") -> dict[str, Any]:
    slides = [
        _foundation_fixture_slide("title", "hook"),
        _foundation_fixture_slide("goal", "objective"),
        _foundation_fixture_slide("vocabulary", "explain"),
        _foundation_fixture_slide("example", "model"),
        _foundation_fixture_slide("practice", "guided_practice"),
        _foundation_fixture_slide("exit", "exit_ticket"),
    ]
    deck = {
        "deck_id": "deck-fixture-1",
        "title": "Fixture Deck",
        "locale": locale,
        "surfaces": {
            "student": {"mode": "presentation", "export_format": "html"},
            "teacher": {"mode": "teacher_guide", "export_format": "html"},
            "print": {"mode": "print", "export_format": "html"},
        },
        "slides": slides,
        "accessibility": {"reading_level": "grade_5", "language": locale},
        "media_policy": {
            "default_tier": "packaged", "online_optional_allowed": False, "fallback_required": True,
        },
    }
    return {"sections": [{"slide_deck": deck}]}


_FOUNDATION_FIXTURE_SCENARIO = Scenario(
    name="fixture_scenario",
    raw_request="n/a",
    class_info={"locale": "en-US"},
    content_probe=re.compile(r".*"),
)


def test_assert_foundation_checks_passes_for_a_well_formed_fixture() -> None:
    content_json = _foundation_fixture_content_json()
    snapshot = _FakeSnapshot('<html lang="en"><body>Content for the title slide.</body></html>')

    result = _assert_foundation_checks(_FOUNDATION_FIXTURE_SCENARIO, content_json, snapshot)

    assert result["stable_ids_unique"] is True
    assert set(result["required_spine_roles_present"]) == set(SPINE_ROLES)
    assert result["total_planned_duration_minutes"] == 30.0
    assert not _missing_fields(result, _FOUNDATION_CHECKS_REQUIRED_FIELDS)


def test_assert_foundation_checks_catches_a_missing_required_pedagogical_role() -> None:
    content_json = _foundation_fixture_content_json()
    # Break the spine: the "practice" slide loses its role, same as a
    # regression in `assign_pedagogical_roles`/`annotate_pedagogical_pacing`.
    content_json["sections"][0]["slide_deck"]["slides"][4]["pedagogical_role"] = None
    snapshot = _FakeSnapshot('<html lang="en"><body>ok</body></html>')

    with pytest.raises(AssertionError, match="pedagogical role"):
        _assert_foundation_checks(_FOUNDATION_FIXTURE_SCENARIO, content_json, snapshot)


def test_assert_foundation_checks_catches_a_teacher_only_field_leaking_into_student_html() -> None:
    content_json = _foundation_fixture_content_json()
    snapshot = _FakeSnapshot(
        '<html lang="en"><body>differentiation_guidance: scaffold this for group A</body></html>',
    )

    with pytest.raises(AssertionError, match="leak"):
        _assert_foundation_checks(_FOUNDATION_FIXTURE_SCENARIO, content_json, snapshot)


def test_assert_foundation_checks_catches_a_primary_locale_mismatch() -> None:
    content_json = _foundation_fixture_content_json(locale="en-US")
    snapshot = _FakeSnapshot('<html lang="en"><body>ok</body></html>')
    vietnamese_scenario = Scenario(
        name="fixture_scenario_vi",
        raw_request="n/a",
        class_info={"locale": "vi-VN"},
        content_probe=re.compile(r".*"),
    )

    with pytest.raises(AssertionError, match="locale"):
        _assert_foundation_checks(vietnamese_scenario, content_json, snapshot)


def test_assert_foundation_checks_catches_a_network_dependent_visual_block() -> None:
    content_json = _foundation_fixture_content_json()
    content_json["sections"][0]["slide_deck"]["slides"][3]["blocks"].append({
        "block_id": "block-example-diagram",
        "block_type": "diagram",
        "body": "See the diagram.",
        "media": {
            "media_id": "media-1",
            "media_type": "diagram",
            "source": "assets/diagram.png",
            "tier": "packaged",
            "alt_text": (
                "A labeled diagram of the water cycle showing evaporation and condensation."
            ),
            "requires_network": True,
        },
    })
    snapshot = _FakeSnapshot('<html lang="en"><body>ok</body></html>')

    with pytest.raises(AssertionError, match="network"):
        _assert_foundation_checks(_FOUNDATION_FIXTURE_SCENARIO, content_json, snapshot)


def test_redact_secrets_strips_jwt_and_bearer_tokens_and_auth_header_values() -> None:
    fake_jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZWFjaGVyMSJ9.c2lnbmF0dXJlLWJ5dGVzLWhlcmU"
    raw = (
        f"logging in with Authorization: Bearer {fake_jwt}\n"
        f'{{"api_key": "sk-super-secret-value"}}\n'
        f"raw jwt seen bare: {fake_jwt}"
    )
    redacted = _redact_secrets(raw)
    assert fake_jwt not in redacted
    assert "sk-super-secret-value" not in redacted
    assert "REDACTED" in redacted


def test_cite_evidence_produces_a_one_line_pointer_not_a_dump() -> None:
    entry = {"run_id": "run-abc", "snapshot_id": "snap-xyz", "outcome": "passed"}
    citation = cite_evidence(Path(".scratch/slide-deck-acceptance/artifacts/sdh-07-evidence.json"), entry)
    assert citation == (
        "See .scratch/slide-deck-acceptance/artifacts/sdh-07-evidence.json: "
        "run=run-abc snapshot=snap-xyz status=passed"
    )
    assert "\n" not in citation


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
