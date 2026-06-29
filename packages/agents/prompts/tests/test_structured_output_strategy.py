from __future__ import annotations

from packages.agents.llm.compiled_chat import _provenance_tags
from packages.agents.llm.prompt_metadata import to_langfuse_metadata
from packages.agents.prompts.compiler import PromptCompiler
from packages.agents.prompts.registry import PromptModule, PromptRegistry


def _compiler_for(module: PromptModule) -> PromptCompiler:
    registry = PromptRegistry()
    registry.register(module)
    return PromptCompiler(registry)


def test_output_schema_defaults_to_json_object_strategy() -> None:
    module = PromptModule.create(
        id="strategy_v1",
        version="1.0.0",
        body="Return JSON.",
        output_schema={"type": "object"},
    )

    compiled = _compiler_for(module).compile(module_id="strategy_v1", variables={})

    assert compiled.metadata.structured_output_strategy == "json_object"
    assert to_langfuse_metadata(compiled.metadata)["structured_output_strategy"] == "json_object"


def test_prompt_metadata_accepts_explicit_native_schema_strategy() -> None:
    module = PromptModule.create(
        id="strategy_v1",
        version="1.0.0",
        body="Return JSON.",
        output_schema={"type": "object"},
        metadata={"structured_output_strategy": "native_schema"},
    )

    compiled = _compiler_for(module).compile(module_id="strategy_v1", variables={})

    assert compiled.metadata.structured_output_strategy == "native_schema"


def test_compiled_chat_tags_include_json_strategy_for_transport_routing() -> None:
    module = PromptModule.create(
        id="strategy_v1",
        version="1.0.0",
        body="Return JSON.",
        output_schema={"type": "object"},
        metadata={"structured_output_strategy": "native_schema"},
    )
    compiled = _compiler_for(module).compile(module_id="strategy_v1", variables={})

    tags = _provenance_tags(compiled)

    assert "json_strategy:native_schema" in tags
