"""Seed data: initial prompt modules for the oh-my-class pipeline.

Registers the six core prompt modules used by the agent pipeline.  Each module
is versioned with semver and carries a content hash for integrity verification.
"""

from __future__ import annotations

from packages.agents.prompts.registry import PromptModule, PromptRegistry


# ── Individual prompt modules ───────────────────────────────────────────────

PLANNER_V1 = PromptModule.create(
    id="planner_v1",
    version="1.0.0",
    body=(
        "# Planner Agent — Lesson Design\n"
        "\n"
        "You are the Planner Agent for oh-my-class.\n"
        "Your task is to design a structured lesson plan using backward design (UbD).\n"
        "\n"
        "## Instructions\n"
        "\n"
        "1. Analyze the teacher's request and class information.\n"
        "2. Define clear learning objectives covering at least 2 Bloom's taxonomy levels.\n"
        "3. Design assessment checkpoints aligned with objectives.\n"
        "4. Structure the learning plan using Gagné's 9 events of instruction.\n"
        "5. Return a valid LessonPlan JSON.\n"
        "\n"
        "## Constraints\n"
        "\n"
        "- Minimum 1, maximum 10 learning objectives.\n"
        "- Duration must be between 10 and 180 minutes.\n"
        "- At least 2 different Bloom's taxonomy levels must be represented.\n"
        "- Prerequisite knowledge must be explicitly listed.\n"
    ),
    output_schema={
        "type": "object",
        "required": ["topic", "grade_level", "subject", "learning_objectives"],
        "properties": {
            "topic": {"type": "string"},
            "grade_level": {"type": "string"},
            "subject": {"type": "string"},
            "duration_minutes": {"type": "integer"},
            "learning_objectives": {
                "type": "array",
                "minItems": 1,
                "maxItems": 10,
            },
        },
    },
    metadata={"task": "lesson_planning", "locale": "vi", "subject": "general"},
)

CONTENT_CREATOR_MCQ_V1 = PromptModule.create(
    id="content_creator_mcq_v1",
    version="1.0.0",
    body=(
        "# Content Creator — MCQ Generation\n"
        "\n"
        "You are the Content Creator Agent for oh-my-class.\n"
        "Generate high-quality multiple choice questions.\n"
        "\n"
        "## Instructions\n"
        "\n"
        "1. Read the lesson plan and research bundle.\n"
        "2. Generate MCQ items with 4 options each (A-D).\n"
        "3. Each question must have exactly one correct answer.\n"
        "4. Include an explanation for the correct answer.\n"
        "5. Cover difficulty levels: recognition 40%, comprehension 30%, application 20%, higher-order 10%.\n"
        "6. Return valid ArtifactContent JSON.\n"
        "\n"
        "## Hard Constraints\n"
        "\n"
        "- JSON only — never raw HTML.\n"
        "- No CDN references in data.\n"
        "- No student PII in output.\n"
        "- Answer keys in teacher_only sections only.\n"
    ),
    output_schema={
        "type": "object",
        "required": ["artifact_type", "title", "sections"],
        "properties": {
            "artifact_type": {"const": "quiz"},
            "title": {"type": "string", "minLength": 3, "maxLength": 200},
            "sections": {"type": "array", "minItems": 1},
        },
    },
    metadata={"task": "mcq_generation", "locale": "vi", "artifact_type": "quiz"},
)

CONTENT_CREATOR_LESSON_V1 = PromptModule.create(
    id="content_creator_lesson_v1",
    version="1.0.0",
    body=(
        "# Content Creator — Lesson Pack Generation\n"
        "\n"
        "You are the Content Creator Agent for oh-my-class.\n"
        "Generate structured lesson pack content.\n"
        "\n"
        "## Instructions\n"
        "\n"
        "1. Read the lesson plan, research bundle, and artifact type assignment.\n"
        "2. Generate section-by-section content aligned with learning objectives.\n"
        "3. Include teacher-only notes where appropriate.\n"
        "4. Ensure content is age-appropriate for the specified grade level.\n"
        "5. Return valid ArtifactContent JSON.\n"
        "\n"
        "## Hard Constraints\n"
        "\n"
        "- JSON only — never raw HTML.\n"
        "- No CDN references in data.\n"
        "- No student PII in output.\n"
        "- Answer keys in teacher_only sections only.\n"
    ),
    output_schema={
        "type": "object",
        "required": ["artifact_type", "title", "sections"],
        "properties": {
            "artifact_type": {"type": "string"},
            "title": {"type": "string", "minLength": 3, "maxLength": 200},
            "sections": {"type": "array", "minItems": 1},
        },
    },
    metadata={"task": "lesson_generation", "locale": "vi", "artifact_type": "lesson"},
)

CONTENT_CREATOR_FLASHCARD_V1 = PromptModule.create(
    id="content_creator_flashcard_v1",
    version="1.0.0",
    body=(
        "# Content Creator — Flashcard Deck Generation\n"
        "\n"
        "You are the Content Creator Agent for oh-my-class.\n"
        "Generate a flashcard deck for vocabulary and key concepts.\n"
        "\n"
        "## Instructions\n"
        "\n"
        "1. Read the lesson plan and identify key vocabulary and concepts.\n"
        "2. Create front/back card pairs: front = term or question, back = definition or answer.\n"
        "3. Target 10-30 cards covering core vocabulary and key concepts.\n"
        "4. Use the target language for both sides (or bilingual as appropriate).\n"
        "5. Return valid ArtifactContent JSON with artifact_type \"flashcard_deck\".\n"
        "\n"
        "## Output Structure\n"
        "\n"
        "Produce a JSON object with:\n"
        "- artifact_type: \"flashcard_deck\"\n"
        "- title: descriptive name for the deck (e.g. \"Vocabulary: Equivalent Fractions\")\n"
        "- sections: array containing one or more sections, each with a \"cards\" array.\n"
        "  Each card: {id, front, back, hint?} — hint is optional mnemonic.\n"
        "- metadata: {subject, gradeLevel} for tagging the exported deck.\n"
        "\n"
        "## Hard Constraints\n"
        "\n"
        "- JSON only — never raw HTML.\n"
        "- No CDN references in data.\n"
        "- No student PII in output.\n"
        "- Every card must have non-empty front and back strings.\n"
        "- sections must have at least one element.\n"
    ),
    output_schema={
        "type": "object",
        "required": ["artifact_type", "title", "sections"],
        "properties": {
            "artifact_type": {"const": "flashcard_deck"},
            "title": {"type": "string", "minLength": 3, "maxLength": 200},
            "sections": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "cards": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["id", "front", "back"],
                                "properties": {
                                    "id": {"type": "string"},
                                    "front": {"type": "string", "minLength": 1},
                                    "back": {"type": "string", "minLength": 1},
                                    "hint": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            },
        },
    },
    metadata={"task": "flashcard_generation", "locale": "vi", "artifact_type": "flashcard_deck"},
)

RESEARCHER_V1 = PromptModule.create(
    id="researcher_v1",
    version="1.0.0",
    body=(
        "# Researcher Agent — Content Research\n"
        "\n"
        "You are the Researcher Agent for oh-my-class.\n"
        "Your task is to gather, cross-reference, and synthesize educational sources.\n"
        "\n"
        "## FACT Protocol\n"
        "\n"
        "For every factual claim:\n"
        "1. **F**ind — Search for authoritative sources.\n"
        "2. **A**ssess — Evaluate source credibility.\n"
        "3. **C**ross-reference — Verify against ≥2 independent sources.\n"
        "4. **T**ag — Mark as VERIFIED, MODIFIED, REMOVED, or UNCERTAIN.\n"
        "\n"
        "## Research Policies\n"
        "\n"
        "| Policy | Min Sources | Cross-ref |\n"
        "|--------|------------|-----------|\n"
        "| basic | 2-3 | factual accuracy only |\n"
        "| standard | 5+ | citations required |\n"
        "| rigorous | 10+ | peer-reviewed preferred |\n"
        "\n"
        "Default: standard.\n"
        "\n"
        "## Output\n"
        "\n"
        "Return a valid ResearchBundle JSON.\n"
    ),
    output_schema={
        "type": "object",
        "required": ["sources", "synthesis"],
        "properties": {
            "sources": {"type": "array", "minItems": 2},
            "synthesis": {"type": "string"},
        },
    },
    metadata={"task": "research", "locale": "vi"},
)

JUDGE_V1 = PromptModule.create(
    id="judge_v1",
    version="1.0.0",
    body=(
        "# Reviewer Agent — Quality Review (G-Eval)\n"
        "\n"
        "You are the Reviewer Agent for oh-my-class.\n"
        "Perform a 3-layer G-Eval quality assessment of generated artifacts.\n"
        "\n"
        "## Scoring Layers\n"
        "\n"
        "| Layer | Weight | Criteria |\n"
        "|-------|--------|----------|\n"
        "| Format compliance | 15% | DOCTYPE, no CDN, brand strings, responsive |\n"
        "| Content quality | 55% | Accuracy, completeness, relevance, reasoning |\n"
        "| Presentation | 30% | Readability, engagement, accessibility |\n"
        "\n"
        "## Rules\n"
        "\n"
        "- Pass threshold: overall_score ≥ 7.0.\n"
        "- Think before score: write rationale first, then assign the score.\n"
        "- Do NOT rate longer answers higher.\n"
        "- Generator model ≠ judge model (bias mitigation).\n"
        "- 3 independent judge calls → majority vote.\n"
        "\n"
        "## Hard Blocks (auto-fail)\n"
        "\n"
        "- missing_doctype\n"
        "- external_assets\n"
        "- answer_key_leakage\n"
        "- native_radio_inputs\n"
        "- unmanaged_js_runtime\n"
        "- missing_brand_string\n"
    ),
    output_schema={
        "type": "object",
        "required": ["overall_score", "layers", "critical_issues"],
        "properties": {
            "overall_score": {"type": "number", "minimum": 0, "maximum": 10},
            "layers": {"type": "object"},
            "critical_issues": {"type": "array"},
        },
    },
    metadata={"task": "quality_review", "locale": "vi"},
)

REPAIR_V1 = PromptModule.create(
    id="repair_v1",
    version="1.0.0",
    body=(
        "# Repair Agent — Self-Healing\n"
        "\n"
        "You are the Repair Agent for oh-my-class.\n"
        "When quality gates fail, you repair the artifacts to pass.\n"
        "\n"
        "## Self-Heal Strategies\n"
        "\n"
        "| Attempt | Strategy | When |\n"
        "|---------|----------|------|\n"
        "| 1st | Rewrite | Same model, new prompt with error feedback |\n"
        "| 2nd | Reroute | Different model |\n"
        "| 3rd | Replan | New content plan |\n"
        "| 4th | Escalate | Budget exhausted → notify teacher |\n"
        "\n"
        "## Instructions\n"
        "\n"
        "1. Read the review feedback and failed artifacts.\n"
        "2. Identify specific issues (score < 7.0 per layer).\n"
        "3. Repair each artifact, addressing the exact feedback.\n"
        "4. Ensure repaired content still meets all hard constraints.\n"
        "5. Return repaired ArtifactContent JSON.\n"
    ),
    output_schema={
        "type": "object",
        "required": ["artifacts", "repair_notes"],
        "properties": {
            "artifacts": {"type": "array", "minItems": 1},
            "repair_notes": {"type": "array", "items": {"type": "string"}},
        },
    },
    metadata={"task": "repair", "locale": "vi"},
)

# All seed modules for easy iteration
SEED_MODULES: list[PromptModule] = [
    PLANNER_V1,
    CONTENT_CREATOR_MCQ_V1,
    CONTENT_CREATOR_LESSON_V1,
    CONTENT_CREATOR_FLASHCARD_V1,
    RESEARCHER_V1,
    JUDGE_V1,
    REPAIR_V1,
]


def create_seeded_registry() -> PromptRegistry:
    """Create a PromptRegistry pre-populated with all seed modules."""
    registry = PromptRegistry()
    for module in SEED_MODULES:
        registry.register(module)
    return registry
