---
title: Adaptive bounded slide-deck structure and density guards
status: ready-for-agent
labels: [ready-for-agent, slide-deck]
created: 2026-07-07
---

## Parent

ADR-040: Native Slide Deck Artifact and SlideDeckEngine

## What to build

Harden slide-deck content quality so real generated decks are neither one-slide nor sparse six-slide shells. The engine should keep a required pedagogical spine while allowing bounded adaptation by topic, grade, and duration.

The v1 spine is title/hook, objective/success criteria, vocabulary or context, worked example, guided practice, and exit ticket. Optional slides may add extra vocabulary, misconception checks, a second worked example, independent practice, recap, or localization-specific support. The deck should have a hard minimum of six meaningful slides and a soft maximum around ten to twelve unless the teacher asks for more.

Density should be checked by slide purpose rather than raw character count. Each slide type needs meaningful blocks, examples, prompts, or scaffolds appropriate to its role while staying presentation-readable.

## Acceptance criteria

- [ ] Generated slide decks use an adaptive bounded structure with the required six-slide pedagogical spine.
- [ ] Optional slides are added only when justified by topic complexity, duration, grade band, or teacher request.
- [ ] Density guards evaluate meaningful slide-purpose requirements, not only slide count or character count.
- [ ] Sparse decks fail deterministic quality before teacher approval/export and route to real recovery where available.
- [ ] Student-facing content remains concise enough for classroom presentation and does not become a worksheet dump.
- [ ] Real prompts used in SDH-07 produce meaningful ESL, math/science, and Vietnamese decks without marker/test prompt leakage.
- [ ] The final acceptance evidence includes deck structure/density assertions for all three real-LLM scenarios.

## Blocked by

None - can start immediately
