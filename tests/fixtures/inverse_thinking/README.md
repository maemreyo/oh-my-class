# Canonical inverse-thinking fixture corpus

This directory is the shared corpus for inverse-thinking contracts, projections,
quality gates, renderer tests, and UI/E2E tests.

## Layout

- `positive/*.json`: valid `InverseThinkingPack` payloads across English grammar,
  math misconception, science false-model, and Vietnamese bilingual examples.
- `negative/*.json`: regression payloads for missing disaster, missing clue,
  missing safe-zone boundary, rule-first ordering, generic disaster, answer
  leakage, residual privacy-marker leakage, and unknown renderer components.
- `manifest.json`: every fixture path, case ID, kind, and sha256 hash.

## Add or update a fixture

1. Add or edit one JSON file under `positive/` or `negative/`.
2. Include metadata: `case_id`, `subject`, `grade_band`, `locale`,
   `expected_gate_outcome`, `expected_projection_outputs`, and either `pack` or
   `artifact`.
3. Keep fixtures synthetic: no real student names, emails, phone numbers,
   addresses, IDs, or external `http(s)://` asset URLs.
4. Update `manifest.json` with the file path and sha256:
   `shasum -a 256 tests/fixtures/inverse_thinking/<kind>/<file>.json`.
5. Run `uv run pytest tests/fixtures/test_inverse_thinking_corpus.py -q`.

Manifest drift is intentional: changing fixture content without updating the
hash must fail tests with the old and new hash values.
