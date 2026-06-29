# ADR-016: Inverse Thinking Creative Frame and Rollout

## Status

**Decided** (2026-06-30) — creative direction is registry-driven, teacher-controllable, and released behind a staged feature flag.

## Context

The inverse-thinking examples rely on memorable visual and narrative frames: case files, evidence cards, stamps, suspect language, clue chips, summary tables, and video challenges. The product goal is to keep outputs creative without making them random or locking every lesson into detective styling.

Teachers also need control without being overloaded. The feature must support safe editing, trust-building previews, staged rollout, and methodology-specific observability.

## Decision

Use a hybrid creative-direction model:

- Default behavior is `Auto`; Visual Engine selects a frame based on subject, grade, topic, artifact type, locale, and tone.
- Teacher UI exposes progressive disclosure: `Teaching approach` first, then optional `Creative direction`, `Intensity`, and `Student output` controls when inverse thinking is selected.
- Creative frames are resolved through an extensible registry/config, not hardcoded as a closed enum.
- Built-in stable frame IDs include `auto`, `detective_case`, `courtroom_trial`, `mythbusters_lab`, `survival_guide`, `disaster_report`, and `custom`.
- Registry entries define labels, grade bands, subject fit, tone limits, signature elements, token overrides, and renderer hints.
- Teacher editing is structured-first. Raw/JSON editing is an advanced escape hatch and must rerun schema and quality gates.
- Preview UI includes the final rendered artifact and a collapsible methodology inspector explaining why the method/frame was chosen, key clues, safe-zone boundaries, student tasks, and quality warnings.

Roll out as a staged production feature:

- Gate with `features.inverse_thinking_v1`.
- Enable dev/staging first with mock LLM fixtures and golden examples.
- Beta with selected teachers/classes before broader release.
- Do not silently downgrade failed inverse-thinking output to standard lesson output. Self-repair first; escalate or ask the teacher if repair fails.
- Add methodology-specific metadata tags and metrics: methodology, creative frame, projection, feature flag, quality gate, repair attempt, warning category, and teacher action.

## Consequences

- New creative frames can be added without changing core contracts.
- Teacher UX remains simple by default but supports power-user control.
- The product can monitor model drift, generic output, repair loops, and approval rates for inverse thinking separately from the general pipeline.
- Standalone HTML and no-CDN constraints still apply to every visual frame.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Hardcode detective frame | Strong initial look | Repetitive and subject-limited |
| Let model choose any style freely | Creative | Hard to validate, inconsistent, risky for age fit |
| Show only final rendered preview | Simple UI | Low teacher trust and hard debugging |
| Registry + progressive UI + inspector | Flexible, user-centric, observable | More implementation surface |
