"""#465 (Content Intelligence Graph): unified package.

Consolidates the four deterministic graph/query-port modules that were
built incrementally across prior sessions on #465 into one package-owned
home, per the issue's "Create a package-owned Content Intelligence Graph"
ask. No behavior changed by this move -- each submodule is verbatim except
for import paths.

What's unified here (see each submodule for the full contract):
- `prerequisite` -- knowledge-component nodes, prerequisite closure.
- `misconception` -- misconception nodes, fail-closed grounded retrieval.
- `objective_decomposition` -- objective -> knowledge-component decomposition.
- `exercise_candidate` -- exercise-candidate nodes, objective/KC/misconception/
  task-model linkage.
- `terminology`, `example`, `task_model` -- new node/edge contracts for the
  three catalog types #465's Scope names that had no contract anywhere yet.
- `snapshot` -- deterministic (hash-based) snapshot versioning + node-id
  uniqueness helper, shared by all of the above.
- `alignment` -- `CurriculumAlignmentRecord`, linking a knowledge component to
  a versioned `CurriculumStandard` (`subject_capability_pack.py`) and the
  `ClaimEvidence` substantiating the alignment claim -- the "every claimed
  curriculum alignment resolves to a versioned source node and evidence
  record" acceptance criterion.

Deliberately NOT duplicated here (imported from where they already live):
`CurriculumStandard`/`MisconceptionEntry` (`subject_capability_pack.py`),
`EvidenceSource`/`LearningMoveEntry`/`ContraindicationEntry`
(`component_strategy_knowledge_models.py`), `ClaimEvidence` +
`assert_high_risk_claims_are_grounded` (`claim_evidence.py`).

Content honesty note: `seeds/ccss_math_sample.py` seeds a SMALL (5-record),
manually reviewed sample of real CCSS Math standard codes -- not a
"certified" or complete catalog. See that module's docstring. MOET 2018 and
NGSS catalogs remain empty/TODO: seeding those accurately requires source
documents this session did not have reliable access to, and fabricating
codes would violate the issue's own "no claim of complete/certified
coverage beyond reviewed catalogs" out-of-scope note.
"""

from __future__ import annotations

from common.contracts.claim_evidence import ClaimEvidence, assert_high_risk_claims_are_grounded
from common.contracts.component_strategy_knowledge_models import (
    ContraindicationEntry,
    EvidenceSource,
    LearningMoveEntry,
)
from common.contracts.content_intelligence_graph.alignment import CurriculumAlignmentRecord
from common.contracts.content_intelligence_graph.example import (
    ExampleGraph,
    ExampleNode,
    retrieve_examples,
)
from common.contracts.content_intelligence_graph.exercise_candidate import (
    ExerciseCandidateAccessDeniedError,
    ExerciseCandidateGraph,
    ExerciseCandidateGraphError,
    ExerciseCandidateNode,
    retrieve_exercise_candidates,
)
from common.contracts.content_intelligence_graph.misconception import (
    MisconceptionAccessDeniedError,
    MisconceptionGraph,
    MisconceptionGraphError,
    MisconceptionNode,
    MisconceptionUngroundedError,
    retrieve_misconceptions,
)
from common.contracts.content_intelligence_graph.objective_decomposition import (
    ObjectiveAccessDeniedError,
    ObjectiveDecompositionGraph,
    ObjectiveDecompositionGraphError,
    ObjectiveMissingError,
    ObjectiveNode,
    decompose_objective,
)
from common.contracts.content_intelligence_graph.prerequisite import (
    ContentAccessScope,
    PrerequisiteAccessDeniedError,
    PrerequisiteCycleError,
    PrerequisiteGraph,
    PrerequisiteGraphError,
    PrerequisiteMissingNodeError,
    PrerequisiteNode,
    PrerequisiteScopeConflictError,
    prerequisite_closure,
)
from common.contracts.content_intelligence_graph.snapshot import (
    DuplicateNodeIdError,
    assert_unique_node_ids,
    compute_snapshot_version,
)
from common.contracts.content_intelligence_graph.task_model import (
    TaskModelCatalog,
    TaskModelNode,
    lookup_task_model,
)
from common.contracts.content_intelligence_graph.terminology import (
    TerminologyGraph,
    TerminologyNode,
    retrieve_terminology,
)
from common.contracts.subject_capability_pack import CurriculumFramework, CurriculumStandard

__all__ = [
    # tenant scope
    "ContentAccessScope",
    # prerequisite
    "PrerequisiteNode",
    "PrerequisiteGraph",
    "PrerequisiteGraphError",
    "PrerequisiteCycleError",
    "PrerequisiteMissingNodeError",
    "PrerequisiteScopeConflictError",
    "PrerequisiteAccessDeniedError",
    "prerequisite_closure",
    # misconception
    "MisconceptionNode",
    "MisconceptionGraph",
    "MisconceptionGraphError",
    "MisconceptionAccessDeniedError",
    "MisconceptionUngroundedError",
    "retrieve_misconceptions",
    # objective decomposition
    "ObjectiveNode",
    "ObjectiveDecompositionGraph",
    "ObjectiveDecompositionGraphError",
    "ObjectiveMissingError",
    "ObjectiveAccessDeniedError",
    "decompose_objective",
    # exercise candidate
    "ExerciseCandidateNode",
    "ExerciseCandidateGraph",
    "ExerciseCandidateGraphError",
    "ExerciseCandidateAccessDeniedError",
    "retrieve_exercise_candidates",
    # terminology (new)
    "TerminologyNode",
    "TerminologyGraph",
    "retrieve_terminology",
    # examples (new)
    "ExampleNode",
    "ExampleGraph",
    "retrieve_examples",
    # task models (new)
    "TaskModelNode",
    "TaskModelCatalog",
    "lookup_task_model",
    # snapshot versioning (new)
    "compute_snapshot_version",
    "assert_unique_node_ids",
    "DuplicateNodeIdError",
    # curriculum alignment (new)
    "CurriculumAlignmentRecord",
    # reused, not duplicated
    "CurriculumFramework",
    "CurriculumStandard",
    "ClaimEvidence",
    "assert_high_risk_claims_are_grounded",
    "EvidenceSource",
    "LearningMoveEntry",
    "ContraindicationEntry",
]
