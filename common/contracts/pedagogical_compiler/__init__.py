"""Pedagogical Intelligence Compiler contracts (#489-#496)."""
from common.contracts.pedagogical_compiler.artifact_compiler import (
    ArtifactCompileRequest,
    ArtifactCompileResult,
    CompileDiagnostic,
    EntityProjection,
    SurfaceConstraint,
    compile_existing_artifact,
)
from common.contracts.pedagogical_compiler.intent import (
    IntentAssumption,
    IntentClarification,
    IntentConstraint,
    IntentEvidenceRequirement,
    IntentField,
    IntentOverride,
    TeachingIntent,
    compile_teaching_intent,
)
from common.contracts.pedagogical_compiler.objective_graph import (
    KnowledgeComponentRef,
    MasteryClaim,
    MisconceptionTarget,
    ObjectiveGraph,
    PrerequisiteRequirement,
    ProgramObjective,
    TransferTarget,
    VocabularyRequirement,
    build_objective_graph,
)
from common.contracts.pedagogical_compiler.optimizer import (
    CandidateProgram,
    Constraint,
    ConstraintResult,
    InfeasibilityExplanation,
    ObjectiveMetric,
    OptimizationPolicy,
    ParetoFrontier,
    SelectionDecision,
    candidate_from_program,
    optimize_programs,
)
from common.contracts.pedagogical_compiler.program_ir import (
    BranchPolicy,
    CognitiveBudget,
    EvidenceOpportunity,
    FeedbackPolicy,
    LearningMoveInstance,
    PedagogicalProgramIR,
    ProgramPhase,
    ProgramVariant,
    StudentAction,
    TeacherAction,
    TimeBudget,
    TransitionRule,
    build_program_ir,
)
from common.contracts.pedagogical_compiler.semantic_ir import (
    AnswerDerivation,
    Claim,
    ConceptExplanation,
    SemanticContentIR,
    SemanticDependency,
    SemanticEntity,
    build_semantic_ir,
)
from common.contracts.pedagogical_compiler.synthesis import (
    CandidateEntity,
    EntityRequirement,
    MultiPassSynthesisResult,
    RepairPlan,
    SelectionResult,
    SynthesisPlan,
    SynthesisReceipt,
    VerificationResult,
    scoped_repair,
    synthesize_semantic_content,
)
from common.contracts.pedagogical_compiler.tools import (
    DomainToolRuntime,
    ToolBudget,
    ToolCapability,
    ToolEvidence,
    ToolFailure,
    ToolPolicy,
    ToolReceipt,
    ToolRequest,
    ToolResult,
    default_tool_runtime,
)

__all__ = [name for name in globals() if not name.startswith("_")]
