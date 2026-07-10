# Module: methodologies

**Path:** `packages/methodologies`
**Role:** Teaching methodology implementations. Currently only **inverse thinking** is implemented.

## Public interface

- `InverseThinkingProjection` — Pydantic model (output of projecting a pack onto an artifact type)
- `normalize_pack(payload)` — Normalize raw dict to `InverseThinkingPack`
- `validate_semantics(payload)` — Validate semantic rules (disaster starts from failure, clues exist, safe zone has boundary rule, filing note has synthesis)
- `project_lesson(payload)` → lesson components: disaster scenes, key clues, safe zones, filing notes
- `project_worksheet(payload)` → worksheet: evidence collection, clue work, repair prompts
- `project_quiz(payload)` → quiz: "Which clue makes this disaster unsafe?"
- `project_drill(payload)` → drill: repair-the-disaster challenges

## Internal structure

- `inverse_thinking/projections.py` (185 lines) — The entire implementation
- `inverse_thinking/__init__.py` — Exports 7 public symbols

### Semantic validation rules
1. `disaster` must start from a failure (not "Use...", "Remember...")
2. `key_clues` must be non-empty
3. `safe_zone` must contain a boundary rule token ("use", "rename", "current", "same", "rule", "before")
4. `filing_note` must have 4+ words (synthesis requirement)

### Student vs Teacher separation
All student-facing text is validated against teacher-only markers ("answer key", "correct answer", "teacher rationale"). The `InverseThinkingTeacherOnly` model holds rationale and answer_key separately.

## Depends on

- **`contracts`** — imports `InverseThinkingPack`, `InverseThinkingCase`, `Heading`, `Paragraph`, `Callout`, `Table`, `QuestionCard`, `QuestionList`
- external: `pydantic` (via common.contracts)

## Used by

- **`agents`** — `inverse_thinking_pipeline.py` calls projection functions
- **`quality`** — `validate_inverse_thinking_pack()` in `layer2_content/`
- **`renderer`** — inverse-thinking is a registered Artifact UI family (`investigation-folder`)

## Data & side effects

- No I/O — pure projection functions

---

_Traced from source on 2026-07-10. Files examined: all 9 files. Note: `packages/methodologies/` has no pyproject.toml — it's an implicit package using the parent workspace._
