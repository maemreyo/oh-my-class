from __future__ import annotations

from typing import NewType

RunId = NewType("RunId", str)
TeacherId = NewType("TeacherId", str)
type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]
