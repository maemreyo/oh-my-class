"""Skill activation middleware — injects curriculum skill files based on subject."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


SUBJECT_SKILL_MAP = {
    "math": "curriculum/ccss_math",
    "ela": "curriculum/ccss_ela",
    "english": "curriculum/ccss_ela",
    "science": "curriculum/ccss_math",
}


class SkillActivationMiddleware(BaseMiddleware):
    """Injects curriculum skill files into context metadata based on subject."""

    name: str = "skill_activation"
    order: int = 14

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        subject = state.get("class_info", {}).get("subject", "").lower()
        skill_rel = SUBJECT_SKILL_MAP.get(subject)
        if skill_rel:
            # context/skill_activation.py: parents[2] = agents/, then /skills
            skills_dir = Path(__file__).resolve().parents[2] / "skills"
            skill_path = skills_dir / skill_rel
            if skill_path.exists():
                context.metadata["injected_skill"] = skill_path.read_text()
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        return state
