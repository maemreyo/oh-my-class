"""Vocabulary lesson methodology components — FilmClipActivity, RoleplayScript, ActiveRecallPrompt."""  # noqa: E501
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FilmClip(BaseModel):
    title: str
    description: str


class FilmClipActivity(BaseModel):
    type: Literal["film_clip_activity"] = "film_clip_activity"
    clips: list[FilmClip] = Field(default_factory=list)
    hunt_chips: list[str] = Field(default_factory=list)
    post_viewing_note: str | None = None


class RoleplayLine(BaseModel):
    speaker: str
    speaker_class: str | None = None  # e.g. "A" or "B" for CSS color
    text: str  # may contain [blank_1], [blank_2] placeholders


class RoleplayScript(BaseModel):
    type: Literal["roleplay_script"] = "roleplay_script"
    lines: list[RoleplayLine] = Field(default_factory=list)
    answer_key: list[str] = Field(default_factory=list)
    instruction: str | None = None


class ActiveRecallPrompt(BaseModel):
    type: Literal["active_recall_prompt"] = "active_recall_prompt"
    instruction: str
    time_minutes: int = Field(default=3, ge=1, le=30)
    scaffold_hint: str | None = None
