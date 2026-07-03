# ADR-024: Flashcard Export for Quizlet/Anki Import

## Status

**Accepted** (2026-07-03) — Enable teachers to export flashcard decks as TSV (Quizlet import) and APKG (Anki import) from the teaching-pack pipeline, via the `flashcard_tsv` and `anki_apkg` exporters. Accepted by ADR-030 full artifact/export coverage.

## Context

Teachers frequently request flashcard-based study tools (Quizlet, Anki) alongside teaching packs. oh-my-class already has:

- A `FlashcardDeckData` contract (`packages/renderer/src/contracts/flashcard_deck.ts`) defining `Flashcard {id, front, back, hint?}`
- A `FlashcardTSVExporter` (`packages/exporters/src/flashcard-tsv/index.ts`) that produces Quizlet-compatible TSV (`front\tback\ttags`)
- An `AnkiApkgExporter` (`packages/exporters/src/anki-apkg/index.ts`) that produces `.apkg` files
- A CLI bridge (`packages/exporters/src/cli.ts`) that invokes both exporters via subprocess
- An `ExporterRegistry` (`packages/agents/teaching_pack/exporters.py`) that lists both formats in `_SUPPORTED_FORMATS`

However, none of these are wired into the teaching-pack pipeline:

1. `_export_finalize` in `nodes.py` returns file paths but does not invoke the CLI bridge for subprocess formats
2. The Content Creator Agent cannot produce `flashcard_deck` artifacts — `ArtifactContent.artifact_type` in `common/contracts/artifact.py` does not include `flashcard_deck`
3. `export_validator.py` has no `FORMAT_REQUIREMENTS` entry for `flashcard_tsv` or `anki_apkg`
4. No quality gate validates flashcard content before export

Research confirms:
- Quizlet's official API is dead (Jan 2020), no new keys issued
- Quizlet embeds violate INVARIANT-04 (standalone HTML, no external assets)
- Quizlet ToS prohibits scraping (Section 7.2)
- The TSV import format (`front\tback\ttags`) is exactly what `FlashcardTSVExporter` produces
- Teachers manually import TSV into Quizlet — no API needed

## Decision

### 1. Add `flashcard_deck` to the `ArtifactContent` artifact_type enum

Extend `common/contracts/artifact.py` to include `flashcard_deck` as a valid artifact type. This allows the Content Creator Agent to officially produce flashcard decks alongside lessons, quizzes, and worksheets.

The existing `FlashcardDeckData` contract already defines the schema. No new Pydantic model is needed — the agent outputs `flashcard_deck` with content conforming to the TypeScript `FlashcardDeckData` interface.

### 2. Wire subprocess exports into `_export_finalize`

Modify `_export_finalize` in `packages/agents/teaching_pack/nodes.py` to invoke the CLI bridge for `flashcard_tsv` and `anki_apkg` formats. Currently the function only returns file paths; it must also trigger the subprocess that writes the actual files.

The gateway-side `teaching_pack_export_writer.py` already handles subprocess invocation. The agent-side `_export_finalize` needs to signal that subprocess formats require gateway-side execution, not just return paths.

### 3. Add FORMAT_REQUIREMENTS for flashcard exports

Register `flashcard_tsv` and `anki_apkg` in `packages/quality/layer6_export/export_validator.py` with `flashcard_deck` as the required artifact type. This ensures the quality gate validates that flashcard content exists before attempting export.

### 4. Content Creator Agent prompt update

Update the pack-generator skill to instruct the Content Creator Agent to generate `flashcard_deck` artifacts when the lesson topic involves vocabulary, terminology, definitions, or memorization-heavy content. The agent already has the capability; the prompt needs to activate it.

### 5. No Quizlet API integration

We explicitly choose NOT to build a Quizlet API integration because:
- The official API is dead (no keys issued since Dec 2018, shut down Jan 2020)
- The unofficial `webapi/3.4` is undocumented and violates ToS
- Embeds violate INVARIANT-04 (standalone HTML requirement)
- The TSV import path is simple, reliable, and requires zero API access

## Consequences

- Teachers gain a new export path: teaching pack → TSV → import into Quizlet (manual, one-click)
- Teachers gain Anki export: teaching pack → .apkg → open in Anki (direct)
- The Content Creator Agent gains a new artifact type output, increasing its versatility
- Quality gates validate flashcard content before export (no empty decks, no placeholder text)
- No external API dependencies, no OAuth, no rate limits, no ToS violations
- The existing `flashcard_deck.html` template provides standalone HTML output as the primary study format

## Alternatives Considered

| Option | Pros | Cons |
|---|---|---|
| Build Quizlet API integration | Automated set creation | API dead, ToS violation, OAuth complexity, external dependency |
| Embed Quizlet iframes | Rich interactive experience | Violates INVARIANT-04, loads trackers, Safari breaks, no offline |
| Use H5P.Flashcards only | Already implemented, offline | Not portable to Quizlet/Anki ecosystems |
| Skip flashcard export entirely | No work needed | Teachers lose a high-value export path |
| Generate Quizlet-importable TXT only | Simplest | Missing Anki export, no quality validation |
