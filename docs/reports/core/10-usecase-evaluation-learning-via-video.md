# 10 — Use Case Evaluation: Learning via Video Worksheet

> **Date**: 2026-06-25
> **Evaluated by**: Sisyphus (2 parallel explore agents + 1 librarian agent + direct codebase analysis)
> **Scope**: Can `docs/templates/learning-via-video-template.html` be implemented through the oh-my-class system?
> **References**:
> - `docs/templates/learning-via-video-template.html` — 1,417-line reference template
> - `docs/reports/core/09-usecase-evaluation-vocab-lesson-plan.md` — prior methodology/template evaluation
> - `AGENTS.md` — standalone HTML, quality gate, and artifact invariants

---

## Verdict

**Conditionally feasible.** The pedagogical design can be implemented through oh-my-class, but the reference HTML cannot be accepted as-is. It violates the system's standalone/offline contract through Google Fonts, YouTube links, and a YouTube iframe. The correct implementation path is to treat this as a richer `worksheet` artifact, not as a new artifact type, and render the video as structured reference metadata rather than as an embedded external player.

The system already has most of the architecture needed: Content Creator returns structured JSON, the renderer uses Eta templates, `worksheet` is an existing artifact type, the pipeline already routes through ContentCreator, and Report 09 added methodology-oriented component patterns. The missing pieces are mainly worksheet block/schema/template support for video-reference cards, route-map stations, fillable tables, checklist blocks, and controlled inline worksheet interactivity.

---

## 1. Template Summary

`learning-via-video-template.html` is a student-facing Vietnamese/English IELTS worksheet built around a TED Talk. It is organized as a seven-station learning route:

| Station | Purpose | Main interaction |
|---|---|---|
| GA 01 | Pre-viewing warm-up | Vocabulary reference table, checkboxes, open response |
| GA 02 | First listening | Four main-idea short-answer questions |
| GA 03 | Second listening | Fillable note-taking table, sentence-pattern transfer |
| GA 04 | Vocabulary building | Reference vocabulary table, 10-row student vocabulary table |
| GA 05 | Summary writing | 120-150 word contenteditable summary with live counter |
| GA 06 | Speaking practice | IELTS Part 2 cue card and Part 3 planning prompts |
| GA 07 | Self-assessment | Checklist before submission |

The reference also includes a ticket-style header, horizontal route map, print styles, fixed action buttons, dynamic row insertion, contenteditable fields, a word counter, and a browser-side text export using `Blob`.

---

## 2. Current System Fit

### Best artifact fit: `worksheet`

The template is fundamentally a worksheet: it has student identity fields, sequential activity sections, questions, tables, written responses, and a self-check. It should not become a new top-level artifact type unless the product wants “video worksheet” to be independently selectable and exported differently from worksheets.

Current evidence:

| System area | Evidence | Fit |
|---|---|---|
| Canonical artifact model | `common/contracts/artifact.py` defines `ArtifactContent` with `artifact_type` including `worksheet` | Use `artifact_type="worksheet"` |
| Renderer type registry | `packages/renderer/src/contracts/index.ts` maps `worksheet` to `WorksheetData` | Extend worksheet data, not registry count |
| Current worksheet template | `packages/renderer/templates/pages/worksheet.html` renders printable worksheet sections/questions | Needs major template expansion |
| Pipeline graph | `packages/agents/graph.py` wires `step_08_generate` to `content_creator_graph_node` | No graph change needed |
| Content Creator | `packages/agents/sub_agents/content_creator/nodes.py` validates LLM output as `ArtifactContent` | Already produces artifact JSON |
| Content Creator prompt | `packages/agents/sub_agents/content_creator/prompts/system.md` already documents methodology components from Report 09 | Add video-worksheet rules |

### Existing components that help

| Capability | File | Reuse |
|---|---|---|
| Film-reference pattern | `packages/renderer/templates/components/film_card.html` | Can inform a video reference/warm-up component |
| Component dispatcher | `packages/renderer/templates/components/dispatcher.html` | Route new worksheet blocks to components |
| Roleplay script | `packages/renderer/templates/components/roleplay_script.html` | Fits speaking / scripted practice blocks |
| Question cards | `packages/renderer/templates/components/question_mc.html` and `question_card.html` | Can support richer prompt/question rendering |
| Vocab methodology contracts | `common/contracts/components/vocab_lesson.py` | Already includes `FilmClipActivity`, `RoleplayScript`, `ActiveRecallPrompt` |
| Methodology gate | `packages/quality/layer2_content/methodology.py` | Demonstrates structural component checks for tagged pedagogy |

---

## 3. Hard Constraint: External Media

The reference template cannot pass current quality gates as a literal HTML import.

| Reference feature | Why it fails |
|---|---|
| Google Fonts links | Layer 3 external asset patterns catch `href="https?://..."`; base sanitizer removes external `href` values |
| YouTube watch link | Same external `href` violation |
| YouTube iframe | External `src`, iframe not allowed by base sanitizer, and preview CSP uses `frame-src 'none'` |
| Missing `oh-my-class` brand string | Layer 3 `check_brand_string()` hard-blocks missing brand |

The relevant hard blocks are in `packages/quality/layer3_html/html_validator.py`: `external_assets` and `missing_brand_string` are hard failures. The renderer sanitizer base config in `packages/renderer/src/sanitizer/base-config.ts` also allows only `data:` schemes for `src` and removes `http(s)` links through `exclusiveFilter`.

### Recommendation: video as reference metadata

The system-conforming implementation should not embed YouTube. Instead, the worksheet should contain a video reference block with:

- title, speaker, duration, source label, proficiency level
- teacher-facing or learner-facing instruction to open the video outside the generated pack
- optional plain video ID or source slug as metadata, not rendered as `https://...`
- optional QR code only if generated as inline SVG or data URI without external fetches

This preserves the worksheet’s pedagogy while keeping standalone HTML offline-safe.

### Not recommended: conditional YouTube embed

Allowing a YouTube iframe would require weakening INVARIANT-04, updating the sanitizer, updating Layer 3 validation, changing preview CSP from `frame-src 'none'`, and handling consent/privacy constraints. Even `youtube-nocookie.com` is still an external network dependency. This should require an ADR if product leadership explicitly wants online embeds.

---

## 4. Interactive Worksheet Constraints

The reference uses inline vanilla JavaScript for dynamic rows, word counting, content cleanup, and text export. Inline JS is not automatically incompatible with interactive artifact types, but the current renderer and sanitizer need explicit support.

| Feature | Current state | Required decision |
|---|---|---|
| `contenteditable` fields | Not present in worksheet contract; not explicitly allowed in worksheet sanitizer attributes | Prefer native `<textarea>` for accessibility, or allow `contenteditable` with ARIA attributes |
| Dynamic fillable tables | No worksheet block/component for add-row tables | Add `fillable_table` block and component |
| Word counter | No reusable component | Add `word_counter` block or attach counter behavior to long-answer blocks |
| Export to `.txt` via Blob | Browser-side possible, but sandbox preview may require `allow-downloads`; production export likely belongs server-side | Prefer server/export pipeline for official export; keep browser export optional only if preview policy supports it |
| Fixed print/export buttons | Current print styles exist in references, but worksheet page is simple | Add print-only/no-print conventions in worksheet template |

External research confirms two implementation cautions:

1. `contenteditable` needs explicit accessibility treatment: `role="textbox"`, accessible labels, `aria-multiline` for multi-line regions, and careful screen-reader behavior. Native `<textarea>` is safer for simple worksheet responses.
2. Blob downloads should always revoke object URLs after use. In sandboxed previews, downloads may need the `allow-downloads` sandbox token, which the current preview sandbox does not include.

---

## 5. Recommended Data Model

Do not add `artifact_type="learning_via_video"` for the first implementation. Extend worksheet content instead.

### Worksheet metadata

Add optional video worksheet metadata to the renderer-side worksheet contract:

```typescript
type VideoWorksheetMetadata = {
  videoTitle: string;
  speaker?: string;
  sourceLabel?: string;
  duration?: string;
  proficiencyLevel?: string;
  videoId?: string;
  routeLabel?: string;
};
```

Avoid rendering full external URLs in standalone HTML. If an external URL is stored internally, make sure Layer 3 validates rendered HTML, not internal metadata JSON.

### New worksheet blocks

Add block types to the worksheet schema rather than creating a new artifact:

```typescript
type VideoReferenceBlock = {
  type: "video_reference";
  title: string;
  speaker?: string;
  sourceLabel?: string;
  duration?: string;
  proficiencyLevel?: string;
  instruction: string;
};

type RouteMapBlock = {
  type: "route_map";
  stations: Array<{ id: string; code: string; label: string; color?: string }>;
};

type FillableTableBlock = {
  type: "fillable_table";
  id: string;
  columns: string[];
  initialRows: number;
  placeholders?: string[];
  allowAddRows?: boolean;
};

type ChecklistBlock = {
  type: "checklist";
  items: string[];
};
```

### Section shape

The reference’s stations can be represented as worksheet sections with station metadata:

```typescript
type VideoStationSection = {
  id: string;
  code: string;
  title: string;
  subtitle?: string;
  timeEstimate?: string;
  accent?: string;
  blocks: WorksheetBlock[];
};
```

---

## 6. Implementation Work

### Minimal system-conforming path

| Phase | Work | Files |
|---|---|---|
| P0 | Extend worksheet schema with video-reference, route-map, fillable-table, checklist blocks | `packages/renderer/src/contracts/schemas/worksheet.ts`, `packages/renderer/src/contracts/worksheet.ts` |
| P1 | Add Eta components for new worksheet blocks | `packages/renderer/templates/components/video_reference.html`, `route_map.html`, `fillable_table.html`, `checklist.html` |
| P1 | Route new block types through the dispatcher | `packages/renderer/templates/components/dispatcher.html` |
| P2 | Expand worksheet page from simple question list to block-driven station layout | `packages/renderer/templates/pages/worksheet.html` |
| P2 | Update worksheet sanitizer allowlist for chosen form controls and safe inline behavior | `packages/renderer/src/sanitizer/configs/worksheet.ts` |
| P2 | Add video-worksheet generation rules to Content Creator prompt | `packages/agents/sub_agents/content_creator/prompts/system.md` |
| P3 | Add renderer and quality tests for no external assets, brand string, print layout, dynamic controls | `packages/renderer/__tests__/`, `packages/quality/tests/` |

Estimated effort: about 4-6 focused engineering days for the system-conforming version, assuming no YouTube iframe exception.

### If product requires embedded video

This becomes a larger architecture decision, not a template task. It requires:

- ADR documenting an exception to INVARIANT-04
- artifact-aware Layer 3 external asset policy
- sanitizer iframe allowlist restricted to approved video hosts
- preview CSP changes from `frame-src 'none'`
- privacy/consent UX for third-party media
- offline fallback behavior

This path should not be mixed into the first implementation.

---

## 7. Quality Gate Impact

| Gate | Current fit | Required change |
|---|---|---|
| Layer 1 schema | `ArtifactContent.sections` is flexible enough, but renderer schema should be typed | Add/extend TS worksheet block schemas; optionally mirror in Python contracts later |
| Layer 2 pedagogy | Generic metrics are stubs; methodology gate pattern exists | Add video-learning methodology checks only if lesson plan declares a video-learning tag |
| Layer 3 HTML | Correctly blocks current reference HTML | No change if using video-reference metadata; change only for iframe exception path |
| Layer 4 judge | Artifact-agnostic | No change |
| Layer 5 teacher gate | Artifact-agnostic | No change |
| Layer 6 export | HTML currently requires `lesson`, not `worksheet`, in `packages/quality/layer6_export/export_validator.py` | If standalone worksheet HTML is a supported output, format requirements should accept `worksheet` for `html` |

Layer 6 is the one non-obvious pipeline gap: the validator currently says `html` requires a `lesson` artifact. If this use case is generated as a standalone worksheet only, export readiness should allow `worksheet` for HTML export.

---

## 8. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---:|---:|---|
| Teacher expects embedded YouTube playback | Medium | High | State product policy clearly: standalone pack references video but does not embed external media |
| LLM emits raw HTML or external links | Medium | High | Add prompt rules and Layer 3 tests; fail closed on rendered `http(s)://` |
| `contenteditable` accessibility gaps | Medium | Medium | Prefer `<textarea>`; if contenteditable is retained, enforce ARIA labels and keyboard/focus tests |
| Worksheet template grows too broad | Medium | Medium | Keep block components small and dispatcher-based |
| Browser-side export diverges from official export pipeline | Medium | Low | Treat client export as convenience; official export remains server-rendered artifact packaging |

---

## 9. Recommendation

Implement this use case as a **video-learning worksheet profile** over the existing `worksheet` artifact.

Do:

1. Keep `artifact_type="worksheet"`.
2. Add block-level support for `video_reference`, `route_map`, `fillable_table`, and `checklist`.
3. Render video as offline-safe reference metadata, not as an iframe.
4. Remove Google Fonts and use theme/system fonts or inline self-hosted fonts only if size is acceptable.
5. Add `oh-my-class` branding in the rendered document.
6. Extend Content Creator prompt with a “learning via video” worksheet structure.
7. Update HTML export readiness if standalone worksheet HTML is intended without a lesson artifact.

Do not:

1. Import the reference HTML directly as raw output.
2. Add a new artifact type before proving worksheet extension is insufficient.
3. Bypass Layer 3 external asset hard blocks for YouTube in the first implementation.
4. Rely on `contenteditable` where a native form control is enough.

**Bottom line**: The system can support the learning-via-video use case well, but only by translating the reference into structured worksheet JSON and invariant-compliant Eta components. It cannot safely ship the current HTML template unchanged.

---

## Appendix: Key File References

| File | Relevance |
|---|---|
| `docs/templates/learning-via-video-template.html` | Source reference; contains the seven-station worksheet, external assets, iframe, inline JS |
| `common/contracts/artifact.py` | Canonical `ArtifactContent` contract and artifact type list |
| `packages/renderer/src/contracts/index.ts` | Renderer `ArtifactDataMap` registry |
| `packages/renderer/src/contracts/worksheet.ts` | Current minimal worksheet renderer contract |
| `packages/renderer/src/contracts/schemas/worksheet.ts` | Richer worksheet schema surface for block extension |
| `packages/renderer/templates/pages/worksheet.html` | Current worksheet page, only 51 lines and question-list oriented |
| `packages/renderer/templates/pages/lesson.html` | Rich template precedent with sidebar/hero/component sections |
| `packages/renderer/templates/components/dispatcher.html` | Component routing pattern to extend |
| `packages/renderer/templates/components/film_card.html` | Existing film activity component pattern |
| `packages/renderer/src/sanitizer/base-config.ts` | Blocks external URLs and non-data asset sources |
| `packages/renderer/src/sanitizer/configs/worksheet.ts` | Worksheet-specific sanitizer config to extend for safe controls |
| `packages/renderer/src/preview-server/csp.ts` | Preview CSP currently uses `frame-src 'none'` and sandbox without downloads |
| `packages/quality/layer3_html/html_validator.py` | Hard-blocks external assets and missing brand string |
| `packages/quality/layer6_export/export_validator.py` | HTML export currently requires `lesson`; may need worksheet support |
| `packages/agents/graph.py` | Confirms ContentCreator is wired into the pipeline |
| `packages/agents/sub_agents/content_creator/prompts/system.md` | Prompt extension point for learning-via-video worksheet generation |
