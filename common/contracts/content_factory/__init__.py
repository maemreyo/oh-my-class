"""Content Factory V2 cross-package contracts."""

from common.contracts.content_factory.assessment import (
    AssessmentItemBlueprint,
    AssessmentVerificationError,
    build_item_blueprints,
    validate_question_card,
)
from common.contracts.content_factory.coherence import (
    PackCoherenceFinding,
    PackCoherenceReport,
    evaluate_pack_coherence,
)
from common.contracts.content_factory.instructional_design import (
    InstructionalDesignPlan,
    LessonPhasePlan,
    build_instructional_design_plan,
)
from common.contracts.content_factory.orchestration import (
    ContentBriefAssemblyError,
    GenerationBudget,
    OrchestratorRequest,
    OrchestratorResult,
    build_content_brief,
    request_from_payload,
)
from common.contracts.content_factory.synthesis import (
    PrerequisiteCycleError,
    SynthesisClaim,
    SynthesisPlan,
    build_synthesis_plan,
    prerequisite_order,
    visual_semantics,
)
from common.contracts.content_factory.tenancy import (
    TenantAccessDeniedError,
    TenantContext,
    personal_tenant_context,
    privacy_safe_metadata,
)

__all__ = [
    "AssessmentItemBlueprint",
    "AssessmentVerificationError",
    "ContentBriefAssemblyError",
    "GenerationBudget",
    "InstructionalDesignPlan",
    "LessonPhasePlan",
    "OrchestratorRequest",
    "OrchestratorResult",
    "PackCoherenceFinding",
    "PackCoherenceReport",
    "PrerequisiteCycleError",
    "SynthesisClaim",
    "SynthesisPlan",
    "TenantAccessDeniedError",
    "TenantContext",
    "build_content_brief",
    "build_instructional_design_plan",
    "build_item_blueprints",
    "build_synthesis_plan",
    "evaluate_pack_coherence",
    "personal_tenant_context",
    "prerequisite_order",
    "privacy_safe_metadata",
    "request_from_payload",
    "validate_question_card",
    "visual_semantics",
]
