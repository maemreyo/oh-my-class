from __future__ import annotations

from packages.agents.llm.prompt_metadata import to_langfuse_metadata
from packages.agents.prompts.compiler import PromptCompiler
from packages.agents.prompts.seed import SEED_MODULES, create_seeded_registry


def test_all_seeded_prompts_default_structured_output_strategy() -> None:
    for module in SEED_MODULES:
        assert module.output_schema is not None, f"Missing output schema in '{module.id}'"

        compiler = PromptCompiler(create_seeded_registry())
        result = compiler.compile(module_id=module.id, variables={})

        assert result.metadata.structured_output_strategy == "json_object", (
            f"Unexpected default structured output strategy in '{module.id}'"
        )


def test_all_compiled_seeded_prompts_export_structured_output_strategy() -> None:
    compiler = PromptCompiler(create_seeded_registry())

    for module in SEED_MODULES:
        result = compiler.compile(module_id=module.id, variables={})
        langfuse = to_langfuse_metadata(result.metadata)

        assert result.metadata.structured_output_strategy == "json_object", (
            f"Missing compiled structured output strategy for '{module.id}'"
        )
        assert langfuse["structured_output_strategy"] == "json_object", (
            f"Missing trace structured output strategy for '{module.id}'"
        )
