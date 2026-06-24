"""Tabular content components — Table."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Table(BaseModel):
    type: Literal["table"] = "table"
    columns: list[str]
    rows: list[list[str]]
    caption: str | None = None
