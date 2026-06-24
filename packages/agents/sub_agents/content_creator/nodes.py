"""Content Creator Agent — LangGraph node function and validators."""

from __future__ import annotations

import json
import re
from typing import Any

from common.contracts.artifact import ArtifactContent

from packages.agents.sub_agents.content_creator.state import ContentCreatorState


async def content_creator_node(state: ContentCreatorState) -> dict[str, Any]:
    """Generate lesson artifacts from plan + research.

    Returns: {"artifacts": [...]}
    """
    import litellm

    from packages.agents.sub_agents.content_creator.prompts import load_system_prompt
    CONTENT_CREATOR_SYSTEM_PROMPT = load_system_prompt()

    lesson_plan = state.get("lesson_plan") or {}
    research_bundle = state.get("research_bundle") or {}
    artifact_types = state.get("artifact_types") or ["lesson"]
    theme = state.get("theme", "default")

    user_prompt = f"""
Generate artifacts for the following lesson:

Lesson Plan:
{json.dumps(lesson_plan, indent=2)}

Research Bundle:
{json.dumps(research_bundle, indent=2)}

Artifact types to generate: {artifact_types}
Theme: {theme}

Please generate one ArtifactContent JSON for each artifact type.
Return a JSON array of artifacts.
"""

    messages = [
        {"role": "system", "content": CONTENT_CREATOR_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = await litellm.acompletion(
            model="f.light",
            messages=messages,
            temperature=0.7,
            extra_body={
                "metadata": {
                    "tags": [
                        "agent:content_creator",
                        f"step:{state.get('current_step', 8)}",
                        f"run:{state.get('run_id', '')}",
                        "pipeline:oh-my-class",
                    ]
                }
            },
        )

        content = response.choices[0].message.content

        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content.strip()

        artifacts_data = json.loads(json_str)

        if isinstance(artifacts_data, dict):
            artifacts_data = [artifacts_data]

        artifacts = []
        for artifact_data in artifacts_data:
            artifact = ArtifactContent.model_validate(artifact_data)
            artifacts.append(artifact.model_dump())

        return {"artifacts": artifacts}

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from LLM: {e}") from e
    except Exception as e:
        raise ValueError(f"Content creator agent failed: {e}") from e


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
