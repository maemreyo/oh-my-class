---
title: "Skill Loader: SK2 — SkillLoader Module, Registry, SKILL.md Files"
status: ready
labels: [architecture, agents, prompts]
created: 2026-06-24
priority: p1
report: "03"
---

## What to build

A `SkillLoader` module separate from the `prompts/` system. Skills = pluggable curriculum capabilities injected into agent system prompts as an `<available_skills>` XML block. Prompts = agent identity (`prompts/system.md`). Two separate concerns, two separate modules.

**Design decision (SK2):**
- `prompts/` = who the agent is — unchanged from Report 01
- `skills/` = what curriculum standards the agent knows — injected separately at graph node level
- `SkillLoader.build_skills_block(subjects)` → `<available_skills>...</available_skills>` string

## File Structure

```
packages/agents/
├── skills/
│   ├── loader.py                     # SkillLoader class
│   ├── registry.py                   # SKILL_MAP: subject → SKILL.md path
│   ├── zamery-pack-generator/
│   │   └── SKILL.md                  # how to generate Zamery-style educational packs
│   ├── ccss_math/
│   │   └── SKILL.md                  # Common Core State Standards — Mathematics
│   ├── ccss_ela/
│   │   └── SKILL.md                  # Common Core State Standards — ELA
│   ├── vn_ministry_2018/
│   │   └── SKILL.md                  # Vietnamese Ministry of Education 2018 curriculum
│   ├── hsa_exam_prep/
│   │   └── SKILL.md                  # HSA (ĐHQG HN) exam format + question types
│   └── bloom_taxonomy/
│       └── SKILL.md                  # Bloom's Taxonomy question design
```

## Implementation Spec

### `skills/registry.py`

```python
"""Maps subject identifiers to skill file paths.

To add a new curriculum standard:
1. Create packages/agents/skills/{skill_name}/SKILL.md
2. Add entry here: 'subject_key': 'skill_name/SKILL.md'
"""
from __future__ import annotations
from pathlib import Path

SKILLS_DIR = Path(__file__).parent

SKILL_MAP: dict[str, Path] = {
    # Curriculum standards
    "ccss_math":        SKILLS_DIR / "ccss_math"          / "SKILL.md",
    "ccss_ela":         SKILLS_DIR / "ccss_ela"           / "SKILL.md",
    "vn_ministry_2018": SKILLS_DIR / "vn_ministry_2018"   / "SKILL.md",
    "hsa_exam_prep":    SKILLS_DIR / "hsa_exam_prep"      / "SKILL.md",
    # Question design frameworks
    "bloom_taxonomy":   SKILLS_DIR / "bloom_taxonomy"     / "SKILL.md",
    # Content packing
    "zamery_pack":      SKILLS_DIR / "zamery-pack-generator" / "SKILL.md",
}
```

### `skills/loader.py`

```python
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

        return "<available_skills>\n" + "\n\n".join(skill_blocks) + "\n</available_skills>"

    def list_available(self) -> list[str]:
        """Return all registered skill names."""
        return list(self._map.keys())
```

### `skills/hsa_exam_prep/SKILL.md`

```markdown
# HSA Exam Prep Skill

## Context
The HSA (Highly Skilled Admission, ĐHQG Hà Nội) exam uses a standardized multiple-choice format
with 5 question sections per subject: sentence completion, synonyms, antonyms,
dialogue completion, and dialogue arrangement.

## Question Format Rules
- Each question has exactly 4 options: A, B, C, D
- Each section has a clear instruction line
- Wrong answers must have plausible reasons for incorrect selection
- Each answer includes: correct answer, full explanation, and wrong-answer breakdown

## Quality Standards
- Difficulty levels: recognition (L1), comprehension (L2), application (L3), analysis (L4)
- Each question must test exactly one linguistic concept
- Distractors must be grammatically parallel to the correct answer
- Explanations reference grammar rules, not just label the answer

## Artifact Format
Produce artifacts of type `quiz` with per-question `explain` and `wrongReasons` fields.
```

### `skills/bloom_taxonomy/SKILL.md`

```markdown
# Bloom's Taxonomy Skill

## Six Cognitive Levels
1. **Remember** — recall facts (define, list, name, identify)
2. **Understand** — explain in own words (describe, explain, summarize, classify)
3. **Apply** — use knowledge in new situations (solve, demonstrate, calculate, use)
4. **Analyze** — break into parts, find relationships (compare, differentiate, examine)
5. **Evaluate** — justify decisions (critique, judge, defend, assess)
6. **Create** — produce new work (design, construct, formulate, compose)

## Application
- Assign each question a Bloom level in metadata
- A well-designed quiz includes questions from at least 3 levels
- Lesson objectives should be written as "Students will be able to [action verb]"
- Exit tickets test Remember + Understand (quick check)
- Worksheets mix Apply + Analyze
```

### Usage in graph node

```python
# packages/agents/content_creator/node.py

from packages.agents.prompts import load_system_prompt
from packages.agents.skills.loader import SkillLoader

def content_creator_node(state: OhMyClassState) -> dict:
    # From Report 01: agent identity
    system_prompt = load_system_prompt("system")

    # From Report 03: curriculum skills — selected based on lesson subject
    skill_loader = SkillLoader()
    subjects = state.get("subjects", [])
    skills = _select_skills(subjects, state.get("exam_format"))
    skills_block = skill_loader.build_skills_block(skills)

    full_prompt = system_prompt + "\n\n" + skills_block
    ...

def _select_skills(subjects: list[str], exam_format: str | None) -> list[str]:
    """Map lesson metadata to skill names."""
    skills = ["bloom_taxonomy"]  # always included
    if "math" in subjects:
        skills.append("ccss_math")
    if "english" in subjects or "ela" in subjects:
        skills.append("ccss_ela")
    if "vietnamese" in subjects:
        skills.append("vn_ministry_2018")
    if exam_format == "hsa":
        skills.append("hsa_exam_prep")
    return skills
```

## Tests

```python
# packages/agents/skills/tests/test_loader.py

def test_build_skills_block_structure():
    loader = SkillLoader()
    block = loader.build_skills_block(["bloom_taxonomy"])
    assert block.startswith("<available_skills>")
    assert block.endswith("</available_skills>")
    assert '<skill name="bloom_taxonomy">' in block

def test_empty_skills_returns_empty_string():
    loader = SkillLoader()
    assert loader.build_skills_block([]) == ""

def test_unknown_skill_raises_key_error():
    loader = SkillLoader()
    with pytest.raises(KeyError, match="not registered"):
        loader.build_skills_block(["nonexistent_skill"])

def test_missing_file_raises_file_not_found(tmp_path):
    fake_map = {"ghost": tmp_path / "ghost.md"}  # file doesn't exist
    loader = SkillLoader(skills_map=fake_map)
    with pytest.raises(FileNotFoundError):
        loader.load_skill("ghost")

def test_multiple_skills_all_present():
    loader = SkillLoader()
    block = loader.build_skills_block(["bloom_taxonomy", "hsa_exam_prep"])
    assert '<skill name="bloom_taxonomy">' in block
    assert '<skill name="hsa_exam_prep">' in block

def test_list_available_returns_all_registered():
    loader = SkillLoader()
    available = loader.list_available()
    assert "ccss_math" in available
    assert "bloom_taxonomy" in available
    assert len(available) >= 5
```

## Acceptance Criteria

- [ ] `registry.py` — `SKILL_MAP` dict mapping skill names to `Path` objects
- [ ] `SkillLoader.load_skill(name)` — raises `KeyError` for unregistered, `FileNotFoundError` for missing file
- [ ] `SkillLoader.build_skills_block(names)` — returns valid `<available_skills>` XML block
- [ ] Empty names list → empty string (not invalid XML)
- [ ] 6 SKILL.md files shipped: `zamery_pack`, `ccss_math`, `ccss_ela`, `vn_ministry_2018`, `hsa_exam_prep`, `bloom_taxonomy`
- [ ] `hsa_exam_prep/SKILL.md` covers HSA question section format + difficulty levels
- [ ] `SkillLoader` is separate from `load_system_prompt()` — never mixed
- [ ] Adding a new skill = 1 SKILL.md file + 1 registry line, zero other changes

## Dependencies

- Blocked by: `prompt-management` (Report 01 — confirms separation of concerns)
- Blocks: `content_creator_node` update (skills injection)
- Priority: p1
