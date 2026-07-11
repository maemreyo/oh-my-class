"""#464 (ADR-053 Content Orchestrator): typed artifact dependency plan.

Formalizes the generation-wave/dependency structure ADR-053 assigns to the
orchestrator -- "artifact dependency planning and generation waves" -- as a
validated contract instead of loose module-level tuples. Wave semantics
match ADR-053's default plan exactly (Wave 0: lesson; Wave 1: worksheet,
quiz, and slide_deck when dependencies are satisfied, plus the other
Practice/Synthesis artifacts that share Wave 1's dependency shape; Wave 2:
recap and the derived answer_key) -- this module does not invent new
ordering, it names and validates the ordering `artifact_fanout.py` already
enforced as bare tuples.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DependencyPlanError(ValueError):
    """Base class for structural defects in a dependency plan."""


class UnknownDependencyError(DependencyPlanError):
    def __init__(self, artifact_type: str, unknown_dependency: str) -> None:
        self.artifact_type = artifact_type
        self.unknown_dependency = unknown_dependency
        super().__init__(
            f"{artifact_type!r} depends on {unknown_dependency!r}, which is not in any wave",
        )


class ForwardDependencyError(DependencyPlanError):
    """Raised when a dependency is not strictly earlier-waved than its dependent."""

    def __init__(self, artifact_type: str, dependency: str) -> None:
        self.artifact_type = artifact_type
        self.dependency = dependency
        super().__init__(
            f"{artifact_type!r} depends on {dependency!r}, which is not in a strictly earlier wave "
            "(same-wave and forward dependencies are not orderable by wave alone)",
        )


class DependencyPlan(BaseModel):
    """An immutable, versioned generation-wave/dependency structure.

    `waves[i]` lists every artifact type eligible to start once wave `i-1`
    has completed. `dependencies[artifact_type]` names the artifact types
    that must be present (from an earlier wave) before that type can start
    -- ADR-053: "A slide deck does not wait for worksheet or quiz unless the
    approved strategy explicitly embeds those activities," i.e. dependencies
    are per-artifact-type, not "wait for the whole previous wave."
    """

    model_config = ConfigDict(frozen=True)

    plan_version: str = Field(min_length=1, max_length=40)
    waves: tuple[tuple[str, ...], ...] = Field(min_length=1)
    dependencies: dict[str, tuple[str, ...]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _dependencies_reference_earlier_waves_only(self) -> DependencyPlan:
        wave_index_by_type = {
            artifact_type: index
            for index, wave in enumerate(self.waves)
            for artifact_type in wave
        }
        for artifact_type, requires in self.dependencies.items():
            dependent_wave = wave_index_by_type.get(artifact_type)
            for dependency in requires:
                dependency_wave = wave_index_by_type.get(dependency)
                if dependency_wave is None:
                    raise UnknownDependencyError(artifact_type, dependency)
                if dependent_wave is not None and dependency_wave >= dependent_wave:
                    raise ForwardDependencyError(artifact_type, dependency)
        return self

    def wave_index_of(self, artifact_type: str) -> int | None:
        for index, wave in enumerate(self.waves):
            if artifact_type in wave:
                return index
        return None

    def dependencies_of(self, artifact_type: str) -> tuple[str, ...]:
        return self.dependencies.get(artifact_type, ())


# ADR-053 default plan: Wave 0 (lesson) -> Wave 1 (worksheet/quiz/slide_deck
# and the other artifacts sharing their lesson-only dependency) -> Wave 2
# (recap, answer_key). Exactly the wave/dependency structure
# `artifact_fanout.py` already enforced.
DEFAULT_DEPENDENCY_PLAN = DependencyPlan(
    plan_version="dependency_plan.v1",
    waves=(
        ("lesson",),
        ("worksheet", "quiz", "drill", "flashcard_deck", "roadmap", "slide_deck", "reading_passage", "infographic", "exit_ticket"),
        ("recap", "answer_key"),
    ),
    dependencies={
        "worksheet": ("lesson",),
        "quiz": ("lesson",),
        "drill": ("lesson",),
        "recap": ("lesson", "quiz"),
        "flashcard_deck": ("lesson",),
        "answer_key": ("quiz",),
        "roadmap": ("lesson",),
        "slide_deck": ("lesson",),
        "reading_passage": ("lesson",),
        "infographic": ("lesson",),
        "exit_ticket": ("lesson",),
    },
)
