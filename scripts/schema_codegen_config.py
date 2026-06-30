from __future__ import annotations

from typing import TypedDict


class ModelConfig(TypedDict):
    main_model: str
    all_models: list[str]
    output: str
    field_refs: dict[str, str]
    external_field_refs: dict[str, str]


MODELS: dict[str, ModelConfig] = {
    "common.contracts.lesson_plan": {
        "main_model": "LessonPlan",
        "all_models": [
            "LessonPlan",
            "LearningObjective",
            "AssessmentCheckpoint",
            "MethodologyPayloads",
            "MethodologyMetadata",
        ],
        "output": "common/schemas/src/generated/lesson_plan.ts",
        "field_refs": {
            "learning_objectives": "LearningObjective",
            "assessment_checkpoints": "AssessmentCheckpoint",
            "methodology": "MethodologyMetadata",
            "payloads": "MethodologyPayloads",
        },
        "external_field_refs": {
            "inverse_thinking": "InverseThinkingPackSchema:./inverse_thinking.js",
        },
    },
    "common.contracts.artifact": {
        "main_model": "TeachingPack",
        "all_models": ["ArtifactContent", "TeachingPack"],
        "output": "common/schemas/src/generated/artifact.ts",
        "field_refs": {"artifacts": "ArtifactContent"},
        "external_field_refs": {},
    },
    "common.contracts.judge_output": {
        "main_model": "JudgeOutput",
        "all_models": ["JudgeOutput", "LayerScore"],
        "output": "common/schemas/src/generated/judge_output.ts",
        "field_refs": {"layer_scores": "LayerScore"},
        "external_field_refs": {},
    },
    "common.contracts.run_contract": {
        "main_model": "RunContract",
        "all_models": [
            "RunContract",
            "ContractRevisionMeta",
            "DecompositionIntent",
            "ContractRevision",
        ],
        "output": "common/schemas/src/generated/run_contract.ts",
        "field_refs": {
            "revision_meta": "ContractRevisionMeta",
            "decomposition_intent": "DecompositionIntent",
            "contract": "RunContract",
        },
        "external_field_refs": {},
    },
    "common.contracts.lesson_sequence": {
        "main_model": "LessonSequence",
        "all_models": ["LessonSequence", "SessionPlan", "KnowledgeComponent", "PrerequisiteEdge"],
        "output": "common/schemas/src/generated/lesson_sequence.ts",
        "field_refs": {
            "sessions": "SessionPlan",
            "knowledge_components": "KnowledgeComponent",
            "prerequisite_edges": "PrerequisiteEdge",
        },
        "external_field_refs": {},
    },
    "common.contracts.class_profile": {
        "main_model": "ClassProfile",
        "all_models": [
            "ClassProfile",
            "LearningPreferences",
            "StudentProfile",
            "LearningStyle",
            "PersonalityTrait",
        ],
        "output": "common/schemas/src/generated/class_profile.ts",
        "field_refs": {
            "learning_preferences": "LearningPreferences",
            "students": "StudentProfile",
            "learning_style": "LearningStyle",
            "personality_traits": "PersonalityTrait",
        },
        "external_field_refs": {},
    },
    "common.contracts.unit_view": {
        "main_model": "UnitView",
        "all_models": [
            "UnitView",
            "UnitParentMeta",
            "UnitSessionProgress",
            "UnitAggregate",
            "UnitCoherenceWarning",
            "UnitSessionStatusEvent",
            "UnitAggregateEvent",
            "UnitCoherenceWarningEvent",
            "UnitEventEnvelope",
        ],
        "output": "common/schemas/src/generated/unit_view.ts",
        "field_refs": {
            "parent": "UnitParentMeta",
            "sessions": "UnitSessionProgress",
            "aggregate": "UnitAggregate",
            "coherence_warnings": "UnitCoherenceWarning",
            "session": "UnitSessionProgress",
            "warning": "UnitCoherenceWarning",
            "payload": "UnitSessionStatusEvent",
        },
        "external_field_refs": {"sequence": "LessonSequenceSchema:./lesson_sequence.js"},
    },
    "common.contracts.inverse_thinking": {
        "main_model": "InverseThinkingPack",
        "all_models": [
            "InverseThinkingPack",
            "InverseThinkingTeacherOnly",
            "InverseThinkingCase",
            "InverseThinkingSummaryRow",
            "InverseThinkingStudentChallenge",
        ],
        "output": "common/schemas/src/generated/inverse_thinking.ts",
        "field_refs": {
            "cases": "InverseThinkingCase",
            "summary_table": "InverseThinkingSummaryRow",
            "student_challenges": "InverseThinkingStudentChallenge",
            "teacher_only": "InverseThinkingTeacherOnly",
        },
        "external_field_refs": {},
    },
    "common.contracts.errors": {
        "main_model": "ErrorResponse",
        "all_models": [
            "ErrorResponse",
            "ValidationErrorDetail",
            "PipelineErrorResponse",
        ],
        "output": "common/schemas/src/generated/errors.ts",
        "field_refs": {"details": "ValidationErrorDetail"},
        "external_field_refs": {},
    },
    "common.contracts.quality": {
        "main_model": "ArtifactQualityReport",
        "all_models": [
            "ArtifactQualityReport",
            "QualityIssue",
            "HealingDecision",
            "ExportReadinessReport",
        ],
        "output": "common/schemas/src/generated/quality.ts",
        "field_refs": {"issues": "QualityIssue"},
        "external_field_refs": {},
    },
    "common.contracts.research_brief": {
        "main_model": "ResearchBrief",
        "all_models": [
            "ResearchBrief",
            "EvidenceCitation",
            "ArtifactResearchGuidance",
            "PrePlanningSearchBrief",
        ],
        "output": "common/schemas/src/generated/research_brief.ts",
        "field_refs": {
            "citations": "EvidenceCitation",
            "artifact_guidance": "ArtifactResearchGuidance",
        },
        "external_field_refs": {},
    },
    "common.contracts.artifact_workflow": {
        "main_model": "ArtifactWorkflowState",
        "all_models": [
            "ArtifactWorkflowState",
            "ArtifactGenerationInput",
        ],
        "output": "common/schemas/src/generated/artifact_workflow.ts",
        "field_refs": {},
        "external_field_refs": {
            "contract": "RunContractSchema:./run_contract.js",
            "research_brief": "ResearchBriefSchema:./research_brief.js",
            "research_guidance": "ArtifactResearchGuidanceSchema:./research_brief.js",
        },
    },
}
