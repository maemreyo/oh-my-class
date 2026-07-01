from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from packages.agents.middleware.base import BaseMiddleware

from packages.agents.middleware.context.deferred_tool_filter import DeferredToolFilterMiddleware
from packages.agents.middleware.context.dynamic_context import DynamicContextMiddleware
from packages.agents.middleware.context.memory import MemoryMiddleware
from packages.agents.middleware.context.skill_activation import SkillActivationMiddleware
from packages.agents.middleware.context.summarization import SummarizationMiddleware
from packages.agents.middleware.context.system_message_coalescing import (
    SystemMessageCoalescingMiddleware,
)
from packages.agents.middleware.context.title import TitleMiddleware
from packages.agents.middleware.context.todo_list import TodoListMiddleware
from packages.agents.middleware.context.token_usage import TokenUsageMiddleware
from packages.agents.middleware.context.view_image import ViewImageMiddleware
from packages.agents.middleware.quality.artifact_coherence import ArtifactCoherenceMiddleware
from packages.agents.middleware.quality.bias_detection import BiasDetectionMiddleware
from packages.agents.middleware.quality.curriculum_alignment import CurriculumAlignmentMiddleware
from packages.agents.middleware.quality.learning_objective_alignment import (
    LearningObjectiveAlignmentMiddleware,
)
from packages.agents.middleware.quality.pedagogical_quality import PedagogicalQualityMiddleware
from packages.agents.middleware.quality.readability_level import ReadabilityLevelMiddleware
from packages.agents.middleware.quality.subagent_limit import SubagentLimitMiddleware
from packages.agents.middleware.safety.content_safety import ContentSafetyMiddleware
from packages.agents.middleware.safety.dangling_tool_call import DanglingToolCallMiddleware
from packages.agents.middleware.safety.guardrail import GuardrailMiddleware
from packages.agents.middleware.safety.input_sanitization import InputSanitizationMiddleware
from packages.agents.middleware.safety.llm_error_handling import LLMErrorHandlingMiddleware
from packages.agents.middleware.safety.loop_detection import LoopDetectionMiddleware
from packages.agents.middleware.safety.safety_finish_reason import SafetyFinishReasonMiddleware
from packages.agents.middleware.safety.teacher_audit_log import TeacherAuditLogMiddleware
from packages.agents.middleware.safety.thread_data import ThreadDataMiddleware
from packages.agents.middleware.safety.token_budget import TokenBudgetMiddleware
from packages.agents.middleware.safety.tool_error_handling import ToolErrorHandlingMiddleware
from packages.agents.middleware.safety.uploads import UploadsMiddleware
from packages.agents.middleware.sequence_consistency_validator import SequenceConsistencyValidator
from packages.agents.middleware.terminal.clarification import ClarificationMiddleware

ORDERED_MIDDLEWARE_LIST: list[type[BaseMiddleware]] = [
    InputSanitizationMiddleware,
    TokenBudgetMiddleware,
    ThreadDataMiddleware,
    UploadsMiddleware,
    ContentSafetyMiddleware,
    DanglingToolCallMiddleware,
    LLMErrorHandlingMiddleware,
    GuardrailMiddleware,
    TeacherAuditLogMiddleware,
    ToolErrorHandlingMiddleware,
    LoopDetectionMiddleware,
    SafetyFinishReasonMiddleware,
    DynamicContextMiddleware,
    SkillActivationMiddleware,
    SummarizationMiddleware,
    TodoListMiddleware,
    TokenUsageMiddleware,
    TitleMiddleware,
    MemoryMiddleware,
    ViewImageMiddleware,
    DeferredToolFilterMiddleware,
    SystemMessageCoalescingMiddleware,
    SubagentLimitMiddleware,
    CurriculumAlignmentMiddleware,
    ReadabilityLevelMiddleware,
    PedagogicalQualityMiddleware,
    BiasDetectionMiddleware,
    ArtifactCoherenceMiddleware,
    LearningObjectiveAlignmentMiddleware,
    SequenceConsistencyValidator,
    ClarificationMiddleware,
]

EXPECTED_MIDDLEWARE_COUNT: int = 31

RUN_ENTRY_MIDDLEWARE: tuple[type[BaseMiddleware], ...] = (
    InputSanitizationMiddleware,
    UploadsMiddleware,
    ThreadDataMiddleware,
    TitleMiddleware,
    MemoryMiddleware,
    TokenBudgetMiddleware,
)

GENERATION_CONTEXT_MIDDLEWARE: dict[str, tuple[type[BaseMiddleware], ...]] = {
    "planner": (DynamicContextMiddleware, SkillActivationMiddleware),
    "content_creator": (DynamicContextMiddleware, SkillActivationMiddleware),
}

GATE_LAYER_MIDDLEWARE: tuple[type[BaseMiddleware], ...] = (
    TeacherAuditLogMiddleware,
    ClarificationMiddleware,
)

QUALITY_GATE_CONSOLIDATED_MIDDLEWARE: tuple[type[BaseMiddleware], ...] = (
    CurriculumAlignmentMiddleware,
    ReadabilityLevelMiddleware,
    PedagogicalQualityMiddleware,
    BiasDetectionMiddleware,
    ArtifactCoherenceMiddleware,
    LearningObjectiveAlignmentMiddleware,
)

PARKED_REACT_MIDDLEWARE: dict[type[BaseMiddleware], str] = {
    DanglingToolCallMiddleware: "ReAct tool-call recovery only; teaching-pack stages do not use tools directly.",
    ToolErrorHandlingMiddleware: "ReAct tool-call error handling only; deterministic stages fail through typed paths.",
    LoopDetectionMiddleware: "Conversational loop detection only; teaching-pack graph has bounded conditional edges.",
    SubagentLimitMiddleware: "ReAct subagent fan-out only; teaching-pack fan-out uses explicit graph limits.",
    DeferredToolFilterMiddleware: "ReAct tool filtering only; deterministic stages have no deferred tool list.",
    SummarizationMiddleware: "Conversational context compression only; stage seams use typed state.",
    TodoListMiddleware: "Conversational planning aid only; teaching-pack progress is graph state.",
    ViewImageMiddleware: "Image-view tool accounting only; uploads are handled at run entry.",
}

ACTIVE_MIDDLEWARE: tuple[type[BaseMiddleware], ...] = (
    *RUN_ENTRY_MIDDLEWARE,
    *GENERATION_CONTEXT_MIDDLEWARE["planner"],
    *GATE_LAYER_MIDDLEWARE,
)
