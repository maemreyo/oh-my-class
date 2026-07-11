# Module: methodologies

**Path:** `packages/methodologies`
**Role:** Teaching methodology implementations — projects pedagogical packs (inverse-thinking, etc.) into student-facing artifact projections (lesson, worksheet, quiz, drill).

## Public interface

```python
# packages/methodologies/inverse_thinking/__init__.py
InverseThinkingProjection   # Pydantic model: artifact_type, case_ids, student_components, summary_rows, teacher_only
normalize_pack(payload)     # InverseThinkingPack | dict → InverseThinkingPack
validate_semantics(payload) # Raises ValidationError on semantic issues; returns validated InverseThinkingPack
project_lesson(payload)     # → InverseThinkingProjection (lesson: disaster scenes, clues, safe zones)
project_worksheet(payload)  # → InverseThinkingProjection (worksheet: evidence collection, repair prompts)
project_quiz(payload)       # → InverseThinkingProjection (quiz: "Which clue makes this disaster unsafe?")
project_drill(payload)      # → InverseThinkingProjection (drill: repair-the-disaster challenges)
```

### Key types

- **`InverseThinkingProjection`** (frozen Pydantic model):
  - `artifact_type: Literal["lesson", "worksheet", "quiz", "drill"]`
  - `methodology: Literal["inverse_thinking"]`
  - `case_ids: list[str]` (min 1)
  - `student_components: list[Heading | Paragraph | Callout | Table | QuestionList]` (min 1)
  - `summary_rows: list[InverseThinkingSummaryRow]`
  - `teacher_only: InverseThinkingTeacherOnly`

### Semantic validation rules (enforced by `validate_semantics()`)
1. `disaster` must start from a failure (not "Use...", "Remember...", "The rule...")
2. `key_clues` must be non-empty
3. `safe_zone` must contain a boundary rule token ("use", "rename", "current", "same", "rule", "before")
4. `filing_note` must have ≥4 words (synthesis requirement)

## Internal structure

```
packages/methodologies/
├── __init__.py                          # Empty re-export
└── inverse_thinking/
    ├── __init__.py                      # Public API: 7 symbols
    ├── projections.py                   # Core logic (185 lines)
    └── tests/
        ├── test_normalize.py
        ├── test_project_lesson.py
        ├── test_project_quiz_drill.py
        ├── test_project_worksheet.py
        ├── test_semantic_validation.py
        └── test_teacher_only_separation.py
```

**Key file:** `projections.py` — 100% of business logic. Functions:
- `normalize_pack()` — ensures dict payloads conform to `InverseThinkingPack` schema, defaults `methodology` and `creative_frame`
- `validate_semantics()` — pedagogical invariant enforcement; raises `pydantic.ValidationError` with per-case per-step error details
- `project_lesson()` / `project_worksheet()` / `project_quiz()` / `project_drill()` — each builds `StudentComponent` list from cases, wraps in `InverseThinkingProjection`
- Helpers: `_projection()` (common fields), `_summary_table()` (Table from rows), `_safe_zone_for()` (case lookup)

## Depends on

- **`contracts`** — 2 import lines bringing in 9 types; components (Heading, Paragraph, etc.) + inverse_thinking

| Target | What | Where cited |
|--------|------|-------------|
| `common.contracts.components` | `Callout, Heading, Paragraph, QuestionCard, QuestionList, Table` | `projections.py:4` |
| `common.contracts.inverse_thinking` | `InverseThinkingPack, InverseThinkingSummaryRow, InverseThinkingTeacherOnly` | `projections.py:5-8` |

**Phase 3 hypothesis "methodologies → contracts: 8 imports" — CONFIRMED.** Two import lines bring in 9 types total (6 from `components`, 3 from `inverse_thinking`). The actual type count is 9, not 8.

## Used by

- **`quality`** — validate_semantics in inverse_thinking gate
- **`agents`** — InverseThinkingProjection, project_* functions in inverse_thinking_pipeline

| Consumer | What imported | Where cited |
|----------|---------------|-------------|
| **quality** | `validate_semantics` | `layer2_content/inverse_thinking.py:8` |
| **agents** | `InverseThinkingProjection`, `project_*` functions | `inverse_thinking_pipeline.py` |
| **quality (tests)** | Full projection pipeline | `inverse_thinking/tests/test_*.py` |

## Data & side effects

- **None.** Pure functions — no I/O, no config, no network, no file access.
- All state flows through the `InverseThinkingPack` input parameter.
- Output is a frozen Pydantic model (`model_config = ConfigDict(frozen=True)`).

## Notes / discrepancies vs existing docs

- **Only `inverse_thinking` is implemented.** No other methodologies exist despite AGENTS.md mentioning "inverse thinking, UbD, and other pedagogical frameworks." The module is structured for future expansion (subdirectory per methodology) but currently has a single implementation.
- **`InverseThinkingProjection` is defined inside `projections.py`**, not in `common/contracts/`. This is a minor departure from INVARIANT-10 (contracts are canonical schema). However, the projection is an internal artifact type used by quality and agents, not an agent output contract — so this is defensible.
- **`pyproject.toml` does not exist** — the package is an implicit workspace member using the parent workspace's Python path setup.

---
_Traced from source on 2026-07-11. Files examined in depth: all 7 source + 6 test files in packages/methodologies/. Only inverse_thinking methodology exists; no UbD or other frameworks implemented._
