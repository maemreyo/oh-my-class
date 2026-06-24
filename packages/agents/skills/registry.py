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
    "ccss_math":        SKILLS_DIR / "ccss_math"             / "SKILL.md",
    "ccss_ela":         SKILLS_DIR / "ccss_ela"              / "SKILL.md",
    "vn_ministry_2018": SKILLS_DIR / "vn_ministry_2018"      / "SKILL.md",
    "hsa_exam_prep":    SKILLS_DIR / "hsa_exam_prep"         / "SKILL.md",
    # Question design frameworks
    "bloom_taxonomy":   SKILLS_DIR / "bloom_taxonomy"        / "SKILL.md",
    # Content packing
    "zamery_pack":      SKILLS_DIR / "zamery-pack-generator" / "SKILL.md",
}
