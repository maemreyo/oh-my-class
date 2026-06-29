# Evidence: task 1 - rich component-first fixtures

## Outcome
- Added reusable rich active-artifact fixtures for `lesson`, `worksheet`, `quiz`, `drill`, `recap`, and `infographic`.
- Python fixtures live in `tests/e2e/rich_teaching_pack_fixtures.py`.
- TypeScript renderer fixtures live in `packages/renderer/__tests__/rich-agent-fixtures.ts`.

## Behavior locked
- Fixtures contain multiple student-visible content units and coherence terms required by the Teaching Pack quality gate.
- Teacher answer material is isolated in `teacher_only` sections.
- A deliberately minimal shell artifact remains available to prove one-section HTML is not assessable.

## Verification
- `uv run pytest tests/e2e/test_teaching_pack_component_driven_flow.py -q` -> `3 passed`.
- `pnpm --filter @oh-my-class/renderer test -- agent-renderer --runInBand` -> `240 passed`.
