"""Rubric selector — selects the appropriate rubric version by artifact type and failure context.

Maps (artifact_type, failure_context) → Rubric from a RubricRegistry.
When failure_context indicates a specific quality area was already flagged
by deterministic gates, the selector returns a rubric variant that weights
that area more heavily so the LLM judge focuses on it.

Rubrics are versioned (common.contracts.rubric.Rubric.version_id) and the
selector tracks which version was chosen for provenance in JudgeResult.
"""

from __future__ import annotations

import logging

from common.contracts.rubric import Rubric, RubricCriterion, RubricLevel, RubricRegistry
from packages.quality.layer4_judge.judge_policy import JudgePolicyContext, JudgeRiskLevel, rubric_version_id

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default rubric criteria — shared across all artifact types.
# Weights mirror GEvalConfig: format 15%, content 55%, presentation 30%.
# ---------------------------------------------------------------------------

_BASE_CRITERIA: list[RubricCriterion] = [
    RubricCriterion(
        name="format_compliance",
        weight=0.15,
        levels=[
            RubricLevel(score=0, description="Missing required pedagogical structure (no title, no sections, no objective coverage)"),
            RubricLevel(score=5, description="Partial structure, some sections/objectives missing"),
            RubricLevel(score=10, description="All required sections/objectives present"),
        ],
        descriptors={
            "scope_note": (
                "Judge JSON content structure only (title, sections, objective coverage). "
                "This artifact is pre-render — HTML/DOCTYPE, brand string, external assets, "
                "and native-input compliance are validated separately by deterministic gates "
                "downstream and are OUT OF SCOPE here; do not penalize their absence."
            ),
        },
    ),
    RubricCriterion(
        name="content_quality",
        weight=0.55,
        levels=[
            RubricLevel(score=0, description="Inaccurate or missing content"),
            RubricLevel(score=5, description="Partially accurate, gaps in coverage"),
            RubricLevel(score=10, description="Accurate, complete, age-appropriate"),
        ],
    ),
    RubricCriterion(
        name="presentation",
        weight=0.30,
        levels=[
            RubricLevel(score=0, description="Unreadable or broken layout"),
            RubricLevel(score=5, description="Readable but poor formatting"),
            RubricLevel(score=10, description="Clean, engaging, accessible layout"),
        ],
    ),
]

# ---------------------------------------------------------------------------
# Artifact-type-specific rubric variants.
# Each artifact type can override weights or add extra criteria.
# ---------------------------------------------------------------------------

_ARTIFACT_TYPE_OVERRIDES: dict[str, dict[str, float]] = {
    # Quiz: content_quality weighted up (accuracy is critical for answers)
    "quiz": {"content_quality": 0.60, "presentation": 0.25},
    # Worksheet: presentation weighted up (students interact with layout)
    "worksheet": {"format_compliance": 0.20, "content_quality": 0.50, "presentation": 0.30},
    # Infographic: presentation weighted up heavily
    "infographic": {"format_compliance": 0.10, "content_quality": 0.40, "presentation": 0.50},
    # Drill: content quality critical (practice accuracy)
    "drill": {"content_quality": 0.60, "format_compliance": 0.15, "presentation": 0.25},
    # Recap: balanced
    "recap": {"content_quality": 0.55, "format_compliance": 0.15, "presentation": 0.30},
    # Lesson: default weights (no override needed)
}

# ---------------------------------------------------------------------------
# Failure-context weight boosts — when deterministic gates flag an area,
# the rubric shifts weight toward that area so the LLM judge scrutinizes it.
# ---------------------------------------------------------------------------

_FAILURE_CONTEXT_BOOSTS: dict[str, dict[str, float]] = {
    "answer_key_leakage": {"content_quality": 0.10},
    "placeholder_content": {"content_quality": 0.10},
    "missing_accessibility": {"presentation": 0.10},
    "external_asset": {"presentation": 0.10},
    "missing_doctype": {"presentation": 0.10},
    "pii_leakage": {"content_quality": 0.10},
    "schema_invalid": {"format_compliance": 0.10},
}

# Fallback artifact type when unrecognized
_DEFAULT_ARTIFACT_TYPE = "lesson"


def _build_criteria_for_type(
    artifact_type: str,
    failure_context: list[str] | None = None,
) -> list[RubricCriterion]:
    """Build rubric criteria with type-specific weights and failure-context boosts.

    Weights are normalized to sum to 1.0 after applying overrides and boosts.
    """
    # Start with base weights
    weights: dict[str, float] = {
        c.name: c.weight for c in _BASE_CRITERIA
    }

    # Apply artifact-type overrides
    overrides = _ARTIFACT_TYPE_OVERRIDES.get(artifact_type, {})
    weights.update(overrides)

    # Apply failure-context boosts
    if failure_context:
        for failure in failure_context:
            boosts = _FAILURE_CONTEXT_BOOSTS.get(failure, {})
            for criterion_name, boost in boosts.items():
                if criterion_name in weights:
                    weights[criterion_name] += boost

    # Normalize to sum to 1.0
    total = sum(weights.values())
    if total > 0:
        weights = {k: v / total for k, v in weights.items()}

    # Round to avoid floating-point drift
    weights = {k: round(v, 4) for k, v in weights.items()}

    # Build criteria with updated weights
    criteria = []
    for base in _BASE_CRITERIA:
        criteria.append(
            RubricCriterion(
                name=base.name,
                weight=weights.get(base.name, base.weight),
                levels=list(base.levels),
                descriptors=base.descriptors,
            )
        )

    return criteria


def _make_version_id(
    artifact_type: str,
    failure_context: list[str] | None,
    *,
    subject: str | None = None,
    locale: str | None = None,
    curriculum: str | None = None,
    risk_level: JudgeRiskLevel = "standard",
) -> str:
    """Generate a deterministic version_id from the selection parameters."""
    return rubric_version_id(JudgePolicyContext(
        artifact_type=artifact_type,
        deterministic_issues=tuple(failure_context or ()),
        subject=subject,
        locale=locale,
        curriculum=curriculum,
        risk_level=risk_level,
    ))


class RubricSelector:
    """Selects the appropriate rubric version by artifact type and failure context.

    Maintains a RubricRegistry of pre-built rubrics and constructs ad-hoc
    rubrics when no exact match exists.  Returns the selected Rubric along
    with a version_id string for provenance tracking.

    Usage::

        selector = RubricSelector()
        rubric = selector.select("quiz", ["answer_key_leakage"])
        # rubric.version_id == "rubric-quiz-answer_key_leakage"
        # rubric.criteria[0].name == "content_quality"
        # rubric.criteria[0].weight > 0.60  (boosted for answer-key concern)
    """

    def __init__(self, registry: RubricRegistry | None = None) -> None:
        self._registry = registry or RubricRegistry()
        self._build_default_rubrics()

    def _build_default_rubrics(self) -> None:
        """Pre-register default rubrics for all known artifact types."""
        all_types = list(_ARTIFACT_TYPE_OVERRIDES.keys()) + [_DEFAULT_ARTIFACT_TYPE]
        for artifact_type in set(all_types):
            version_id = _make_version_id(artifact_type, None)
            if version_id not in self._registry:
                criteria = _build_criteria_for_type(artifact_type)
                rubric = Rubric(
                    version_id=version_id,
                    criteria=criteria,
                    description=f"Default rubric for {artifact_type} artifacts",
                )
                self._registry.register(rubric)

    def select(
        self,
        artifact_type: str,
        failure_context: list[str] | None = None,
        *,
        subject: str | None = None,
        locale: str | None = None,
        curriculum: str | None = None,
        risk_level: JudgeRiskLevel = "standard",
    ) -> Rubric:
        """Select rubric for the given artifact type and failure context.

        First checks the registry for an exact version_id match. If not found,
        constructs a new rubric with adjusted weights, registers it, and returns it.

        Args:
            artifact_type: The type of artifact (e.g. "quiz", "lesson").
            failure_context: Optional list of failure class strings from
                deterministic gates. When present, rubric weights are boosted
                toward the relevant quality area.

        Returns:
            The selected Rubric with the appropriate version_id.
        """
        version_id = _make_version_id(
            artifact_type,
            failure_context,
            subject=subject,
            locale=locale,
            curriculum=curriculum,
            risk_level=risk_level,
        )

        # Check registry for existing rubric
        existing = self._registry.get(version_id)
        if existing is not None:
            return existing

        # Build and register new rubric
        criteria = _build_criteria_for_type(artifact_type, failure_context)
        if failure_context:
            ctx = ", ".join(failure_context)
            desc = f"Rubric for {artifact_type} with failure context: {ctx}"
        else:
            desc = f"Rubric for {artifact_type}"

        rubric = Rubric(
            version_id=version_id,
            criteria=criteria,
            description=desc,
        )
        try:
            self._registry.register(rubric)
        except ValueError:
            # Race condition safety — another thread may have registered it
            existing = self._registry.get(version_id)
            if existing is not None:
                return existing
            logger.warning("Failed to register rubric %s", version_id)
            raise

        return rubric

    @property
    def registry(self) -> RubricRegistry:
        """Access the underlying rubric registry."""
        return self._registry
