from __future__ import annotations

from packages.agents.sub_agents.content_creator.prompts import load_system_prompt


class TestContentCreatorPedagogyPrompt:
    def test_present_tenses_inverse_thinking_requirements_are_explicit(self) -> None:
        prompt = load_system_prompt()

        assert "Present Tenses" in prompt
        assert "Exit Ticket" in prompt
        assert "wrong_reasons" in prompt
        assert "lesson, worksheet, and quiz" in prompt
        assert "know" in prompt
        assert "believe" in prompt
        assert "seem" in prompt
        assert "what the listener wrongly hears" in prompt
