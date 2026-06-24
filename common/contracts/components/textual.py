"""Textual content components — Heading, Paragraph, Callout, lists."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Heading(BaseModel):
    type: Literal["heading"] = "heading"
    level: Literal[1, 2, 3, 4]
    text: str
    id: str | None = None


class Paragraph(BaseModel):
    type: Literal["paragraph"] = "paragraph"
    text: str


class Callout(BaseModel):
    type: Literal["callout"] = "callout"
    variant: Literal["note", "warning", "tip", "alert"]
    title: str | None = None
    body: str


class OrderedList(BaseModel):
    type: Literal["ordered_list"] = "ordered_list"
    items: list[str]


class UnorderedList(BaseModel):
    type: Literal["unordered_list"] = "unordered_list"
    items: list[str]
