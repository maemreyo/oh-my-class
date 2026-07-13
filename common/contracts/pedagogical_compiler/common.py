"""Deterministic primitives shared by the pedagogical compiler contracts."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict

JsonObject = dict[str, Any]


class FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def canonical_json(value: Any) -> str:
    return json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _jsonable(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {str(key): _jsonable(nested) for key, nested in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    return value


def stable_hash(prefix: str, value: Any, *, length: int = 24) -> str:
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:length]}"


def stable_id(prefix: str, *parts: object, length: int = 20) -> str:
    normalized = [normalize_text(str(part)) for part in parts]
    digest = hashlib.sha256("|".join(normalized).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:length]}"


def normalize_text(value: str) -> str:
    value = value.strip().casefold()
    value = re.sub(r"[\s\u00a0]+", " ", value)
    value = re.sub(r"[.!?;,]+$", "", value)
    return value
