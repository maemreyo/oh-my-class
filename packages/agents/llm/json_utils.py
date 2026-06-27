from __future__ import annotations

import json
from typing import Any


def extract_json_text(content: Any, reasoning_content: Any = None) -> str:
    if isinstance(content, (dict, list)):
        return json.dumps(content)
    text = str(content).strip() if content else ""
    if not text and reasoning_content:
        text = _reasoning_text(reasoning_content)
    if not text:
        raise ValueError("LLM returned empty content")
    if "```json" in text:
        return text.split("```json")[1].split("```")[0].strip()
    if "```" in text:
        return text.split("```")[1].split("```")[0].strip()
    return text


def _reasoning_text(reasoning_content: Any) -> str:
    if isinstance(reasoning_content, list):
        parts = [
            part.get("text", str(part)) if isinstance(part, dict) else str(part)
            for part in reasoning_content
        ]
        return "".join(parts).strip()
    return str(reasoning_content).strip()
