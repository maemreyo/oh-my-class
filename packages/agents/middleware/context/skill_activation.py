"""Skill activation middleware — injects curriculum skill files based on subject."""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState

if TYPE_CHECKING:
    from packages.agents.skills.loader import SkillLoader

SUBJECT_SKILLS: dict[str, str] = {
    "math": "ccss_math",
    "ela": "ccss_ela",
    "english": "ccss_ela",
    "science": "ccss_math",
}


class SkillActivationMiddleware(BaseMiddleware):
    """Injects curriculum skill files into context metadata based on subject.

    Uses SkillLoader (registry-backed) for path resolution instead of
    manual Path walking. The subject → skill-name mapping stays here because
    it is a middleware concern (which skill per subject), while the registry
    owns *where* skill files live.
    """

    name: str = "skill_activation"
    order: int = 11

    _loader: SkillLoader

    def __init__(self, loader: SkillLoader | None = None) -> None:
        if loader is None:
            from packages.agents.skills.loader import SkillLoader as _SkillLoader
            self._loader = _SkillLoader()
        else:
            self._loader = loader

    async def before_model(
        self,
        state: MiddlewareState,
        context: MiddlewareContext,
    ) -> MiddlewareState:
        subject = state.get("class_info", {}).get("subject", "").lower()
        skill_name = SUBJECT_SKILLS.get(subject)
        if skill_name:
            try:
                content = self._loader.load_skill(skill_name)
            except (KeyError, FileNotFoundError):
                return state
            context.metadata["injected_skill"] = content
        return state

    async def after_model(
        self,
        state: MiddlewareState,
        _context: MiddlewareContext,
    ) -> MiddlewareState:
        return state
