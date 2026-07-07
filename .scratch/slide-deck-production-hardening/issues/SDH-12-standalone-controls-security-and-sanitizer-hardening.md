---
title: Standalone slide deck controls security and sanitizer hardening
status: ready-for-agent
labels: [ready-for-agent, slide-deck, security]
created: 2026-07-07
---

## Parent

ADR-043: Slide Deck Display Preferences and Projection Boundaries

## What to build

Harden the standalone slide-deck control surface introduced for presentation and print customization. Hash/query overrides, localStorage preferences, inline vanilla JS, buttons, selectors, and data attributes must remain safe, minimal, and compatible with the renderer sanitizer policy.

The slice should make it impossible for malformed URL state or localStorage state to inject HTML/JS, enable teacher-only data in student surfaces, or persist sensitive content. Only display preferences should be stored client-side, and all parsed values must be validated against the typed preference contract.

## Acceptance criteria

- [ ] Hash/query parsing accepts only known display preference values and rejects or defaults malformed values safely.
- [ ] localStorage stores only non-sensitive display preferences under a namespaced key and never stores teacher notes, answer keys, raw prompts, student PII, model output, or quality traces.
- [ ] Standalone controls use only sanitizer-approved native elements and attributes required for the feature.
- [ ] No dynamic HTML insertion is used for untrusted hash/query/localStorage values.
- [ ] Student/presentation surfaces cannot be switched into teacher-only data visibility through client-side state if teacher-only data was not projected into the HTML.
- [ ] Technical negative tests cover malformed hash/query values, poisoned localStorage values, and sanitizer output.
- [ ] Real acceptance in SDH-07 confirms actual exported HTML remains standalone, no external assets, and no teacher-only leakage after using controls.

## Blocked by

- SDH-03-standalone-presentation-print-controls.md
