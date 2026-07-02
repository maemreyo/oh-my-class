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
    from packages.agents.llm import (
        chat_messages,
        compiled_json_chat,
        extract_json_text,
        log_llm_failure,
        log_llm_start,
        log_llm_success,
    )
    from packages.agents.prompts.compiler import PromptCompiler
    from packages.agents.prompts.seed import create_seeded_registry
    from packages.agents.sub_agents.content_creator.prompts import load_system_prompt

    model = MODELS.content_creator
    run_id = str(state.get("run_id", ""))
    step = int(state.get("current_step", 8))
    system_prompt = load_system_prompt() + _JSON_ONLY_SUFFIX

    validated_artifacts: list[dict[str, Any]] = []
    artifact_failure_context: list[dict[str, Any]] = []

    for artifact_type in artifact_types:
        user_prompt = build_single_artifact_prompt(
            lesson_summary, research_summary, artifact_type, theme,
        )
        base_user_prompt = user_prompt
        messages = chat_messages(system_prompt, user_prompt)

        prompt_module = (
            "content_creator_mcq_v1" if artifact_type == "quiz"
            else "content_creator_lesson_v1"
        )
        compiled = PromptCompiler(create_seeded_registry()).compile(
            module_id=prompt_module, variables={},
        )

        content = None
        last_content = None
        for attempt in range(3):
            attempt_number = attempt + 1
            started = log_llm_start(
                "content_creator", run_id, step, model, attempt_number,
            )
            try:
                content = await compiled_json_chat(
                    model=model,
                    compiled=compiled,
                    messages=messages,
                    temperature=0.3,
                    tags=[
                        "agent:content_creator",
                        f"step:{state.get('current_step', 8)}",
                        f"run:{state.get('run_id', '')}",
                        f"attempt:{attempt_number}",
                        f"artifact:{artifact_type}",
                        "pipeline:oh-my-class",
                    ],
                )
                last_content = content
                log_llm_success(
                    "content_creator", run_id, step, model, attempt_number, started,
                )
                json_str = extract_json_text(content)
                artifact_data = json.loads(json_str)

                # Unwrap array — LLM should return single object but handle array too
                if isinstance(artifact_data, list):
                    if not artifact_data:
                        raise ValueError("LLM returned empty array")
                    artifact_data = artifact_data[0]

                if not isinstance(artifact_data, dict):
                    raise ValueError(
                        f"Expected dict, got {type(artifact_data).__name__}",
                    )

                # Validate artifact_type matches request
                returned_type = artifact_data.get("artifact_type")
                if returned_type != artifact_type:
                    raise ValueError(
                        f"Artifact type mismatch: expected '{artifact_type}', "
                        f"got '{returned_type}'",
                    )

                artifact = ArtifactContent.model_validate(artifact_data)
                validated_artifacts.append(artifact.model_dump())
                break  # success — move to next artifact type

            except (ValueError, json.JSONDecodeError) as parse_err:
                log_llm_failure(
                    "content_creator", run_id, step, model,
                    attempt_number, started, parse_err,
                )
                error_class = type(parse_err).__name__
                _LOGGER.warning(
                    "content_creator.artifact_failed artifact_type=%s "
                    "attempts=%d error=%s",
                    artifact_type, attempt_number, str(parse_err)[:200],
                )
                if attempt < 2:
                    messages = chat_messages(
                        system_prompt,
                        retry_single_artifact_prompt(
                            base_user_prompt, artifact_type, parse_err, last_content,
                        ),
                    )
                    continue
                artifact_failure_context.append({
                    "artifact_type": artifact_type,
                    "attempts": attempt_number,
                    "error_class": error_class,
                    "last_error": str(parse_err)[:500],
                })
                raise ValueError(
                    f"Content creator failed for '{artifact_type}' "
                    f"({error_class}, after {attempt_number} attempts): "
                    f"{parse_err}",
                ) from parse_err

            except Exception as e:
                log_llm_failure(
                    "content_creator", run_id, step, model,
                    attempt_number, started, e,
                )
                error_class = type(e).__name__
                _LOGGER.warning(
                    "content_creator.artifact_failed artifact_type=%s "
                    "attempts=%d error=%s",
                    artifact_type, attempt_number, str(e)[:200],
                )
                if attempt < 2:
                    messages = chat_messages(
                        system_prompt,
                        retry_single_artifact_prompt(
                            base_user_prompt, artifact_type, e, last_content,
                        ),
                    )
                    continue
                artifact_failure_context.append({
                    "artifact_type": artifact_type,
                    "attempts": attempt_number,
                    "error_class": error_class,
                    "last_error": str(e)[:500],
                })
                raise ValueError(
                    f"Content creator failed for '{artifact_type}' "
                    f"({error_class}, after {attempt_number} attempts): "
                    f"{e}",
                ) from e

    return {"artifacts": validated_artifacts}


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
