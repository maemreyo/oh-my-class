from __future__ import annotations

from dataclasses import dataclass
from typing import assert_never

from common.contracts.quality import QualityFailureClass
from packages.agents.prompts.registry import PromptModule, PromptRegistry
from packages.agents.prompts.seed import REPAIR_V1


@dataclass(frozen=True, slots=True)
class RepairPromptSelection:
    module_id: str
    failure_class: QualityFailureClass


REPAIR_SCHEMA_V1 = PromptModule.create(
    id="repair_schema_v1",
    version="1.0.0",
    body=(
        "# Repair Agent — Schema Repair\n"
        "\n"
        "Repair only the schema and structural fields for {{artifact_type}}.\n"
        "\n"
        "## Failure Summary\n"
        "{{failure_summary}}\n"
        "\n"
        "## Instructions\n"
        "1. Add missing required ArtifactContent fields.\n"
        "2. Preserve existing educational content where possible.\n"
        "3. Do not modify unrelated fields.\n"
        "4. Return valid JSON only.\n"
    ),
    metadata={"task": "repair", "repair_type": "schema"},
)

REPAIR_ANSWER_KEY_V1 = PromptModule.create(
    id="repair_answer_key_v1",
    version="1.0.0",
    body=(
        "# Repair Agent — Answer Key Isolation\n"
        "\n"
        "Repair answer-key leakage for {{artifact_type}}.\n"
        "\n"
        "## Failure Summary\n"
        "{{failure_summary}}\n"
        "\n"
        "## Instructions\n"
        "1. Move answers, solutions, and scoring notes into teacher_only sections.\n"
        "2. Remove parseable correct-answer markers from student-facing sections.\n"
        "3. Do not modify unrelated fields.\n"
        "4. Return valid JSON only.\n"
    ),
    metadata={"task": "repair", "repair_type": "answer_key"},
)

REPAIR_PII_V1 = PromptModule.create(
    id="repair_pii_v1",
    version="1.0.0",
    body=(
        "# Repair Agent — PII Removal\n"
        "\n"
        "Remove student personal data from {{artifact_type}}.\n"
        "\n"
        "## Failure Summary\n"
        "{{failure_summary}}\n"
        "\n"
        "## Instructions\n"
        "1. Redact names, emails, phone numbers, and student identifiers.\n"
        "2. Preserve pedagogical meaning after redaction.\n"
        "3. Do not modify unrelated fields.\n"
        "4. Return valid JSON only.\n"
    ),
    metadata={"task": "repair", "repair_type": "pii"},
)

REPAIR_ACCESSIBILITY_V1 = PromptModule.create(
    id="repair_accessibility_v1",
    version="1.0.0",
    body=(
        "# Repair Agent — Accessibility Repair\n"
        "\n"
        "Repair accessibility metadata for {{artifact_type}}.\n"
        "\n"
        "## Failure Summary\n"
        "{{failure_summary}}\n"
        "\n"
        "## Instructions\n"
        "1. Add missing language, reading-level, and alt-text metadata.\n"
        "2. Keep student-facing learning content unchanged.\n"
        "3. Do not modify unrelated fields.\n"
        "4. Return valid JSON only.\n"
    ),
    metadata={"task": "repair", "repair_type": "accessibility"},
)

REPAIR_PROMPT_MODULES: tuple[PromptModule, ...] = (
    REPAIR_V1,
    REPAIR_SCHEMA_V1,
    REPAIR_ANSWER_KEY_V1,
    REPAIR_PII_V1,
    REPAIR_ACCESSIBILITY_V1,
)


def create_repair_prompt_registry() -> PromptRegistry:
    registry = PromptRegistry()
    for module in REPAIR_PROMPT_MODULES:
        registry.register(module)
    return registry


def repair_prompt_for_failure(failure_class: QualityFailureClass) -> RepairPromptSelection:
    match failure_class:
        case QualityFailureClass.SCHEMA_INVALID:
            module_id = REPAIR_SCHEMA_V1.id
        case QualityFailureClass.ANSWER_KEY_LEAKAGE:
            module_id = REPAIR_ANSWER_KEY_V1.id
        case QualityFailureClass.PII_LEAKAGE:
            module_id = REPAIR_PII_V1.id
        case QualityFailureClass.MISSING_ACCESSIBILITY:
            module_id = REPAIR_ACCESSIBILITY_V1.id
        case (
            QualityFailureClass.PLACEHOLDER_CONTENT
            | QualityFailureClass.EXTERNAL_ASSET
            | QualityFailureClass.MISSING_DOCTYPE
            | QualityFailureClass.UNSUPPORTED_COMPONENT
            | QualityFailureClass.FACTUAL_UNCERTAINTY
            | QualityFailureClass.PEDAGOGICAL_MISMATCH
            | QualityFailureClass.EXPORT_NOT_READY
        ):
            module_id = REPAIR_V1.id
        case unreachable:
            assert_never(unreachable)
    return RepairPromptSelection(module_id=module_id, failure_class=failure_class)
