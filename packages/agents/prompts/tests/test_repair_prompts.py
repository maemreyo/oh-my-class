from __future__ import annotations

from common.contracts.quality import QualityFailureClass
from packages.agents.prompts.compiler import PromptCompiler
from packages.agents.prompts.repair_prompts import (
    create_repair_prompt_registry,
    repair_prompt_for_failure,
)


def test_answer_key_failure_selects_dedicated_repair_prompt() -> None:
    selected = repair_prompt_for_failure(QualityFailureClass.ANSWER_KEY_LEAKAGE)

    assert selected.module_id == "repair_answer_key_v1"


def test_schema_failure_selects_dedicated_repair_prompt() -> None:
    selected = repair_prompt_for_failure(QualityFailureClass.SCHEMA_INVALID)

    assert selected.module_id == "repair_schema_v1"


def test_unhandled_failure_uses_generic_repair_prompt() -> None:
    selected = repair_prompt_for_failure(QualityFailureClass.EXPORT_NOT_READY)

    assert selected.module_id == "repair_v1"


def test_selected_answer_key_prompt_compiles_with_failure_context() -> None:
    registry = create_repair_prompt_registry()
    selected = repair_prompt_for_failure(QualityFailureClass.ANSWER_KEY_LEAKAGE)

    result = PromptCompiler(registry).compile(
        module_id=selected.module_id,
        variables={
            "failure_summary": "Answer key leaked in student section",
            "artifact_type": "quiz",
        },
    )

    assert "teacher_only" in result.compiled_body
    assert "Do not modify unrelated fields" in result.compiled_body
    assert "Answer key leaked in student section" in result.compiled_body
