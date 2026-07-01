from __future__ import annotations

from common.contracts.run_contract import ContractRevisionMeta, DecompositionIntent, RunContract


def _revision() -> ContractRevisionMeta:
    return ContractRevisionMeta(
        revision=1,
        actor="system",
        source="code_defaults",
        reason="test contract",
        effective_stage="setup_contract",
    )


def _contract(mode: str = "generate_pack") -> RunContract:
    return RunContract(
        contract_id="contract-1",
        run_id="run-1",
        teacher_id="teacher-1",
        mode=mode,
        topic="Fractions",
        grade_band="Grade 5",
        subject="math",
        locale="vi-VN",
        instruction_language="vi",
        citation_locale="vi-VN",
        artifact_types=["lesson"],
        export_formats=["html"],
        config_version="v1",
        config_hash="a" * 64,
        revision_meta=_revision(),
    )


def test_plan_unit_mode_and_decomposition_intent_parse_when_unit_planning() -> None:
    contract = RunContract(
        **{
            **_contract("plan_unit").model_dump(),
            "decomposition_intent": DecompositionIntent(
                target_sessions=6,
                session_length_minutes=45,
                source="teacher",
                rationale="Teacher requested a six-session unit.",
            ).model_dump(),
        }
    )

    assert contract.mode == "plan_unit"
    assert contract.decomposition_intent is not None
    assert contract.decomposition_intent.target_sessions == 6
    assert contract.decomposition_intent.rationale == "Teacher requested a six-session unit."


def test_existing_modes_parse_unchanged_when_decomposition_intent_is_absent() -> None:
    generate_pack = _contract("generate_pack")
    diagnose = _contract("diagnose_then_generate")

    assert generate_pack.decomposition_intent is None
    assert diagnose.decomposition_intent is None


def test_vocabulary_batch_mode_parses_without_new_artifact_type() -> None:
    contract = _contract("vocabulary_batch")

    assert contract.mode == "vocabulary_batch"
    assert contract.artifact_types == ["lesson"]
