"""Prompt observability metadata for Langfuse tracing.

Builds structured metadata from a :class:`PromptModule` so every LLM call
carries full provenance — prompt id, version, content hash, and section
breakdown — for debugging, cost attribution, and quality auditing.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

from packages.agents.llm.transport_policy import JsonStrategy

_STRUCTURED_OUTPUT_STRATEGIES: Final[dict[str, JsonStrategy]] = {
    "native_schema": "native_schema",
    "json_object": "json_object",
    "prompt_json": "prompt_json",
    "text_extract": "text_extract",
}

if TYPE_CHECKING:
    from packages.agents.prompts.registry import PromptModule


def _sha256(content: str) -> str:
    """Return hex-encoded SHA-256 of *content*."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PromptMetadata:
    """Structured metadata attached to every LLM call for observability.

    Attributes:
        prompt_id: Module identifier (e.g. ``"planner_v1"``).
        prompt_version: Semver of the module used.
        content_hash: SHA-256 of the prompt body at registration time.
        compiled_hash: SHA-256 of the *compiled* (post-substitution) prompt body.
        sections: Section headers detected in the prompt body.
        output_schema_version: Version string for the expected output schema, or None.
    """

    prompt_id: str
    prompt_version: str
    content_hash: str
    compiled_hash: str
    sections: list[str]
    output_schema_version: str | None = None
    structured_output_strategy: JsonStrategy | None = None
    overlay_ids: list[str] = field(default_factory=list)
    compacted: bool = False
    dropped_sections: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class InvalidStructuredOutputStrategyError(ValueError):
    strategy: str

    def __str__(self) -> str:
        return f"Invalid structured output strategy: {self.strategy}"


def _extract_sections(body: str) -> list[str]:
    """Extract Markdown ``#`` / ``##`` headers from *body* as section names."""
    headers = re.findall(r"^#{1,3}\s+(.+)$", body, re.MULTILINE)
    return [h.strip() for h in headers]


def build_prompt_metadata(
    module: PromptModule,
    compiled_body: str,
    *,
    output_schema_version: str | None = None,
    overlay_ids: list[str] | None = None,
    compacted: bool = False,
    dropped_sections: list[str] | None = None,
) -> PromptMetadata:
    """Build :class:`PromptMetadata` from a module and its compiled output.

    Args:
        module: The registered prompt module.
        compiled_body: The final prompt string sent to the LLM (after variable
            substitution).
        output_schema_version: Optional version tag for the expected output
            schema.

    Returns:
        A fully-populated :class:`PromptMetadata`.
    """
    return PromptMetadata(
        prompt_id=module.id,
        prompt_version=module.version,
        content_hash=module.content_hash,
        compiled_hash=_sha256(compiled_body),
        sections=_extract_sections(module.body),
        output_schema_version=output_schema_version,
        structured_output_strategy=_structured_output_strategy(module),
        overlay_ids=overlay_ids or [],
        compacted=compacted,
        dropped_sections=dropped_sections or [],
    )


def to_langfuse_metadata(meta: PromptMetadata) -> dict[str, object]:
    """Convert :class:`PromptMetadata` to a Langfuse-compatible dict.

    The returned dict is suitable for passing as ``metadata`` to Langfuse
    ``generation()`` calls.
    """
    return {
        "prompt_id": meta.prompt_id,
        "prompt_version": meta.prompt_version,
        "content_hash": meta.content_hash,
        "compiled_hash": meta.compiled_hash,
        "sections": meta.sections,
        "output_schema_version": meta.output_schema_version,
        "structured_output_strategy": meta.structured_output_strategy,
        "overlay_ids": meta.overlay_ids,
        "compacted": meta.compacted,
        "dropped_sections": meta.dropped_sections,
    }


def _structured_output_strategy(module: PromptModule) -> JsonStrategy | None:
    raw_strategy = module.metadata.get("structured_output_strategy")
    match raw_strategy:
        case None:
            return "json_object" if module.output_schema is not None else None
        case str() as strategy:
            selected_strategy = _STRUCTURED_OUTPUT_STRATEGIES.get(strategy)
            if selected_strategy is None:
                raise InvalidStructuredOutputStrategyError(strategy=strategy)
            return selected_strategy
        case invalid:
            raise InvalidStructuredOutputStrategyError(strategy=repr(invalid))
