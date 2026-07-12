"""#464: joint specialist-capability + curriculum-coverage resolution,
tested against the real capability-pack fixtures (not synthetic data)."""

from __future__ import annotations

from pathlib import Path

import pytest

from common.contracts.grade_band import GradeBand
from common.contracts.subject_capability_pack import SubjectCapabilityPack, load_subject_capability_pack
from packages.agents.teaching_pack.content_coverage_resolution import resolve_content_coverage

_CAPABILITIES_DIR = (
    Path(__file__).resolve().parents[4] / "common" / "component_strategy_knowledge" / "capabilities"
)


@pytest.fixture(scope="module")
def math_pack() -> SubjectCapabilityPack:
    return load_subject_capability_pack(_CAPABILITIES_DIR / "math_capability_pack.json")


def test_supported_artifact_type_certified_by_the_pack_is_fully_supported(math_pack: SubjectCapabilityPack) -> None:
    # math_capability_pack.json certifies "quiz" for grades_3_5.
    resolution = resolve_content_coverage(
        "quiz",
        subject="math",
        grade_band=GradeBand.GRADES_3_5,
        generic_fallback_enabled=False,
        capability_packs={"math": math_pack},
    )

    assert resolution.status == "supported"
    assert resolution.specialist_resolution.status == "supported"
    assert resolution.coverage_policy_note is None


def test_supported_artifact_type_not_certified_for_this_band_degrades(math_pack: SubjectCapabilityPack) -> None:
    # "worksheet" is not certified for k_2 in math_capability_pack.json
    # (only quiz/drill are), even though the worksheet specialist exists.
    resolution = resolve_content_coverage(
        "worksheet",
        subject="math",
        grade_band=GradeBand.K_2,
        generic_fallback_enabled=False,
        capability_packs={"math": math_pack},
    )

    assert resolution.status == "degraded"
    assert resolution.specialist_resolution.status == "supported"
    assert resolution.coverage_policy_note is not None
    assert "worksheet" in resolution.coverage_policy_note
    assert "quiz" in resolution.coverage_policy_note  # names what IS certified


def test_missing_capability_pack_for_subject_degrades_not_blocks() -> None:
    resolution = resolve_content_coverage(
        "quiz",
        subject="art",
        grade_band=GradeBand.GRADES_3_5,
        generic_fallback_enabled=False,
        capability_packs={},
    )

    assert resolution.status == "degraded"
    assert resolution.specialist_resolution.status == "supported"
    assert "art" in resolution.coverage_policy_note


def test_unsupported_artifact_type_is_unsupported_regardless_of_coverage(math_pack: SubjectCapabilityPack) -> None:
    resolution = resolve_content_coverage(
        "no-such-artifact-type",
        subject="math",
        grade_band=GradeBand.GRADES_3_5,
        generic_fallback_enabled=False,
        capability_packs={"math": math_pack},
    )

    assert resolution.status == "unsupported"
    assert resolution.specialist_resolution.status == "unsupported"
    assert resolution.coverage_policy_note is None


def test_unsupported_artifact_type_can_degrade_via_generic_fallback_flag(math_pack: SubjectCapabilityPack) -> None:
    resolution = resolve_content_coverage(
        "no-such-artifact-type",
        subject="math",
        grade_band=GradeBand.GRADES_3_5,
        generic_fallback_enabled=True,
        capability_packs={"math": math_pack},
    )

    # Flag-enabled reach for an undeclared type: the specialist resolution
    # itself degrades (never "unsupported"), and there's no certified
    # coverage for a type the pack doesn't even declare -- still "degraded"
    # overall, never silently "supported".
    assert resolution.status == "degraded"
    assert resolution.specialist_resolution.status == "degraded"


def test_all_four_real_capability_packs_load_and_resolve_without_error() -> None:
    for fixture_name in (
        "math_capability_pack.json",
        "science_capability_pack.json",
        "humanities_capability_pack.json",
        "language_literacy_capability_pack.json",
    ):
        pack = load_subject_capability_pack(_CAPABILITIES_DIR / fixture_name)
        for grade_band in GradeBand:
            coverage = pack.coverage_for(grade_band)
            for artifact_type in coverage.artifact_families:
                resolution = resolve_content_coverage(
                    artifact_type,
                    subject=pack.subject,
                    grade_band=grade_band,
                    generic_fallback_enabled=False,
                    capability_packs={pack.subject: pack},
                )
                assert resolution.status == "supported", (
                    f"{pack.subject}/{grade_band.value}/{artifact_type} expected supported, "
                    f"got {resolution.status}: {resolution.coverage_policy_note}"
                )


def test_registered_artifact_types_not_declared_by_any_pack_degrade_for_every_pack() -> None:
    """The negative-space half of the registry matrix: a specialist that
    exists in code (e.g. `lesson`, `flashcard_deck` -- registered but not
    certified by any of the four subject packs today) must never resolve
    `supported` just because the code can generate it. Walks every real
    pack x every grade band x every SPECIALIST_REGISTRY-declared type that
    pack's coverage does NOT list, asserting each one degrades with a
    `coverage_policy_note` naming the gap."""
    from packages.agents.teaching_pack.specialist_registry import SPECIALIST_REGISTRY

    fixture_names = (
        "math_capability_pack.json",
        "science_capability_pack.json",
        "humanities_capability_pack.json",
        "language_literacy_capability_pack.json",
    )
    checked = 0
    for fixture_name in fixture_names:
        pack = load_subject_capability_pack(_CAPABILITIES_DIR / fixture_name)
        for grade_band in GradeBand:
            coverage = pack.coverage_for(grade_band)
            uncertified_types = set(SPECIALIST_REGISTRY) - set(coverage.artifact_families)
            assert uncertified_types, "expected at least one registered-but-uncertified type per band"
            for artifact_type in uncertified_types:
                checked += 1
                resolution = resolve_content_coverage(
                    artifact_type,
                    subject=pack.subject,
                    grade_band=grade_band,
                    generic_fallback_enabled=False,
                    capability_packs={pack.subject: pack},
                )
                assert resolution.status == "degraded", (
                    f"{pack.subject}/{grade_band.value}/{artifact_type} expected degraded "
                    f"(uncertified), got {resolution.status}"
                )
                assert resolution.coverage_policy_note is not None
    assert checked > 0
