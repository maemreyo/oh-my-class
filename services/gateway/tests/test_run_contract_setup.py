from __future__ import annotations

from services.gateway.run_contract_setup import (
    DEFAULT_POLICY,
    ContractSetupGate,
    ContractSetupInput,
    ContractSetupReady,
    resolve_contract_setup,
)
from services.gateway.teaching_pack_types import RunId, TeacherId


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

    def test_unsupported_artifact_opens_clarification_gate_when_pptx_is_supported(self) -> None:
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

    def test_slide_deck_request_creates_slide_deck_contract(self) -> None:
        result = resolve_contract_setup(ContractSetupInput(
            run_id=RunId("run-slide-deck"),
            teacher_id=TeacherId("teacher-a"),
            raw_request="Generate a slide deck for Grade 5 English ESL food vocabulary.",
            class_info={"grade": 5, "subject": "English"},
        ))

        assert isinstance(result, ContractSetupGate)
        assert result.gate_name == "contract_confirmation"
        assert result.contract is not None
        assert result.contract.topic == "Grade 5 English ESL food vocabulary"
        assert result.contract.artifact_types == ["slide_deck"]
        assert result.payload["inferred_fields"] == [
            {
                "field": "topic",
                "value": "Grade 5 English ESL food vocabulary",
                "reason": "inferred_from_request",
            },
            {
                "field": "curriculum",
                "value": "English ESL",
                "reason": "locale_default",
            },
        ]

    def test_required_source_conflict_opens_source_conflict_gate_before_generation(self) -> None:
        result = resolve_contract_setup(ContractSetupInput(
            run_id=RunId("run-conflict"),
            teacher_id=TeacherId("teacher-a"),
            raw_request="Fractions",
            class_info={
                "topic": "Fractions",
                "grade": 5,
                "subject": "science",
                "source_collection": {
                    "collection_id": "sources-1",
                    "scope": "private_teacher",
                    "owner_id": "teacher-a",
                    "entries": [{
                        "entry_id": "entry-1",
                        "title": "District science handbook",
                        "authority": "required",
                        "subject_key": "boiling_point_water_celsius",
                        "claim_value": "100",
                    }],
                },
                "verified_findings": [{
                    "subject_key": "boiling_point_water_celsius",
                    "claim_value": "90",
                    "source_id": "src-verified-1",
                    "verification_status": "VERIFIED",
                }],
            },
        ))

        assert isinstance(result, ContractSetupGate)
        assert result.gate_name == "source_conflict"
        assert result.contract is not None
        assert result.payload["conflicts"] == [{
            "entry_id": "entry-1",
            "subject_key": "boiling_point_water_celsius",
            "required_claim_value": "100",
            "verified_claim_value": "90",
            "verified_source_id": "src-verified-1",
        }]

    def test_source_collection_without_conflict_does_not_open_source_conflict_gate(self) -> None:
        result = resolve_contract_setup(ContractSetupInput(
            run_id=RunId("run-no-conflict"),
            teacher_id=TeacherId("teacher-a"),
            raw_request="Fractions",
            class_info={
                "topic": "Fractions",
                "grade": 5,
                "subject": "science",
                "source_collection": {
                    "collection_id": "sources-1",
                    "scope": "private_teacher",
                    "owner_id": "teacher-a",
                    "entries": [{
                        "entry_id": "entry-1",
                        "title": "District science handbook",
                        "authority": "required",
                        "subject_key": "boiling_point_water_celsius",
                        "claim_value": "100",
                    }],
                },
            },
        ))

        assert isinstance(result, ContractSetupReady)

    def test_all_renderable_artifact_types_are_requestable(self) -> None:
        result = resolve_contract_setup(ContractSetupInput(
            run_id=RunId("run-full-artifacts"),
            teacher_id=TeacherId("teacher-a"),
            raw_request="Fractions",
            class_info={
                "topic": "Fractions",
                "grade": 5,
                "subject": "math",
                "artifact_types": [
                    "lesson",
                    "worksheet",
                    "quiz",
                    "drill",
                    "recap",
                    "infographic",
                    "flashcard_deck",
                    "answer_key",
                    "roadmap",
                    "slide_deck",
                ],
            },
        ))

        assert isinstance(result, ContractSetupReady)
        assert result.contract.artifact_types == [
            "lesson",
            "worksheet",
            "quiz",
            "drill",
            "recap",
            "infographic",
            "flashcard_deck",
            "answer_key",
            "roadmap",
            "slide_deck",
        ]

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

    def test_long_inferred_topic_is_capped_to_contract_limit(self) -> None:
        result = resolve_contract_setup(ContractSetupInput(
            run_id=RunId("run-long-topic"),
            teacher_id=TeacherId("teacher-a"),
            raw_request=(
                "Teach Grade 5 English ESL food vocabulary with lesson quiz worksheet "
                "teacher-only answer key student preview export evidence and additional "
                "instructions that exceed the topic schema limit by a wide margin. "
                "Include a recap artifact, content approval previews, standalone HTML export, "
                "release evidence, and no answer-key leakage in the student-facing preview."
            ),
            class_info={"grade": 5, "subject": "English"},
        ))

        assert isinstance(result, ContractSetupGate)
        assert result.contract is not None
        assert len(result.contract.topic) <= 200

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
