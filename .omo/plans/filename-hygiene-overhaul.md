# Filename Hygiene Overhaul — Execution Plan

Generated: 2026-07-02 · Plan Agent session: `ses_0de3b9734ffexqeAtseREl9Cdd`

---

## Summary

11 tasks, 2 waves, ~60+ files moved/renamed, 11 commits.

| Wave | Tasks | Parallelism |
|------|-------|-------------|
| Wave 1 | Tasks 1–9 (all independent) | 9 parallel |
| Wave 2 | Tasks 10–11 (depend on Wave 1) | 2 parallel |

## Risk Assessment

| Change | Risk | Why |
|--------|------|-----|
| **1. teaching_pack/** | **HIGH** | 25 files, 134+ importers, alembic, main.py |
| 2. vocabulary/ | LOW | 4 files, ~10 import sites |
| 3. Exporter stubs | MEDIUM | Fixes real bug (exportByFormat broken) |
| 4. scoped_repair + artifacts | MEDIUM | Circular lazy imports to preserve |
| 5. judge_ prefix | LOW | 4 files, ~5 imports |
| 6. unit_packager pkg | MEDIUM | New package + workspace config |
| 7. questions.ts | LOW | 1 import site |
| 8. domain_skills/ | LOW | Rename only, no code imports |
| 9. coherence/ | LOW | 1 file, 2 import sites |

## Execution Waves

### Wave 1 (start immediately, all independent)

| # | Task | Category | Skills |
|---|------|----------|--------|
| 1 | teaching_pack/ subdirectory (services/gateway/) | deep | programming |
| 2 | vocabulary/ subdirectory (agents/teaching_pack/) | quick | programming |
| 3 | Exporter stubs merge (gift + h5p) | quick | programming |
| 4 | scoped_repair/ + artifacts/ subdirs | unspecified-low | programming |
| 5 | Strip judge_ prefix | quick | programming |
| 6 | unit_packager standalone package | unspecified-low | programming |
| 7 | Delete questions.ts | quick | programming |
| 8 | skills/ → domain_skills/ | quick | — |
| 9 | quality/ → coherence/ | quick | programming |

### Wave 2 (after Wave 1 completes)

| # | Task | Category | Skills |
|---|------|----------|--------|
| 10 | Enforcement script + pre-commit + CI + Makefile | unspecified-low | programming |
| 11 | Update AGENTS.md | writing | — |

## Commit Strategy

1 commit per change, 11 total:

1. `refactor(gateway): move teaching_pack_* files into teaching_pack/ subpackage`
2. `refactor(agents): move vocabulary_* files into vocabulary/ subpackage`
3. `fix(exporters): merge gift-impl/h5p-impl into canonical directories`
4. `refactor(agents): organize scoped_repair and artifact_fanout into subdirs`
5. `refactor(quality): strip judge_ prefix in layer4_judge/`
6. `refactor: extract unit_packager into standalone package`
7. `refactor(schemas): delete questions.ts, merge into exercise-types/`
8. `refactor: rename skills/ to domain_skills/`
9. `refactor(agents): rename quality/ to coherence/`
10. `chore: add naming convention enforcement script`
11. `docs: update AGENTS.md to reflect new directory structure`

## Final Verification

```bash
uv run pytest --tb=short
pnpm -r test
lint-imports
pnpm depcruise --validate .dependency-cruiser.cjs .
ruff check .
python scripts/check_naming_conventions.py
```
