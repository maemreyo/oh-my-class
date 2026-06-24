"""Middleware registry — canonical ordered list of all 30 pipeline middleware layers.

Import from this module to get the complete, ordered middleware chain.
The list is ordered by `order` attribute (1–30). ClarificationMiddleware
MUST always be last (order=30).

Do NOT reorder entries without updating all references.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from packages.agents.middleware.base import BaseMiddleware

from packages.agents.middleware.safety.input_sanitization import InputSanitizationMiddleware
from packages.agents.middleware.safety.token_budget import TokenBudgetMiddleware
from packages.agents.middleware.safety.thread_data import ThreadDataMiddleware
from packages.agents.middleware.safety.uploads import UploadsMiddleware
from packages.agents.middleware.safety.content_safety import ContentSafetyMiddleware
from packages.agents.middleware.safety.dangling_tool_call import DanglingToolCallMiddleware
from packages.agents.middleware.safety.llm_error_handling import LLMErrorHandlingMiddleware
from packages.agents.middleware.safety.guardrail import GuardrailMiddleware
from packages.agents.middleware.safety.teacher_audit_log import TeacherAuditLogMiddleware
from packages.agents.middleware.safety.tool_error_handling import ToolErrorHandlingMiddleware
from packages.agents.middleware.safety.loop_detection import LoopDetectionMiddleware
from packages.agents.middleware.safety.safety_finish_reason import SafetyFinishReasonMiddleware
from packages.agents.middleware.context.dynamic_context import DynamicContextMiddleware
from packages.agents.middleware.context.skill_activation import SkillActivationMiddleware
from packages.agents.middleware.context.summarization import SummarizationMiddleware
from packages.agents.middleware.context.todo_list import TodoListMiddleware
from packages.agents.middleware.context.token_usage import TokenUsageMiddleware
from packages.agents.middleware.context.title import TitleMiddleware
from packages.agents.middleware.context.memory import MemoryMiddleware
from packages.agents.middleware.context.view_image import ViewImageMiddleware
from packages.agents.middleware.context.deferred_tool_filter import DeferredToolFilterMiddleware
from packages.agents.middleware.context.system_message_coalescing import SystemMessageCoalescingMiddleware
from packages.agents.middleware.quality.subagent_limit import SubagentLimitMiddleware
from packages.agents.middleware.quality.curriculum_alignment import CurriculumAlignmentMiddleware
from packages.agents.middleware.quality.readability_level import ReadabilityLevelMiddleware
from packages.agents.middleware.quality.pedagogical_quality import PedagogicalQualityMiddleware
from packages.agents.middleware.quality.bias_detection import BiasDetectionMiddleware
from packages.agents.middleware.quality.artifact_coherence import ArtifactCoherenceMiddleware
from packages.agents.middleware.quality.learning_objective_alignment import LearningObjectiveAlignmentMiddleware
from packages.agents.middleware.terminal.clarification import ClarificationMiddleware

ORDERED_MIDDLEWARE_LIST: list[type[BaseMiddleware]] = [
    InputSanitizationMiddleware,          # order=1   safety
    TokenBudgetMiddleware,                # order=2   safety
    ThreadDataMiddleware,                 # order=3   safety
    UploadsMiddleware,                    # order=4   safety
    ContentSafetyMiddleware,              # order=5   safety
    DanglingToolCallMiddleware,           # order=6   safety
    LLMErrorHandlingMiddleware,           # order=7   safety
    GuardrailMiddleware,                  # order=8   safety
    TeacherAuditLogMiddleware,            # order=9   safety
    ToolErrorHandlingMiddleware,          # order=10  safety
    LoopDetectionMiddleware,              # order=11  safety
    SafetyFinishReasonMiddleware,         # order=12  safety
    DynamicContextMiddleware,             # order=13  context
    SkillActivationMiddleware,            # order=14  context
    SummarizationMiddleware,              # order=15  context
    TodoListMiddleware,                   # order=16  context
    TokenUsageMiddleware,                 # order=17  context
    TitleMiddleware,                      # order=18  context
    MemoryMiddleware,                     # order=19  context
    ViewImageMiddleware,                  # order=20  context
    DeferredToolFilterMiddleware,         # order=21  context
    SystemMessageCoalescingMiddleware,    # order=22  context
    SubagentLimitMiddleware,              # order=23  quality
    CurriculumAlignmentMiddleware,        # order=24  quality
    ReadabilityLevelMiddleware,           # order=25  quality
    PedagogicalQualityMiddleware,         # order=26  quality
    BiasDetectionMiddleware,              # order=27  quality
    ArtifactCoherenceMiddleware,          # order=28  quality
    LearningObjectiveAlignmentMiddleware, # order=29  quality
    ClarificationMiddleware,              # order=30  terminal (MUST be last)
]

EXPECTED_MIDDLEWARE_COUNT: int = 30
