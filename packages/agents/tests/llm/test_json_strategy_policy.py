from __future__ import annotations

from packages.agents.llm.chat_context import build_call_context
from packages.agents.llm.transport_policy import JsonStrategy, TransportPolicyInput, decide_transport


class TestJsonStrategyPolicy:
    def test_uses_native_schema_when_requested_and_supported(self) -> None:
        decision = decide_transport(_payload(
            requested_json_strategy="native_schema",
            model_supports_native_schema=True,
        ))

        assert decision.json_strategy == "native_schema"

    def test_falls_back_from_unsupported_native_schema_to_json_object(self) -> None:
        decision = decide_transport(_payload(
            requested_json_strategy="native_schema",
            model_supports_native_schema=False,
            model_supports_json_object=True,
        ))

        assert decision.json_strategy == "json_object"

    def test_falls_back_to_text_extract_when_json_object_is_unsupported(self) -> None:
        decision = decide_transport(_payload(model_supports_json_object=False))

        assert decision.json_strategy == "text_extract"

    def test_chat_context_reads_strategy_and_capability_tags(self) -> None:
        context = build_call_context(
            "openai/4omc",
            [{"role": "user", "content": "Return JSON"}],
            [
                "agent:researcher",
                "run:run-json-strategy",
                "step:7",
                "task:research_synthesis",
                "json_strategy:native_schema",
                "supports_native_schema:true",
            ],
            256,
        )

        assert context.decision.json_strategy == "native_schema"


def _payload(
    *,
    requested_json_strategy: JsonStrategy | None = None,
    model_supports_native_schema: bool = False,
    model_supports_json_object: bool = True,
) -> TransportPolicyInput:
    return TransportPolicyInput(
        agent="researcher",
        task="research_synthesis",
        message_chars=100,
        max_tokens=1024,
        attempt=1,
        previous_error_type=None,
        requires_strict_json=True,
        safe_to_stream=True,
        requested_json_strategy=requested_json_strategy,
        model_supports_native_schema=model_supports_native_schema,
        model_supports_json_object=model_supports_json_object,
    )
