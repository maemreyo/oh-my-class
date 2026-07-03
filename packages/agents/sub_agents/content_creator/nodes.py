"""Content Creator Agent — LangGraph node function and validators."""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

_LOGGER = logging.getLogger(__name__)

from common.contracts.artifact import ArtifactContent
from packages.agents.sub_agents.content_creator.prompt_contract import (
    build_single_artifact_prompt,
    retry_single_artifact_prompt,
)
from packages.agents.sub_agents.content_creator.summarizers import (
    summarize_lesson_plan,
    summarize_research_bundle,
)
from packages.agents.teaching_pack.stages import StageEnum, stage_number

_build_single_artifact_prompt = build_single_artifact_prompt
_retry_single_artifact_prompt = retry_single_artifact_prompt

if TYPE_CHECKING:
    from packages.agents.sub_agents.content_creator.state import ContentCreatorNodeState


_JSON_ONLY_SUFFIX = (
    "\n\nCRITICAL: Respond ONLY with a single JSON ArtifactContent object. "
    "No prose, no explanation, no markdown code fences. Just the raw JSON."
)


# ── Main node ──────────────────────────────────────────────────────────────


async def content_creator_node(state: ContentCreatorNodeState) -> dict[str, Any]:
    """Generate lesson artifacts from plan + research.

    Iterates artifact types and makes one LLM call per type, each returning
    a single ArtifactContent object.

    Returns: {"artifacts": [...]}
    """
    if state.get("use_hierarchical_creator", False):
        from packages.agents.sub_agents.content_creator.hierarchical import build_hierarchical_artifacts

        return build_hierarchical_artifacts(state)

    lesson_plan = state.get("lesson_plan") or {}
    research_bundle = state.get("research_bundle") or {}
    artifact_types = state.get("artifact_types") or ["lesson"]
    theme = state.get("theme", "default")
    lesson_summary = summarize_lesson_plan(lesson_plan)
    research_summary = summarize_research_bundle(research_bundle)

    from packages.agents.config.models import MODELS
    from packages.agents.llm import extract_json_text
    from packages.agents.prompts.compiler import PromptCompiler
    from packages.agents.prompts.seed import create_seeded_registry
    from packages.agents.runtime import AgentRuntime, AgentRuntimeConfig
    from packages.agents.sub_agents.content_creator.prompts import load_system_prompt

    generation_model = state.get("generation_model")
    model = generation_model if isinstance(generation_model, str) and generation_model else MODELS.content_creator
    run_id = str(state.get("run_id", ""))
    current_step = state.get("current_step", StageEnum.ARTIFACT_WORKFLOW)
    step = stage_number(current_step)
    system_prompt = load_system_prompt() + _JSON_ONLY_SUFFIX
    runtime = AgentRuntime(AgentRuntimeConfig(
        agent="content_creator",
        run_id=run_id,
        step=step,
        step_label=current_step.value,
        model=model,
        base_temperature=0.3,
        retry_temperature=0.3,
    ))

    validated_artifacts: list[dict[str, Any]] = []
    artifact_failure_context: list[dict[str, Any]] = []

    for artifact_type in artifact_types:
        user_prompt = build_single_artifact_prompt(
            lesson_summary, research_summary, artifact_type, theme,
        )
        base_user_prompt = user_prompt
        messages = runtime.messages(system_prompt, user_prompt)

        prompt_module = (
            "content_creator_mcq_v1" if artifact_type == "quiz"
            else "content_creator_lesson_v1"
        )
        compiled = PromptCompiler(create_seeded_registry()).compile(
            module_id=prompt_module, variables={},
        )

        try:
            artifact = await runtime.complete_compiled_json_with_retries(
                compiled=compiled,
                messages=messages,
                parse=lambda content: _parse_artifact_content(content, artifact_type),
                retry_messages=lambda error, content: runtime.messages(
                    system_prompt,
                    retry_single_artifact_prompt(
                        base_user_prompt, artifact_type, error, content,
                    ),
                ),
                extra_tags=(f"artifact:{artifact_type}",),
            )
            validated_artifacts.append(artifact.model_dump())
        except (ValueError, json.JSONDecodeError) as parse_err:
            _record_artifact_failure(artifact_failure_context, artifact_type, parse_err, runtime.config.max_retries)
            raise ValueError(
                f"Content creator failed for '{artifact_type}' "
                f"({type(parse_err).__name__}, after {runtime.config.max_retries} attempts): "
                f"{parse_err}",
            ) from parse_err
        except Exception as exc:
            _record_artifact_failure(artifact_failure_context, artifact_type, exc, runtime.config.max_retries)
            raise ValueError(
                f"Content creator failed for '{artifact_type}' "
                f"({type(exc).__name__}, after {runtime.config.max_retries} attempts): "
                f"{exc}",
            ) from exc

    return {"artifacts": validated_artifacts}


def _parse_artifact_content(content: str, artifact_type: str) -> ArtifactContent:
    from packages.agents.llm import extract_json_text

    artifact_data = json.loads(extract_json_text(content))
    if isinstance(artifact_data, list):
        if not artifact_data:
            raise ValueError("LLM returned empty array")
        artifact_data = artifact_data[0]
    if not isinstance(artifact_data, dict):
        raise ValueError(f"Expected dict, got {type(artifact_data).__name__}")
    returned_type = artifact_data.get("artifact_type")
    if returned_type != artifact_type:
        raise ValueError(
            f"Artifact type mismatch: expected '{artifact_type}', got '{returned_type}'",
        )
    return ArtifactContent.model_validate(artifact_data)


def _record_artifact_failure(
    artifact_failure_context: list[dict[str, Any]],
    artifact_type: str,
    error: BaseException,
    attempts: int,
) -> None:
    error_class = type(error).__name__
    _LOGGER.warning(
        "content_creator.artifact_failed artifact_type=%s attempts=%d error=%s",
        artifact_type,
        attempts,
        str(error)[:200],
    )
    artifact_failure_context.append({
        "artifact_type": artifact_type,
        "attempts": attempts,
        "error_class": error_class,
        "last_error": str(error)[:500],
    })


# ── Validation utilities ───────────────────────────────────────────────────


def validate_no_cdn(artifacts: list[dict[str, Any]]) -> list[str]:
    """Check for CDN references in artifacts."""
    issues = []
    cdn_patterns = ["cdn.", "cloudflare.com", "jsdelivr.net", "unpkg.com"]
    for i, artifact in enumerate(artifacts):
        content = json.dumps(artifact)
        for pattern in cdn_patterns:
            if pattern in content:
                issues.append(f"CDN reference found in artifact {i}: {pattern}")
    return issues


def validate_no_pii(artifacts: list[dict[str, Any]]) -> list[str]:
    """Check for PII in artifacts."""
    issues = []
    email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    phone_pattern = re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")
    for i, artifact in enumerate(artifacts):
        content = json.dumps(artifact)
        if email_pattern.search(content):
            issues.append(f"Email found in artifact {i}")
        if phone_pattern.search(content):
            issues.append(f"Phone number found in artifact {i}")
    return issues
