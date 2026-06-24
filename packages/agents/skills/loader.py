"""SkillLoader: reads SKILL.md files and assembles <available_skills> XML block."""
from __future__ import annotations

from pathlib import Path

from packages.agents.skills.registry import SKILL_MAP


class SkillLoader:
    """Load curriculum skills and inject into agent system prompt.

    Separate from load_system_prompt() (Report 01) — different concerns:
      - system prompt: agent identity, output format, behavior
      - skills block: curriculum knowledge injected alongside system prompt

    Usage in graph node:
        system_prompt = load_system_prompt('system')
        skills_block = SkillLoader().build_skills_block(['ccss_math', 'bloom_taxonomy'])
        full_prompt = system_prompt + "\\n\\n" + skills_block
    """

    def __init__(self, skills_map: dict[str, Path] | None = None):
        self._map = skills_map or SKILL_MAP

    def load_skill(self, name: str) -> str:
        """Load a single SKILL.md file content. Raises KeyError if not registered."""
        if name not in self._map:
            raise KeyError(
                f"Skill '{name}' not registered in SKILL_MAP. "
                f"Available: {list(self._map.keys())}"
            )
        path = self._map[name]
        if not path.exists():
            raise FileNotFoundError(f"SKILL.md not found at: {path}")
        return path.read_text(encoding="utf-8")

    def build_skills_block(self, skill_names: list[str]) -> str:
        """Build <available_skills> XML block from list of skill names.

        Returns empty string if no skills requested.
        """
        if not skill_names:
            return ""

        skill_blocks = []
        for name in skill_names:
            content = self.load_skill(name)
            skill_blocks.append(
                f'<skill name="{name}">\n{content.strip()}\n</skill>'
            )

        return (
            "<available_skills>\n"
            + "\n\n".join(skill_blocks)
            + "\n</available_skills>"
        )

    def list_available(self) -> list[str]:
        """Return all registered skill names."""
        return list(self._map.keys())
