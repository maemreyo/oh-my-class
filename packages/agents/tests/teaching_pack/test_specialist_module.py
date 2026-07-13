from __future__ import annotations

import pytest

from common.contracts.education_policy import ArtifactKind, SubjectKey
from common.contracts.grade_band import GradeBand
from packages.agents.teaching_pack.specialist_capability import (
    NATIVELY_DISPATCHED_ARTIFACT_TYPES,
    resolve_specialist_capability,
)
from packages.agents.teaching_pack.specialist_module import (
    SPECIALIST_MODULES,
    NativelyDispatchedModuleError,
    SpecialistRequest,
    get_specialist_module,
)
from packages.agents.teaching_pack.specialist_registry import SPECIALIST_REGISTRY


def test_every_canonical_artifact_kind_has_a_registered_module() -> None:
    """Registry-matrix test: no ArtifactKind is undeclared, no module is
    orphaned -- mirrors specialist_capability's own matrix test so the two
    can never silently diverge."""
    canonical = {kind.value for kind in ArtifactKind}
    assert set(SPECIALIST_MODULES) == canonical


@pytest.mark.parametrize("artifact_type", sorted(SPECIALIST_MODULES))
def test_every_module_declares_the_full_subject_grade_language_matrix(artifact_type: str) -> None:
    """No specialist branches on subject, grade band, or language today --
    declaring anything narrower would be a false capability claim."""
    declaration = SPECIALIST_MODULES[artifact_type].declaration

    assert set(declaration.subjects) == {key.value for key in SubjectKey}
    assert set(declaration.grade_bands) == {band.value for band in GradeBand}
    assert set(declaration.languages) == {"en", "vi"}
    expected_criteria = {"format_compliance", "content_quality", "presentation"}
    assert set(declaration.quality_criteria) == expected_criteria


def test_module_declaration_payload_kind_matches_capability_declaration() -> None:
    """Parity with specialist_capability.py's own SSOT -- no drift between
    the two declaration surfaces."""
    from packages.agents.teaching_pack.specialist_capability import capability_declaration_for

    for artifact_type, module in SPECIALIST_MODULES.items():
        expected = capability_declaration_for(artifact_type).payload_kind
        assert module.declaration.payload_kind == expected


def test_registered_specialist_module_dispatches_to_the_real_registry_callable() -> None:
    module = get_specialist_module("lesson")
    assert module is not None
    request = SpecialistRequest(
        artifact_type="lesson",
        lesson_plan={
            "topic": "Fractions",
            "grade_level": "Grade 5",
            "learning_objectives": [{"description": "Students understand fractions"}],
        },
        research_brief={"key_findings": [], "sources": []},
    )

    via_module = module.generate(request)
    via_registry = SPECIALIST_REGISTRY["lesson"](request.lesson_plan, request.research_brief)

    assert via_module["artifact_type"] == via_registry["artifact_type"] == "lesson"


@pytest.mark.parametrize("artifact_type", sorted(NATIVELY_DISPATCHED_ARTIFACT_TYPES))
def test_natively_dispatched_modules_refuse_uniform_dispatch(artifact_type: str) -> None:
    """`answer_key` and `slide_deck` have their own dedicated dispatch branch
    in generate_one_artifact.py -- calling them through the uniform
    SpecialistModule.generate entry point must fail closed, not silently
    return something wrong."""
    module = get_specialist_module(artifact_type)
    assert module is not None
    request = SpecialistRequest(artifact_type=artifact_type, lesson_plan={}, research_brief={})

    with pytest.raises(NativelyDispatchedModuleError):
        module.generate(request)


def test_lineage_carries_the_resolved_specialist_id_and_declared_brief_fields() -> None:
    module = get_specialist_module("quiz")
    assert module is not None
    resolution = resolve_specialist_capability("quiz", generic_fallback_enabled=False)

    lineage = module.lineage(resolution)

    assert lineage.artifact_type == "quiz"
    assert lineage.specialist_id == "registry:quiz"
    assert lineage.module_version == "v2"
    assert lineage.consumed_content_brief_fields == module.declaration.consumed_content_brief_fields
    assert lineage.consumed_content_brief_fields
