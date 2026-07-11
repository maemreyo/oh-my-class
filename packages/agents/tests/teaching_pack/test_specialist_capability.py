from __future__ import annotations

from common.contracts.education_policy import ArtifactKind
from packages.agents.teaching_pack.specialist_capability import (
    ANSWER_SET_ARTIFACT_TYPES,
    NATIVELY_DISPATCHED_ARTIFACT_TYPES,
    SPECIALIST_CAPABILITIES,
    SPECIALIST_FAMILIES,
    capability_declaration_for,
    family_for,
    resolve_specialist_capability,
)
from packages.agents.teaching_pack.specialist_registry import SPECIALIST_REGISTRY


def test_registered_specialist_type_resolves_supported() -> None:
    resolution = resolve_specialist_capability("quiz", generic_fallback_enabled=False)

    assert resolution.status == "supported"
    assert resolution.specialist_id == "registry:quiz"
    assert resolution.supported_alternatives == ()


def test_natively_dispatched_type_resolves_supported() -> None:
    resolution = resolve_specialist_capability("slide_deck", generic_fallback_enabled=False)

    assert resolution.status == "supported"
    assert resolution.specialist_id == "native:slide_deck"


def test_undeclared_type_resolves_unsupported_by_default() -> None:
    resolution = resolve_specialist_capability("an_undeclared_type", generic_fallback_enabled=False)

    assert resolution.status == "unsupported"
    assert resolution.specialist_id is None
    assert resolution.policy_note is None
    expected = tuple(sorted({*SPECIALIST_REGISTRY, *NATIVELY_DISPATCHED_ARTIFACT_TYPES}))
    assert resolution.supported_alternatives == expected


def test_undeclared_type_resolves_degraded_with_explicit_policy_when_flag_enabled() -> None:
    resolution = resolve_specialist_capability("an_undeclared_type", generic_fallback_enabled=True)

    assert resolution.status == "degraded"
    assert resolution.policy_note is not None
    assert "experimental" in resolution.policy_note
    assert resolution.supported_alternatives != ()


def test_every_canonical_artifact_kind_has_a_capability_declaration() -> None:
    """#464 registry-matrix test: every ArtifactKind must have a declared
    capability -- no natively-dispatched or registered specialist is
    undeclared, and no declaration is orphaned (references a retired type)."""
    canonical = {kind.value for kind in ArtifactKind}
    declared = set(SPECIALIST_CAPABILITIES)

    assert declared == canonical, f"declaration set diverges from ArtifactKind: {declared.symmetric_difference(canonical)}"
    assert declared == {*SPECIALIST_REGISTRY, *NATIVELY_DISPATCHED_ARTIFACT_TYPES}


def test_answer_bearing_declaration_matches_the_real_answer_set_derivation_set() -> None:
    """Cross-check against generate_one_artifact's own SSOT -- a declaration
    can't silently drift from the code path it describes."""
    for artifact_type in ANSWER_SET_ARTIFACT_TYPES:
        assert capability_declaration_for(artifact_type).answer_bearing is True

    non_answer_set_types = set(SPECIALIST_CAPABILITIES) - ANSWER_SET_ARTIFACT_TYPES - {"slide_deck"}
    for artifact_type in non_answer_set_types:
        assert capability_declaration_for(artifact_type).answer_bearing is False


def test_assessment_payload_kind_matches_the_projection_mapper_dispatch_set() -> None:
    """Cross-check against artifact_projection_mapper's own SSOT for which
    types produce an assessment_document payload."""
    from common.contracts.artifact_projection_mapper import _ASSESSMENT_TYPES

    for artifact_type, declaration in SPECIALIST_CAPABILITIES.items():
        if artifact_type in _ASSESSMENT_TYPES:
            assert declaration.payload_kind == "assessment_document"
        elif artifact_type == "slide_deck":
            assert declaration.payload_kind == "slide_deck_document"
        else:
            assert declaration.payload_kind == "rich_document"


def test_every_capability_declaration_has_exactly_one_specialist_family() -> None:
    """#464: 'Register five specialist families' -- every declared artifact
    type belongs to exactly one of ADR-053's five named families."""
    assert set(SPECIALIST_FAMILIES) == set(SPECIALIST_CAPABILITIES)
    assert {family_for(artifact_type) for artifact_type in SPECIALIST_CAPABILITIES} == {
        "lesson_design", "assessment", "practice", "synthesis", "presentation",
    }


def test_specialist_families_match_adr_053_grouping() -> None:
    """Transcribed directly from ADR-053's 'Five Artifact Specialist
    families' decision section -- pin it so drift is caught."""
    assert family_for("lesson") == "lesson_design"
    assert {artifact_type for artifact_type, family in SPECIALIST_FAMILIES.items() if family == "assessment"} == {
        "quiz", "exit_ticket", "answer_key",
    }
    assert {artifact_type for artifact_type, family in SPECIALIST_FAMILIES.items() if family == "practice"} == {
        "worksheet", "drill", "flashcard_deck",
    }
    assert {artifact_type for artifact_type, family in SPECIALIST_FAMILIES.items() if family == "synthesis"} == {
        "recap", "infographic", "roadmap", "reading_passage",
    }
    assert {artifact_type for artifact_type, family in SPECIALIST_FAMILIES.items() if family == "presentation"} == {
        "slide_deck",
    }
