from __future__ import annotations

from services.gateway.teaching_pack_types import RunId, TeacherId
from services.gateway.run_contract_setup import (
    DEFAULT_POLICY,
    ContractSetupGate,
    ContractSetupInput,
    ContractSetupReady,
    resolve_contract_setup,
)


class TestTeachingPackContractSetup:
    def test_missing_required_fields_open_clarification_gate(self) -> None:
        result = resolve_contract_setup(ContractSetupInput(
            run_id=RunId("run-a"),
            teacher_id=TeacherId("teacher-a"),
            raw_request="",
            class_info={},
        ))

        assert isinstance(result, ContractSetupGate)
        assert result.gate_name == "clarification_required"
        assert result.payload["missing_fields"] == [
            "raw_request",
            "topic",
            "grade_band",
            "subject",
        ]

    def test_unsupported_artifact_and_export_open_clarification_gate(self) -> None:
        result = resolve_contract_setup(ContractSetupInput(
            run_id=RunId("run-unsupported"),
            teacher_id=TeacherId("teacher-a"),
            raw_request="Fractions",
            class_info={
                "topic": "Fractions",
                "grade": 5,
                "subject": "math",
                "artifact_types": ["slides"],
                "export_formats": ["pptx"],
            },
        ))

        assert isinstance(result, ContractSetupGate)
        assert result.gate_name == "clarification_required"
        assert result.payload["unsupported_values"] == [
            {"field": "artifact_types", "value": "slides"},
            {"field": "export_formats", "value": "pptx"},
        ]

    def test_safe_defaults_create_runnable_contract_without_gate(self) -> None:
        result = resolve_contract_setup(ContractSetupInput(
            run_id=RunId("run-b"),
            teacher_id=TeacherId("teacher-a"),
            raw_request="Fractions",
            class_info={"topic": "Fractions", "grade": 5, "subject": "math"},
        ))

        assert isinstance(result, ContractSetupReady)
        assert result.contract.artifact_types == DEFAULT_POLICY["artifact_types"]
        assert result.contract.export_formats == ["html"]
        assert len(result.contract.config_hash) == 64

    def test_risky_inferred_topic_opens_contract_confirmation(self) -> None:
        result = resolve_contract_setup(ContractSetupInput(
            run_id=RunId("run-c"),
            teacher_id=TeacherId("teacher-a"),
            raw_request="Teach fractions",
            class_info={"grade": 5, "subject": "math"},
        ))

        assert isinstance(result, ContractSetupGate)
        assert result.gate_name == "contract_confirmation"
        assert result.contract is not None
        assert result.payload["inferred_fields"][0]["field"] == "topic"

    def test_diagnosis_mode_requires_evidence_and_minimizes_pii(self) -> None:
        missing = resolve_contract_setup(ContractSetupInput(
            run_id=RunId("run-d"),
            teacher_id=TeacherId("teacher-a"),
            raw_request="Fractions",
            class_info={
                "topic": "Fractions",
                "grade": 5,
                "subject": "math",
                "mode": "diagnose_then_generate",
            },
        ))
        ready = resolve_contract_setup(ContractSetupInput(
            run_id=RunId("run-e"),
            teacher_id=TeacherId("teacher-a"),
            raw_request="Fractions",
            class_info={
                "topic": "Fractions",
                "grade": 5,
                "subject": "math",
                "mode": "diagnose_then_generate",
                "student_evidence": {"name": "A", "misconceptions": ["equivalent fractions"]},
            },
        ))

        assert isinstance(missing, ContractSetupGate)
        assert "student_evidence" in missing.payload["missing_fields"]
        assert isinstance(ready, ContractSetupReady)
        assert ready.contract.student_evidence == {"misconceptions": ["equivalent fractions"]}

    def test_curriculum_defaults_only_for_known_high_impact_contexts(self) -> None:
        vietnam_math = resolve_contract_setup(ContractSetupInput(
            run_id=RunId("run-f"),
            teacher_id=TeacherId("teacher-a"),
            raw_request="Phân số",
            class_info={"topic": "Phân số", "grade": 5, "subject": "math", "locale": "vi-VN"},
        ))
        unknown = resolve_contract_setup(ContractSetupInput(
            run_id=RunId("run-g"),
            teacher_id=TeacherId("teacher-a"),
            raw_request="Rocks",
            class_info={"topic": "Rocks", "grade": 5, "subject": "science", "locale": "fr-FR"},
        ))

        assert isinstance(vietnam_math, ContractSetupGate)
        assert vietnam_math.contract is not None
        assert vietnam_math.contract.curriculum == "BGDĐT Việt Nam"
        assert isinstance(unknown, ContractSetupReady)
        assert unknown.contract.curriculum is None
