from __future__ import annotations

import pytest

from packages.agents.prompts.compiler import (
    Overlay,
    PromptCompiler,
    StructuredOutputContradictionError,
)
from packages.agents.prompts.registry import PromptModule, PromptRegistry


def _compiler_for(body: str) -> PromptCompiler:
    registry = PromptRegistry()
    registry.register(PromptModule.create(id="contract_v1", version="1.0.0", body=body))
    return PromptCompiler(registry)


class TestStructuredOutputContracts:
    def test_rejects_object_and_array_output_in_same_body(self) -> None:
        compiler = _compiler_for(
            "# Contract\nReturn a JSON object.\nDo not include prose.\nReturn a JSON array.",
        )

        with pytest.raises(StructuredOutputContradictionError) as exc_info:
            compiler.compile(module_id="contract_v1", variables={})

        assert exc_info.value.formats == frozenset({"object", "array"})

    def test_rejects_object_and_array_output_across_overlay(self) -> None:
        compiler = _compiler_for("# Contract\nReturn a JSON object.")

        with pytest.raises(StructuredOutputContradictionError):
            compiler.compile(
                module_id="contract_v1",
                variables={},
                overlays=[Overlay(id="array_overlay", body="Return a JSON array.")],
            )

    def test_accepts_single_structured_output_form(self) -> None:
        compiler = _compiler_for("# Contract\nReturn a JSON object.")

        result = compiler.compile(module_id="contract_v1", variables={})

        assert "JSON object" in result.compiled_body
