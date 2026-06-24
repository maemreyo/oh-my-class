"""Tests for G2 prompt management — markdown files per agent, skills directory."""

from __future__ import annotations

import pytest


# ── load_system_prompt() per sub-agent ────────────────────────────────────────

class TestPlannerPrompt:
    def test_loads_without_error(self):
        from packages.agents.sub_agents.planner.prompts import load_system_prompt
        prompt = load_system_prompt()
        assert isinstance(prompt, str) and len(prompt) > 50

    def test_contains_role(self):
        from packages.agents.sub_agents.planner.prompts import load_system_prompt
        assert "Planner" in load_system_prompt()

    def test_mentions_bloom(self):
        from packages.agents.sub_agents.planner.prompts import load_system_prompt
        assert "Bloom" in load_system_prompt() or "bloom" in load_system_prompt()

    def test_missing_name_raises_file_not_found(self):
        from packages.agents.sub_agents.planner.prompts import load_system_prompt
        with pytest.raises(FileNotFoundError):
            load_system_prompt("nonexistent_prompt")


class TestResearcherPrompt:
    def test_loads_without_error(self):
        from packages.agents.sub_agents.researcher.prompts import load_system_prompt
        prompt = load_system_prompt()
        assert isinstance(prompt, str) and len(prompt) > 50

    def test_contains_fact_protocol(self):
        from packages.agents.sub_agents.researcher.prompts import load_system_prompt
        assert "FACT" in load_system_prompt()

    def test_contains_research_policies(self):
        from packages.agents.sub_agents.researcher.prompts import load_system_prompt
        prompt = load_system_prompt()
        assert "basic" in prompt and "rigorous" in prompt


class TestContentCreatorPrompt:
    def test_loads_without_error(self):
        from packages.agents.sub_agents.content_creator.prompts import load_system_prompt
        prompt = load_system_prompt()
        assert isinstance(prompt, str) and len(prompt) > 50

    def test_mentions_json_only(self):
        from packages.agents.sub_agents.content_creator.prompts import load_system_prompt
        assert "JSON" in load_system_prompt()

    def test_mentions_hard_constraints(self):
        from packages.agents.sub_agents.content_creator.prompts import load_system_prompt
        assert "CDN" in load_system_prompt() or "constraint" in load_system_prompt().lower()


class TestReviewerPrompt:
    def test_loads_without_error(self):
        from packages.agents.sub_agents.reviewer.prompts import load_system_prompt
        prompt = load_system_prompt()
        assert isinstance(prompt, str) and len(prompt) > 50

    def test_mentions_geval(self):
        from packages.agents.sub_agents.reviewer.prompts import load_system_prompt
        assert "G-Eval" in load_system_prompt()

    def test_mentions_hard_blocks(self):
        from packages.agents.sub_agents.reviewer.prompts import load_system_prompt
        assert "hard" in load_system_prompt().lower() or "block" in load_system_prompt().lower()


# ── Lead Agent prompt (already exists) ───────────────────────────────────────

def test_lead_agent_prompt_loads():
    from packages.agents.lead_agent.prompts import load_system_prompt
    prompt = load_system_prompt()
    assert "Lead Agent" in prompt
    assert "run_planner" in prompt


# ── Skills directory ──────────────────────────────────────────────────────────

class TestSkillsDirectory:
    def _load_skill(self, rel_path: str) -> str:
        from pathlib import Path
        skills_dir = Path(__file__).resolve().parents[1] / "skills"
        return (skills_dir / rel_path).read_text(encoding="utf-8")

    def test_ccss_math_exists(self):
        content = self._load_skill("curriculum/ccss_math.md")
        assert len(content) > 100

    def test_ccss_ela_exists(self):
        content = self._load_skill("curriculum/ccss_ela.md")
        assert len(content) > 100

    def test_vn_ministry_exists(self):
        content = self._load_skill("curriculum/vn_ministry_2018.md")
        assert len(content) > 100

    def test_bloom_taxonomy_exists(self):
        content = self._load_skill("pedagogy/bloom_taxonomy.md")
        assert "Remember" in content

    def test_differentiation_exists(self):
        content = self._load_skill("pedagogy/differentiation.md")
        assert len(content) > 100

    def test_ccss_math_mentions_grade_bands(self):
        content = self._load_skill("curriculum/ccss_math.md")
        assert "K-2" in content or "Grades" in content

    def test_bloom_taxonomy_has_six_levels(self):
        content = self._load_skill("pedagogy/bloom_taxonomy.md")
        for level in ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]:
            assert level in content


# ── G2 compliance: no hardcoded prompts in nodes.py ──────────────────────────

def test_planner_nodes_uses_load_system_prompt():
    import inspect
    from packages.agents.sub_agents.planner import nodes
    src = inspect.getsource(nodes)
    assert "load_system_prompt" in src
    assert "PLANNER_SYSTEM_PROMPT = " not in src.replace("PLANNER_SYSTEM_PROMPT = load_system_prompt()", "")


def test_researcher_nodes_uses_load_system_prompt():
    import inspect
    from packages.agents.sub_agents.researcher import nodes
    src = inspect.getsource(nodes)
    assert "load_system_prompt" in src


def test_content_creator_nodes_uses_load_system_prompt():
    import inspect
    from packages.agents.sub_agents.content_creator import nodes
    src = inspect.getsource(nodes)
    assert "load_system_prompt" in src
