---
title: "Prompt Management: G2 Pattern — Markdown Files per Agent + SkillActivation"
status: done
labels: [architecture, agents, prompts]
created: 2026-06-24
priority: p1
report: "01"
---

## What to build

Move all LLM system prompts from hardcoded strings to Markdown files in `prompts/` subfolders per agent. Integrate with `SkillActivationMiddleware` for on-demand curriculum standards injection.

**Design decision (grilling Q8):** G2 — Markdown files. Non-devs can edit prompts without code changes. SkillActivation middleware loads and injects `.md` files as skills (curriculum standards CCSS, VN Ministry).

## Current State

Prompts are either:
- Hardcoded f-strings inside agent class methods
- Not yet written (stub agents)

No `prompts/` directories exist anywhere in `packages/agents/`.

## Target Structure

```
packages/agents/
├── lead_agent/
│   └── prompts/
│       ├── __init__.py           # load_system_prompt() helper
│       └── system.md             # Lead Agent system prompt
├── planner/
│   └── prompts/
│       ├── __init__.py
│       ├── system.md             # Planner system prompt
│       └── examples/
│           └── lesson_plan.md    # few-shot example
├── researcher/
│   └── prompts/
│       ├── __init__.py
│       └── system.md
├── content_creator/
│   └── prompts/
│       ├── __init__.py
│       ├── system.md
│       ├── lesson.md             # artifact-type specific guidance
│       ├── worksheet.md
│       └── quiz.md
├── reviewer/
│   └── prompts/
│       ├── __init__.py
│       └── system.md
└── skills/                       # SkillActivation targets
    ├── curriculum/
    │   ├── ccss_math.md          # Common Core State Standards — Math
    │   ├── ccss_ela.md           # Common Core State Standards — ELA
    │   └── vn_ministry_2018.md   # Vietnamese MoET 2018 curriculum
    └── pedagogy/
        ├── bloom_taxonomy.md     # Bloom's taxonomy guidance
        └── differentiation.md   # Differentiated instruction
```

## Implementation Spec

### Shared `prompts/__init__.py` pattern (same for every agent)

```python
from pathlib import Path


_PROMPTS_DIR = Path(__file__).parent


def load_system_prompt(name: str = "system") -> str:
    """Load a prompt markdown file by name."""
    path = _PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def load_skill(skill_name: str) -> str:
    """Load a skill markdown file for injection (used by SkillActivation)."""
    skills_dir = Path(__file__).resolve().parents[3] / "skills"
    path = skills_dir / f"{skill_name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Skill not found: {path}")
    return path.read_text(encoding="utf-8")
```

### `packages/agents/planner/prompts/system.md`

```markdown
# Oh My Class — Planner Agent

You design lesson blueprints for teachers. Given a raw teaching request and class info,
output a structured lesson plan in JSON format.

## Required Output Format

```json
{
  "topic": "string",
  "grade_level": "string",
  "subject": "string",
  "duration_minutes": number,
  "learning_objectives": ["string"],
  "key_concepts": ["string"],
  "suggested_activities": ["string"],
  "artifact_types": ["lesson", "worksheet", "quiz"],
  "curriculum_standard": "string or null"
}
```

## Guidelines

- Align content to the specified grade level (use Bloom's taxonomy for objectives)
- Set duration based on typical class periods (40-90 minutes)
- Choose artifact_types based on the teacher's request
- If curriculum_standard is mentioned, include it verbatim
```

### `packages/agents/skills/curriculum/ccss_math.md`

```markdown
# Curriculum Skill: Common Core State Standards — Mathematics

When creating math content, align learning objectives and activities to CCSS Math standards.

## Grade Band Examples

### K-2
- Count, add, subtract within 20 (K.CC, 1.OA, 2.OA)
- Understand place value (1.NBT, 2.NBT)

### 3-5
- Operations with whole numbers and fractions (3.OA-3.NF, 4.NF, 5.NF)
- Geometric measurement (3.MD, 4.MD, 5.MD)

### 6-8
- Ratios and proportional relationships (6.RP, 7.RP)
- Linear equations and functions (8.EE, 8.F)

## How to Apply

Prefix each learning objective with the relevant standard code, e.g.:
"[3.OA.A.1] Students will be able to interpret products of whole numbers."
```

### `SkillActivationMiddleware` integration

The existing `SkillActivationMiddleware` (layer 9) should be updated to look for skills in `packages/agents/skills/`:

```python
# packages/agents/middleware/context/skill_activation.py

class SkillActivationMiddleware(BaseMiddleware):
    """Detects skill references in system prompt and injects skill content.

    For oh-my-class: curriculum standards and pedagogy skills are injected
    based on the teacher's request context (subject, grade level).
    """
    name = "skill_activation"
    order = 9

    SKILLS_DIR = Path(__file__).resolve().parents[3] / "skills"

    SUBJECT_SKILL_MAP = {
        "math": "curriculum/ccss_math",
        "ela": "curriculum/ccss_ela",
        "english": "curriculum/ccss_ela",
    }

    async def before_model(self, state, context: MiddlewareContext) -> None:
        subject = state.get("class_info", {}).get("subject", "").lower()
        skill_name = self.SUBJECT_SKILL_MAP.get(subject)

        if skill_name:
            skill_path = self.SKILLS_DIR / f"{skill_name}.md"
            if skill_path.exists():
                skill_content = skill_path.read_text()
                # Inject as additional system message
                context.metadata["injected_skill"] = skill_content
```

## Acceptance Criteria

- [ ] Every agent has a `prompts/__init__.py` with `load_system_prompt()`
- [ ] Every agent has `prompts/system.md` with complete system prompt (not hardcoded string)
- [ ] `packages/agents/skills/` directory with at least: `ccss_math.md`, `ccss_ela.md`, `vn_ministry_2018.md`, `bloom_taxonomy.md`
- [ ] `SkillActivationMiddleware` updated to load skills from `packages/agents/skills/`
- [ ] Subject → skill mapping configurable (not hardcoded)
- [ ] Tests: `load_system_prompt()` raises `FileNotFoundError` for missing prompts; skill injection verified

## Dependencies

- Blocked by: nothing (standalone)
- Blocks: `lead-agent-react` (needs prompts/system.md), all sub-agent compiled graphs (need prompts/system.md)
- Depends on: `middleware-full-stack` for SkillActivationMiddleware implementation
