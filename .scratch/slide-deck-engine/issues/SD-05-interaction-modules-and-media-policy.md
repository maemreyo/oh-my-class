---
title: Add registered slide interactions and two-tier media policy
status: done
labels: [slide-deck-engine, interactions, media, ready-for-agent]
created: 2026-07-06
---

## Parent

ADR-041 and ADR-042.

## What to build

Add production interaction and media modules for `slide_deck` using registries, not ad hoc template branches. Interactions should be offline-first and non-persistent in v1, with no backend writes or student analytics. Media should support rich classroom use while preserving offline standalone exports by default.

The initial interaction set should include at least reveal/progression, quick check, poll prompt, timer, discussion prompt, exit ticket, and think-pair-share. Each module must declare schema, render behavior, print behavior, no-JS fallback, accessibility requirements, and answer/teacher-only policy.

Media policy should distinguish default offline packaged media from optional online embeds. Online media must be explicitly flagged, teacher-visible, and paired with fallback content.

## Acceptance criteria

- [x] `SlideInteractionRegistry` contains registered modules for reveal, quick check, poll prompt, timer, discussion prompt, exit ticket, and think-pair-share.
- [x] Each interaction has schema validation, renderer support, print/no-JS fallback, accessibility metadata, and tests.
- [x] Quick check supports teacher-only answer guidance without putting correct answers into student-facing DOM.
- [x] Media blocks validate alt text, media kind, source policy, and fallback requirements.
- [x] Offline export rejects unmanaged external URLs and supports inline SVG/data URI/local packaged assets according to policy.
- [x] Optional online media carries `requires_network` metadata, teacher preview warning, and fallback instructions.

## Todo items

- [x] Register v1 interactions: reveal, quick check, poll prompt, timer, discussion prompt, exit ticket, and think-pair-share.
- [x] Add schema, renderer, print/no-JS fallback, accessibility, and tests for each interaction.
- [x] Add quick-check teacher-only answer guidance without student DOM leakage.
- [x] Implement media block validation for alt text, media kind, source policy, and fallback fields.
- [x] Enforce offline export policy for inline/data/local assets and unmanaged external URL rejection.
- [x] Surface `requires_network` warnings and fallback instructions for optional online media.

## Completion notes

- Added registry metadata for v1 interactions with schema kind, no-JS fallback, accessibility requirement, print behavior, and non-persistence guarantees.
- Extended slide deck contracts to validate registered interaction types plus packaged/online media policy, including unmanaged external URL rejection for packaged media and fallback/network requirements for optional online media.
- Renderer projection now exposes interaction module classing, no-JS fallback text, and teacher-visible optional-online media warnings without leaking quick-check answers in student HTML.
- Focused verification passed: `uv run pytest common/contracts/tests/test_slide_deck.py packages/agents/tests/slide_deck_engine/test_engine.py` and `pnpm --dir packages/renderer exec vitest run __tests__/slide-deck-renderer.test.ts`.

## Blocked by

- SD-04 slide surfaces and answer-leak-safe projection.

## References

- `docs/adr/041-slide-deck-registries-and-interaction-modules.md`
- `docs/adr/042-slide-deck-surfaces-quality-and-release-gates.md`
- `common/contracts/components/registry.py`
- `packages/renderer/src/inline-assets.ts`
- `packages/quality/compliance_policy.py`

## Implementation notes

- Do not persist student responses in this issue.
- Do not introduce external script/framework dependencies.
- Keep complex drag/drop or scored classroom response collection deferred unless it can meet the same registry/test/fallback bar.
