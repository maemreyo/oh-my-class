"""Quality tier middleware — curriculum alignment, readability, pedagogy, and bias checks."""

from packages.agents.middleware.quality.artifact_coherence import ArtifactCoherenceMiddleware
from packages.agents.middleware.quality.bias_detection import BiasDetectionMiddleware
from packages.agents.middleware.quality.curriculum_alignment import CurriculumAlignmentMiddleware
from packages.agents.middleware.quality.learning_objective_alignment import (
    LearningObjectiveAlignmentMiddleware,
)
from packages.agents.middleware.quality.pedagogical_quality import PedagogicalQualityMiddleware
from packages.agents.middleware.quality.readability_level import ReadabilityLevelMiddleware

__all__ = [
    "CurriculumAlignmentMiddleware",
    "ReadabilityLevelMiddleware",
    "PedagogicalQualityMiddleware",
    "BiasDetectionMiddleware",
    "ArtifactCoherenceMiddleware",
    "LearningObjectiveAlignmentMiddleware",
]
