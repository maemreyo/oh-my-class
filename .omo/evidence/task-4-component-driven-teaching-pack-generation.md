# Evidence: task 4 - organized E2E full-flow tests

## Outcome
- Added checked-in E2E file `tests/e2e/test_teaching_pack_component_driven_flow.py`.
- E2E coverage drives rich artifacts through `_render_quality`, snapshot approval IDs, and `FileSystemTeachingPackExportWriter`.

## Behavior locked
- Minimal shell artifact still produces standalone HTML but fails the richness bar, proving one-section shells are not accepted as assessable evidence.
- Rich all-active-artifact flow exports each active artifact type through the gateway renderer adapter.
- Scoped regeneration flow preserves an accepted lesson while exporting a regenerated rich quiz.

## Verification
- Initial red run exposed fixture/quality mismatch: `_render_quality` returned recovery state instead of snapshots.
- Fixture corrections made the pack satisfy real quality coherence rules without weakening production gates.
- Final focused run: `uv run pytest tests/e2e/test_teaching_pack_component_driven_flow.py -q` -> `3 passed`.
- Combined focused run: `37 passed`.
