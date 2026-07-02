# Kiến trúc chi tiết module `packages/renderer/`

> Mỗi module: **khi nào trigger** → **có những function gì** → **gọi những gì** → **data flow**.

---

## Mục lục

1. [Tổng quan kiến trúc](#1-tổng-quan-kiến-trúc)
2. [agent-worker.ts — Subprocess entry point](#2-agent-worker-ts)
3. [agent-renderer.ts — Bridge adapter](#3-agent-renderer-ts)
4. [agent-component-projection.ts — Teacher/student projection](#4-agent-component-projection-ts)
5. [renderer.ts — Public API (Luồng A)](#5-renderer-ts)
6. [artifact-ui/renderer.ts — Public API (Luồng B)](#6-artifact-ui-renderer-ts)
7. [artifact-ui/registry.ts — Family registry](#7-artifact-ui-registry-ts)
8. [artifact-ui/loader.ts — CSS loader](#8-artifact-ui-loader-ts)
9. [artifact-ui/adapters/ — Contract adapters](#9-artifact-ui-adapters)
10. [eta-engine.ts — Template engine singleton](#10-eta-engine-ts)
11. [theme/loader.ts — Brand theme loader](#11-theme-loader-ts)
12. [theme/generator.ts — CSS generator](#12-theme-generator-ts)
13. [theme/tokens.ts — Token types](#13-theme-tokens-ts)
14. [sanitizer/index.ts — DOMPurify pipeline](#14-sanitizer-index-ts)
15. [sanitizer.ts — Legacy regex sanitizer](#15-sanitizer-ts)
16. [semantic-anchor-projections.ts — Legacy wrapper](#16-semantic-anchor-projections-ts)
17. [inverse-thinking-renderer.ts — Legacy wrapper](#17-inverse-thinking-renderer-ts)
18. [contracts/ — Typed data shapes](#18-contracts)
19. [inline-assets.ts — Asset inlining](#19-inline-assets-ts)
20. [preview-server/ — Sandboxed preview](#20-preview-server)
21. [exporters/ — QTI JSON export](#21-exporters)
22. [diagrams/ — SVG sanitizer](#22-diagrams)
23. [scoring/ — Question scoring](#23-scoring)
24. [design-kit/ — Theme extraction](#24-design-kit)
25. [Cross-cutting: Dependency graph](#25-cross-cutting-dependency-graph)

---

## 1. Tổng quan kiến trúc

```
                        EXTERNAL CALLERS
       ┌──────────────────┬──────────────────────┬──────────────────┐
       │                  │                      │                  │
       ▼                  ▼                      ▼                  ▼
  renderer_pool.py   vocabulary-batch/    quality gates        apps/web/
  (Python subproc)   (TS exporter)        (TS quality)        (Next.js)
       │                  │                      │                  │
       │ stdin/stdout     │ import               │ import           │ import
       │ JSON             │                      │                  │
       ▼                  ▼                      ▼                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     RENDERER PACKAGE BOUNDARY                          │
│                                                                        │
│  ┌─────────────┐   ┌──────────────────┐   ┌────────────────────────┐  │
│  │ agent-worker │   │ agent-renderer   │   │ semantic-anchor-       │  │
│  │ (subprocess  │──▶│ (bridge:         │   │ projections.ts         │  │
│  │  entry)      │   │  ArtifactContent │   │ (69 LOC → renderArtif  │  │
│  │              │   │  → typed data)   │   │  actUi)                │  │
│  └─────────────┘   └────────┬─────────┘   └───────────┬────────────┘  │
│                              │                         │               │
│  ┌───────────────────────────┼─────────────────────────┘               │
│  │                           │                                         │
│  │   ┌───────────────────────▼───────────────────────┐                │
│  │   │            PUBLIC API (renderer.ts)            │                │
│  │   │                                                │                │
│  │   │  renderArtifact<T>()    renderArtifactUi()     │                │
│  │   │  renderArtifactSync()   renderArtifactUiSet()  │                │
│  │   └───────────┬──────────────────┬─────────────────┘                │
│  │               │                  │                                   │
│  │    ┌──────────▼──────┐  ┌───────▼──────────────┐                   │
│  │    │ theme/loader    │  │ artifact-ui/          │                   │
│  │    │ loadTheme()     │  │  ├ registry.ts        │                   │
│  │    │ ┌─ generator   │  │  ├ loader.ts           │                   │
│  │    │ ├─ tokens.ts   │  │  ├ adapters/*          │                   │
│  │    │ └─ cache       │  │  ├ interactivity.js    │                   │
│  │    └─────────────────┘  │  └ cache               │                   │
│  │               │          └───────────┬────────────┘                   │
│  │               │                      │                               │
│  │    ┌──────────▼──────────────────────▼────────────┐                  │
│  │    │         eta-engine.ts (singleton)              │                  │
│  │    │  eta.renderAsync(templatePath, data)           │                  │
│  │    └──────────────────┬────────────────────────────┘                  │
│  │                       │                                               │
│  │    ┌──────────────────▼────────────────────────────┐                  │
│  │    │              TEMPLATES (templates/)              │                  │
│  │    │  pages/quiz.html, pages/drill.html, ...         │                  │
│  │    │  artifact/navy-ticket/teaching.teacher.html     │                  │
│  │    │  components/question_mc.html, hint_box.html ... │                  │
│  │    └──────────────────┬────────────────────────────┘                  │
│  │                       │                                               │
│  │    ┌──────────────────▼────────────────────────────┐                  │
│  │    │              SANITIZER PIPELINE                 │                  │
│  │    │  sanitize(html, type)  ← Luồng A               │                  │
│  │    │  sanitizeArtifactUi(html)  ← Luồng B           │                  │
│  │    │  └ configs/quiz.ts, configs/lesson.ts, ...     │                  │
│  │    └────────────────────────────────────────────────┘                  │
│  │                                                                        │
│  └────────────────────────────────────────────────────────────────────────┘
│                                    │                                      │
│                                    ▼                                      │
│                            STANDALONE HTML                                │
│                     (CSS inline, JS inline, zero CDN)                    │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. agent-worker.ts

> **Khi nào trigger:** Gateway spawn subprocess `node --worker`. Worker loop đọc stdin, render, ghi stdout.

### Entry point

```typescript
// Khi chạy với --worker flag:
if (process.argv.includes("--worker")) {
  await runWorkerLoop();   // ← stdin/stdout JSON loop
}
```

### Functions

| Function | Trigger | Gọi | Trả về |
|----------|---------|-----|--------|
| `runWorkerLoop()` | Subprocess startup | `renderWorkerRequest()` per line | void (writes stdout) |
| `renderWorkerRequest(raw: string)` | Mỗi dòng JSON từ stdin | `parseWorkerRequest()` → `assertCompatibleVersion()` → `renderAgentArtifact()` | `WorkerResponse {ok, html, error}` |
| `parseWorkerRequest(value)` | `renderWorkerRequest` | `asRecord()` → `asString()` | `WorkerRequest` |
| `assertCompatibleVersion(req)` | `renderWorkerRequest` | — | void (throws nếu version mismatch) |

### Data flow

```
stdin: {"renderer_version":"0.1.0","template_version":"0.1.0","artifact":{...}}
  │
  ▼ parseWorkerRequest()
WorkerRequest { renderer_version, template_version, artifact }
  │
  ▼ assertCompatibleVersion()  ← throws nếu version ≠ "0.1.0"
  │
  ▼ renderAgentArtifact(request.artifact)
  │   └→ see §3 (agent-renderer.ts)
  │
  ▼ stdout: {"ok":true,"html":"<!DOCTYPE html>..."}
```

### Constants

- `RENDERER_VERSION = "0.1.0"` — checked against `WorkerRequest.renderer_version`
- `TEMPLATE_VERSION = "0.1.0"` — checked against `WorkerRequest.template_version`

---

## 3. agent-renderer.ts

> **Khi nào trigger:** Gateway gọi `renderAgentArtifact(artifactContent)` qua subprocess bridge. Đây là **bridge adapter** — nhận `ArtifactContent` JSON (schema `common/schemas`), transform thành typed data, rồi dispatch đến đúng render function.

### Entry point

```typescript
export async function renderAgentArtifact(input: unknown): Promise<string>
```

### Dispatch table (switch artifact_type)

| `artifact_type` | Adapter function | Render target | Audience |
|-----------------|-----------------|---------------|----------|
| `"quiz"` | `quizData(artifact)` | `renderArtifact("quiz", data)` | — |
| `"worksheet"` | `worksheetData(artifact)` | `renderArtifact("worksheet", data)` | — |
| `"drill"` | `drillData(artifact)` | `renderArtifact("drill", data)` | — |
| `"recap"` | `recapData(artifact)` | `renderArtifact("recap", data)` | — |
| `"infographic"` | `infographicData(artifact)` | `renderArtifact("infographic", data)` | — |
| `"answer_key"` | `answerKeyData(artifact)` | `renderArtifactUi({family:"paper-dossier", kind:"answer-key", audience:"student"})` | student |
| default (lesson) | `lessonData(artifact)` | `renderArtifactUi({family:"paper-dossier", kind:"lesson", audience:"student"})` | student |

### Adapter functions detail

| Function | Input | Output type | Xử lý đặc biệt |
|----------|-------|-------------|-----------------|
| `common(artifact)` | `ArtifactRecord` | `{title, subject, gradeLevel, theme, lang}` | Extract từ metadata + accessibility |
| `lessonData(artifact)` | `ArtifactRecord` | `LessonData` | Filter `teacher_only`, extract objectives, build hero |
| `quizData(artifact)` | `ArtifactRecord` | `QuizData` | `optionList()` cho MC options, `quizAnswer()` + `quizExplanation()` |
| `drillData(artifact)` | `ArtifactRecord` | `DrillData` | Phân biệt MC vs fill dựa trên `section.type` |
| `worksheetData(artifact)` | `ArtifactRecord` | `WorksheetData` | Section-level questions hoặc fallback single question |
| `recapData(artifact)` | `ArtifactRecord` | `RecapData` | Simple concept → summary mapping |
| `infographicData(artifact)` | `ArtifactRecord` | `InfographicData` | Title → content mapping |
| `answerKeyData(artifact)` | `ArtifactRecord` | `AnswerKeyData` | `preserveComponents()` — giữ nguyên components cho teacher |

### Helper functions

| Function | Purpose | Gọi |
|----------|---------|-----|
| `asRecord(value)` | Cast unknown → Record | — |
| `asString(value, fallback)` | Safe string extraction | — |
| `asRecordArray(value)` | Cast unknown[] → Record[] | `asRecord()` per item |
| `optionList(optionsValue)` | Map {A,B,C,D} → `{label, text}[]` | `asString()` |
| `quizAnswer(section)` | Fallback chain: `answer → correct_answer → correctAnswer → ...` | `asString()` |
| `quizExplanation(section)` | Fallback chain: `explain → explanation → rationale` | `asString()` |

### Call chain

```
renderAgentArtifact(input)
  ├─ ArtifactContentSchema.parse(input)          ← Zod validation
  ├─ asString(artifact.artifact_type, "lesson")
  ├─ switch (artifactType)
  │    ├─ "quiz":       quizData(artifact)       → renderArtifact("quiz", data)
  │    ├─ "worksheet":  worksheetData(artifact)   → renderArtifact("worksheet", data)
  │    ├─ "drill":      drillData(artifact)       → renderArtifact("drill", data)
  │    ├─ "recap":      recapData(artifact)       → renderArtifact("recap", data)
  │    ├─ "infographic": infographicData(artifact) → renderArtifact("infographic", data)
  │    ├─ "answer_key": answerKeyData(artifact)   → renderArtifactUi({family:"paper-dossier", ...})
  │    └─ default:      lessonData(artifact)      → renderArtifactUi({family:"paper-dossier", ...})
  │
  ├─ lessonData() calls:
  │    ├─ common(artifact)
  │    ├─ asRecordArray(artifact.sections).filter(!teacher_only)
  │    ├─ sections.filter(type === "objective").map(content)
  │    └─ preserveStudentComponents(section)      ← see §4
  │
  └─ answerKeyData() calls:
       ├─ common(artifact)
       ├─ asRecordArray(artifact.sections)        ← KHÔNG filter teacher_only
       └─ preserveComponents(section)             ← teacher-safe, giữ nguyên
```

---

## 4. agent-component-projection.ts

> **Khi nào trigger:** Được gọi bởi `agent-renderer.ts` khi transform `ArtifactContent.sections[].components[]`. Quyết định component nào giữ nguyên (teacher) vs strip answer/explain (student).

### Functions

| Function | Trigger | Input | Output | Gọi |
|----------|---------|-------|--------|-----|
| `preserveComponents(section, fallbackId)` | answerKeyData() | `ArtifactRecord` | `ContentComponent[]` | `parseContentComponent()` per item |
| `preserveStudentComponents(section, fallbackId)` | lessonData() | `ArtifactRecord` | `ContentComponent[]` | `preserveComponents()` → `projectComponentForStudent()` per item |
| `projectComponentForStudent(component)` | `preserveStudentComponents` | `ContentComponent` | `ContentComponent` | Per-type strip logic |
| `parseContentComponent(component, sectionId)` | `preserveComponents` | `unknown` | `ContentComponent` | `isContentComponent()` → throw on unknown |
| `isContentComponent(value)` | `parseContentComponent` | `unknown` | `boolean` | Checks `KNOWN_COMPONENT_TYPE_SET` |

### Teacher vs Student projection rules

| Component type | Teacher (preserveComponents) | Student (preserveStudentComponents) |
|---------------|----------------------------|--------------------------------------|
| `question_card` | keeps `answer`, `explain`, `wrong_reasons` | strips all three |
| `question_list` | keeps nested question answers | strips nested answers |
| `roleplay_script` | keeps `answer_key`, `coaching_notes` | strips both |
| `active_recall_prompt` | keeps `reveal_answer`, `teacher_rationale` | strips both |
| `contrastive_pairs` | keeps `teacher_rationale` per row | strips per row |
| `heading`, `paragraph`, `callout`, etc. | pass-through | pass-through |

### Known component types (24 total)

```typescript
const KNOWN_COMPONENT_TYPES = [
  "heading", "paragraph", "callout", "table", "stat_grid", "pattern_grid",
  "trait_grid", "taxonomy_grid", "phase_timeline", "flow_step",
  "question_card", "question_list", "concept_map", "timeline", "alert",
  "vocab_cluster", "contrastive_pairs", "phrasal_verb_cluster",
  "film_clip_activity", "roleplay_script", "active_recall_prompt", "hw_list",
] as const
```

### Call chain

```
preserveStudentComponents(section, sectionId)
  │
  ├─ preserveComponents(section, sectionId)
  │    ├─ Array.isArray(section.components)?
  │    └─ map → parseContentComponent(component, sectionId)
  │         ├─ isContentComponent(component) → check type ∈ KNOWN_COMPONENT_TYPE_SET
  │         └─ throw UnknownContentComponentError if not
  │
  └─ map → projectComponentForStudent(component)
       ├─ "question_card"      → strip answer/explain/wrong_reasons
       ├─ "question_list"      → strip per-question answer/explain/wrong_reasons
       ├─ "roleplay_script"    → strip answer_key/coaching_notes
       ├─ "active_recall_prompt" → strip reveal_answer/teacher_rationale
       ├─ "contrastive_pairs"  → strip teacher_rationale per row
       └─ other 17 types       → pass-through
```

---

## 5. renderer.ts

> **Khi nào trigger:** Called by `agent-renderer.ts` cho quiz/worksheet/drill/recap/infographic. Also exports `renderArtifactUi` / `renderArtifactUiSet` re-exports.

### Public API

| Function | Signature | Trigger | Gọi chain |
|----------|-----------|---------|-----------|
| `renderArtifact<T>(type, data)` | `<T extends ArtifactType>(type: T, data: ArtifactDataMap[T]) → Promise<string>` | quiz/worksheet/drill/recap/infographic render | `loadTheme()` → `eta.renderAsync()` → `sanitize()` |
| `renderArtifactSync(data)` | `(data) → string` | Legacy backward compat (DEPRECATED) | `loadTheme()` → manual HTML string → `sanitizeHtml()` |
| `renderTemplate(templateStr, data)` | `(templateStr, data) → string` | Convenience helper | `eta.renderString()` |

### Render Artifact call chain

```
renderArtifact("quiz", quizData)
  │
  ├─ (data as any).theme ?? "default"
  ├─ (data as any).lang ?? "vi"
  │
  ├─ loadTheme(themeName)                     ← see §11
  │    └→ CSS string (e.g., ":root { --color-primary: #... }")
  │
  ├─ eta.renderAsync(`pages/quiz`, {
  │     ...data,      ← QuizData { title, questions, ... }
  │     themeCSS,     ← CSS string injected into <style>
  │     lang,         ← "vi" | "en"
  │   })
  │    └→ raw HTML string
  │
  └─ sanitize(html, "quiz")                   ← see §14
       └→ safe standalone HTML
```

### Re-exports (from renderer.ts barrel)

```typescript
export { renderSemanticAnchorProjection, renderSemanticAnchorProjectionSet }
  from "./semantic-anchor-projections.js";

export { renderArtifactUi, renderArtifactUiSet }
  from "./artifact-ui/renderer.js";

export type { ArtifactUiRenderRequest, ArtifactUiSetRequest, ArtifactUiSet, ... }
  from "./artifact-ui/renderer.js";
```

---

## 6. artifact-ui/renderer.ts

> **Khi nào trigger:** Called by `agent-renderer.ts` (lesson/answer_key), `semantic-anchor-projections.ts` (vocabulary), `inverse-thinking-renderer.ts` (thinking), `vocabulary-batch/index.ts` (export).

### Public API

| Function | Signature | Trigger | Gọi chain |
|----------|-----------|---------|-----------|
| `renderArtifactUi(request)` | `(ArtifactUiRenderRequest) → Promise<string>` | Luồng B render | See full chain below |
| `renderArtifactUiSet(request)` | `(ArtifactUiSetRequest) → Promise<ArtifactUiSet>` | Batch render 4 navy-ticket projections | `Promise.all([renderArtifactUi × 4])` |

### Request types (discriminated union)

| Request type | family | kind | audience | data field |
|-------------|--------|------|----------|-----------|
| `NavyTicketTeachingRequest` | `"navy-ticket"` | `"teaching"` | teacher / student | `cluster: SemanticAnchorCluster` |
| `NavyTicketPracticeRequest` | `"navy-ticket"` | `"practice"` | teacher / student | `cluster + practiceSet` |
| `PaperDossierLessonRequest` | `"paper-dossier"` | `"lesson"` | teacher / student | `data: LessonData` |
| `PaperDossierAnswerKeyRequest` | `"paper-dossier"` | `"answer-key"` | teacher / student | `data: AnswerKeyData` |
| `PaperDossierRootCauseRequest` | `"paper-dossier"` | `"root-cause-session"` | teacher / student | `data: RootCauseSessionData` |
| `TransitRouteRequest` | `"transit-route"` | `"video-route"` | teacher / student | `data: VideoRouteData` |
| `InvestigationFolderRequest` | `"investigation-folder"` | `"inverse-thinking"` | teacher / student | `data: InverseThinkingRenderInput` |

### Full render chain

```
renderArtifactUi(request)
  │
  ├─ getFamily(request.family)                ← see §7: validates family exists
  │    └→ throws nếu family unknown
  │
  ├─ loadArtifactCSS(request.family)           ← see §8: concatenated CSS
  │    └→ string: contract.css + family tokens + primitives + family components
  │
  ├─ buildTemplateData(request, css)            ← see §9: adapter dispatch
  │    ├─ navy-ticket + "teaching"
  │    │    └→ adaptNavyTicketTeaching(cluster, audience, css, lang)
  │    ├─ navy-ticket + "practice"
  │    │    └→ adaptNavyTicketPractice(cluster, practiceSet, audience, css, lang)
  │    ├─ paper-dossier + "lesson"
  │    │    └→ adaptLesson(data, css)
  │    ├─ paper-dossier + "answer-key"
  │    │    └→ adaptAnswerKey(data, css, getInteractivityJS())
  │    ├─ paper-dossier + "root-cause-session"
  │    │    └→ adaptRootCauseSession(data, audience, css, getInteractivityJS())
  │    ├─ transit-route
  │    │    └→ adaptVideoRoute(data, css)
  │    └─ investigation-folder
  │         └→ adaptInverseThinking(data, audience, css)
  │    └→ TemplateData { artifactUiCSS, interactivityJS?, ... }
  │
  ├─ templatePath(family, kind, audience)       ← path to Eta template
  │    ├─ navy-ticket: "artifact/navy-ticket/{kind}.{audience}.html"
  │    └─ others:      "artifact/{family}/{kind}.html"
  │
  ├─ eta.renderAsync(templatePath, templateData) ← see §10
  │    └→ raw HTML string
  │    └ throws nếu template not found
  │
  └─ sanitizeArtifactUi(raw)                    ← see §14
       └→ safe standalone HTML
```

### Interactivity.js loading

```typescript
// Module-level lazy load — once at first call, cached forever
let _interactivityJS: string | undefined;
function getInteractivityJS(): string {
  if (_interactivityJS === undefined) {
    _interactivityJS = readFileSync(
      join(__dirname, "../artifact-ui/interactivity.js"), "utf-8"
    );
  }
  return _interactivityJS;
}
// Used by: adaptAnswerKey, adaptRootCauseSession
// NOT used by: adaptLesson, adaptNavyTicket*, adaptVideoRoute, adaptInverseThinking
```

### renderArtifactUiSet call chain

```
renderArtifactUiSet({ cluster, practiceSet, lang })
  │
  └─ Promise.all([
       renderArtifactUi({ family:"navy-ticket", kind:"teaching", audience:"teacher", ... }),
       renderArtifactUi({ family:"navy-ticket", kind:"teaching", audience:"student", ... }),
       renderArtifactUi({ family:"navy-ticket", kind:"practice", audience:"teacher", ... }),
       renderArtifactUi({ family:"navy-ticket", kind:"practice", audience:"student", ... }),
     ])
  │
  └→ { teachingTeacher, teachingStudent, practiceTeacher, practiceStudent }
```

---

## 7. artifact-ui/registry.ts

> **Khi nào trigger:** Called by `renderArtifactUi()` để validate family ID và resolve metadata.

### Data structure

```typescript
export interface ArtifactFamily {
  readonly id: string;              // "navy-ticket"
  readonly kinds: readonly string[];// ["teaching", "practice"]
  readonly tokenFile: string;       // "tokens/navy-ticket.css"
  readonly familyFile: string;      // "families/navy-ticket.css"
  readonly templateDir: string;     // "navy-ticket"
  readonly adapterName: string;     // "navy-ticket"
}

export const ARTIFACT_FAMILIES: readonly ArtifactFamily[] = [
  { id: "navy-ticket",            kinds: ["teaching", "practice"], tokenFile: "tokens/navy-ticket.css",            familyFile: "families/navy-ticket.css",            templateDir: "navy-ticket",            adapterName: "navy-ticket" },
  { id: "paper-dossier",          kinds: ["lesson", "answer-key", "root-cause-session"], ... },
  { id: "transit-route",          kinds: ["video-route"], ... },
  { id: "investigation-folder",   kinds: ["inverse-thinking"], ... },
];

export type ArtifactFamilyId = (typeof ARTIFACT_FAMILIES)[number]["id"];
```

### Functions

| Function | Input | Output | Throws |
|----------|-------|--------|--------|
| `getFamily(familyId)` | `string` | `ArtifactFamily` | `Error: Unknown artifact UI family: "{id}". Known: navy-ticket, ...` |

### Call chain

```
getFamily("navy-ticket")
  └─ ARTIFACT_FAMILIES.find(f => f.id === "navy-ticket")
       ├─ found → return family object
       └─ not found → throw Error
```

---

## 8. artifact-ui/loader.ts

> **Khi nào trigger:** Called by `renderArtifactUi()` mỗi lần render. Cache Map đảm bảo CSS chỉ đọc file 1 lần.

### CSS loading order (contract → family tokens → primitives → family components)

```
loadArtifactCSS("navy-ticket")
  │
  ├─ _cache.get("navy-ticket")? → return cached (if hit)
  │
  ├─ readFileSync("tokens/contract.css")          ← --art-* base tokens
  ├─ readFileSync("tokens/navy-ticket.css")        ← family token overrides
  ├─ readFileSync("../primitives.css")             ← 7 cross-family primitives
  ├─ readFileSync("families/navy-ticket.css")      ← family component styles
  │
  ├─ concatenated = [contract, familyTokens, primitives, familyComponents].join("\n")
  ├─ _cache.set("navy-ticket", concatenated)
  │
  └→ return concatenated CSS string
```

### Functions

| Function | Trigger | Gọi | Output |
|----------|---------|-----|--------|
| `loadArtifactCSS(familyId)` | `renderArtifactUi()` | `readFileSync()` × 4, `_cache.get/set()` | concatenated CSS string |
| `clearArtifactCSSCache()` | Tests only | `_cache.clear()` | void |

### File read paths (relative to `artifact-ui/`)

| File | Purpose |
|------|---------|
| `tokens/contract.css` | Base `--art-*` design tokens (shared across all families) |
| `tokens/{family}.css` | Family-specific token overrides |
| `primitives.css` | Cross-family component primitives (art-card, art-badge, etc.) |
| `families/{family}.css` | Family-specific component styles |

---

## 9. artifact-ui/adapters/

> **Khi nào trigger:** Called by `buildTemplateData()` trong `artifact-ui/renderer.ts`. Mỗi adapter transform typed contract data → Eta template data.

### Adapter registry (index.ts)

```typescript
export {
  adaptNavyTicketTeaching,
  adaptNavyTicketPractice,
} from "./navy-ticket.js";

export { adaptLesson, adaptAnswerKey, adaptRootCauseSession } from "./paper-dossier.js";
export { adaptVideoRoute } from "./transit-route.js";
export { adaptInverseThinking } from "./investigation-folder.js";
```

### Per-adapter detail

#### navy-ticket.ts (124 LOC)

| Function | Input | Output key fields | Interactivity? |
|----------|-------|-------------------|----------------|
| `adaptNavyTicketTeaching(cluster, audience, css, lang)` | `SemanticAnchorCluster` | `{ artifactUiCSS, audience, cluster, lang, ... }` | No |
| `adaptNavyTicketPractice(cluster, practiceSet, audience, css, lang)` | `SemanticAnchorCluster + PracticeSet` | `{ artifactUiCSS, audience, cluster, practiceSet, lang, ... }` | No |

#### paper-dossier.ts (337 LOC — largest)

| Function | Input | Output key fields | Interactivity? |
|----------|-------|-------------------|----------------|
| `adaptLesson(data, css)` | `LessonData` | `{ artifactUiCSS, title, sections, sidebar, hero, ... }` | No |
| `adaptAnswerKey(data, css, interactivityJS)` | `AnswerKeyData` | `{ artifactUiCSS, title, sections, interactivityJS, ... }` | **Yes** (reveal) |
| `adaptRootCauseSession(data, audience, css, interactivityJS)` | `RootCauseSessionData` | `{ artifactUiCSS, title, sections, audience, interactivityJS, ... }` | **Yes** (toggle + jump) |

**Key transformations in paper-dossier.ts:**

- `adaptLesson()`: builds `sidebar` (stats + nav items), `hero` (eyebrow/lede/statCards/objectives), renders section components as pre-rendered HTML strings
- `adaptAnswerKey()`: injects `interactivityJS` for reveal toggle, builds answer items with component HTML
- `adaptRootCauseSession()`: injects `interactivityJS` for toggle + jump-to-target, builds directory nav + section content

#### transit-route.ts (101 LOC)

| Function | Input | Output key fields | Interactivity? |
|----------|-------|-------------------|----------------|
| `adaptVideoRoute(data, css)` | `VideoRouteData` | `{ artifactUiCSS, title, video, sections, ... }` | No |

#### investigation-folder.ts (97 LOC)

| Function | Input | Output key fields | Interactivity? |
|----------|-------|-------------------|----------------|
| `adaptInverseThinking(data, audience, css)` | `InverseThinkingRenderInput` | `{ artifactUiCSS, audience, frameVariant, steps, ... }` | No |

---

## 10. eta-engine.ts

> **Khi nào trigger:** Singleton — import once, used by both `renderer.ts` và `artifact-ui/renderer.ts`.

### Configuration

```typescript
export const eta = new Eta({
  views: path.resolve(__dirname, "../templates"),  // template root
  defaultExtension: ".html",                        // auto-append .html
  cache: process.env.NODE_ENV === "production",     // template caching in prod
  autoEscape: true,                                 // XSS Layer 1: < % = > escapes HTML entities
  useWith: false,                                   // data accessed via it. only, no global scope pollution
});
```

### Usage patterns

| Caller | Method | Example |
|--------|--------|---------|
| `renderArtifact()` | `eta.renderAsync(path, data)` | `eta.renderAsync("pages/quiz", { title, questions, themeCSS })` |
| `renderArtifactUi()` | `eta.renderAsync(path, data)` | `eta.renderAsync("artifact/navy-ticket/teaching.teacher.html", data)` |
| `renderTemplate()` | `eta.renderString(str, data)` | `eta.renderString("<h1><%= it.title %></h1>", { title })` |

### Template resolution

```
eta.renderAsync("pages/quiz")
  → views = templates/
  → resolves to templates/pages/quiz.html
  → defaultExtension: .html (already ends with .html, so no append)

eta.renderAsync("artifact/navy-ticket/teaching.teacher.html")
  → resolves to templates/artifact/navy-ticket/teaching.teacher.html
```

---

## 11. theme/loader.ts

> **Khi nào trigger:** Called by `renderArtifact()` (Luồng A). Load theme JSON → generate CSS custom properties. Cache theo tên theme.

### Theme file location

```typescript
const THEMES_DIR = existsSync(path.resolve(__dirname, "themes"))
  ? path.resolve(__dirname, "themes")          // dist/themes (built)
  : SOURCE_THEMES_DIR;                          // src/theme/themes (dev)
```

### Functions

| Function | Trigger | Gọi | Output |
|----------|---------|-----|--------|
| `loadTheme(name)` | `renderArtifact()` | `loadTokens(name)` → `generator.generate(tokens)` → cache | CSS string |
| `loadTokens(name)` | `loadTheme()` | `readFileSync()` + `JSON.parse()` | `ThemeTokens` |
| `clearThemeCache()` | Tests only | `_cache.clear()` | void |

### Load chain

```
loadTheme("default")
  │
  ├─ _cache.get("default")? → return cached
  │
  ├─ loadTokens("default")
  │    ├─ readFileSync("themes/default.json") → JSON.parse → ThemeTokens
  │    └ throws? → fallback to themes/default.json
  │
  ├─ generator.generate(tokens)
  │    └→ CSS string: ":root { --color-primary: #...; --color-bg: #...; ... }"
  │
  ├─ _cache.set("default", css)
  │
  └→ return CSS string
```

### Available themes

```
themes/
├── default.json
├── ocean.json
├── forest.json
└── high-contrast-dyslexia.json
```

---

## 12. theme/generator.ts

> **Khi nào trigger:** Called by `theme/loader.ts`. Converts `ThemeTokens` → CSS custom properties string.

### Class: `ThemeCSSGenerator`

| Method | Input | Output | Logic |
|--------|-------|--------|-------|
| `generate(tokens)` | `ThemeTokens` | `string` | Maps token tiers → CSS variables |

### Token tiers

```
PrimitiveTokens        → SemanticTokens          → ComponentTokens
(raw hex values)        (meaning)                (scoped to component)

--color-blue-500   →   --color-primary      →   .quiz-option { border-color: var(--color-primary) }
--space-4          →   --space-md
--font-size-base   →   --text-body
```

---

## 13. theme/tokens.ts

> **Type definitions only — no runtime code.**

```typescript
export interface PrimitiveTokens {
  // raw color/space/font values
  [key: string]: string;
}

export interface SemanticTokens {
  // meaning: primary, secondary, bg, text, border, ...
  [key: string]: string;
}

export interface ComponentTokens {
  // scoped: quiz-option, lesson-hero, drill-timer, ...
  [key: string]: string;
}

export interface ThemeTokens {
  primitives: PrimitiveTokens;
  semantic: SemanticTokens;
  components?: ComponentTokens;
}
```

---

## 14. sanitizer/index.ts

> **Khi nào trigger:** Called as final step in both `renderArtifact()` (Luồng A) và `renderArtifactUi()` (Luồng B). XSS Layer 2.

### Per-type config map

```typescript
const CONFIG_MAP: Record<ArtifactType, IOptions> = {
  lesson:          LESSON_CONFIG,
  quiz:            QUIZ_CONFIG,
  drill:           DRILL_CONFIG,
  worksheet:       WORKSHEET_CONFIG,
  recap:           RECAP_CONFIG,
  infographic:     INFOGRAPHIC_CONFIG,
  answer_key:      ANSWER_KEY_CONFIG,
  flashcard_deck:  FLASHCARD_DECK_CONFIG,
  reading_passage: READING_PASSAGE_CONFIG,
  exit_ticket:     EXIT_TICKET_CONFIG,
  teaching_pack:   BASE_CONFIG,
  roadmap:         ROADMAP_CONFIG,
};
```

### Functions

| Function | Trigger | Input | Logic |
|----------|---------|-------|-------|
| `sanitize(html, type)` | `renderArtifact()` | full HTML string + ArtifactType | Extract `<body>`, sanitize body content only, reassemble |
| `sanitizeArtifactUi(html)` | `renderArtifactUi()` | full HTML string | Same body-extraction pattern, uses `ARTIFACT_UI_CONFIG` |

### Sanitize logic

```
sanitize(html, "quiz")
  │
  ├─ html.match(/(<body[^>]*>)([\s\S]*)(<\/body>)/i)
  │    ├─ bodyMatch found → extract body content only
  │    │    └─ sanitizeHtmlLib(bodyContent, QUIZ_CONFIG)
  │    │    └─ reassemble: <body>{sanitized}</body>
  │    └─ no bodyMatch → fragment mode
  │         ├─ preserve DOCTYPE if present
  │         └─ sanitizeHtmlLib(fullString, QUIZ_CONFIG)
  │
  └→ sanitized HTML string
```

### sanitizeArtifactUi (artifact-ui path)

```typescript
export function sanitizeArtifactUi(html: string): string {
  const bodyMatch = html.match(/(<body[^>]*>)([\s\S]*)(<\/body>)/i);
  if (bodyMatch) {
    const sanitizedBody = sanitizeHtmlLib(bodyMatch[2], ARTIFACT_UI_CONFIG);
    return html.replace(bodyMatch[0], `${bodyMatch[1]}${sanitizedBody}${bodyMatch[3]}`);
  }
  const doctypeMatch = html.match(/^(<!DOCTYPE[^>]*>)\s*/i);
  const doctype = doctypeMatch ? doctypeMatch[1] : "";
  const body = doctypeMatch ? html.slice(doctypeMatch[0].length) : html;
  const sanitized = sanitizeHtmlLib(body, ARTIFACT_UI_CONFIG);
  return doctype ? `${doctype}\n${sanitized}` : sanitized;
}
```

### Config files in `sanitizer/configs/`

| Config | Allowed tags (examples) | Special rules |
|--------|------------------------|---------------|
| `quiz.ts` | `<h1-h6>`, `<p>`, `<ul/ol/li>`, `<strong/em>`, `<table>` | No `<video>`, no `class="art-*"` |
| `lesson.ts` | `<h1-h6>`, `<p>`, `<section>`, `<aside>`, `<table>`, `<details>` | Broader content tags |
| `drill.ts` | Similar to quiz | Allow `<input>` for fill-blank |
| `worksheet.ts` | `<h1-h6>`, `<p>`, `<table>`, `<pre/code>` | Allow `<code>` blocks |
| `recap.ts` | `<h1-h6>`, `<p>`, `<ul/ol/li>` | Simple content |
| `infographic.ts` | `<h1-h6>`, `<p>`, `<svg>`, `<img>` | Allow SVG for visuals |
| `answer_key.ts` | `<h1-h6>`, `<p>`, `<details/summary>` | Allow toggle elements |
| `artifact-ui.ts` | All standard + `data-*`, `aria-*` attributes | **Allows `data-toggle-reveal`, `data-jump-target`, `data-mode-toggle`** |
| `flashcard_deck.ts` | `<h1-h6>`, `<p>`, `<dl/dt/dd>` | Definition lists for cards |
| `roadmap.ts` | `<h1-h6>`, `<p>`, `<ol/li>`, `<table>` | Ordered lists for roadmap |

---

## 15. sanitizer.ts

> **Legacy sanitizer — kept for `renderArtifactSync()` backward compatibility.**

### Function

```typescript
export function sanitizeHtml(html: string): string
```

### Regex-based stripping (no DOM, no library)

```typescript
// 1. Remove <script>...</script> (including multiline)
const SCRIPT_BLOCK_RE = /<script\b[^>]*>[\s\S]*?<\/script\s*>/gi;

// 2. Remove self-closing <script ... />
const SCRIPT_SELF_CLOSE_RE = /<script\b[^>]*\/>/gi;

// 3. Remove <iframe>, <object>, <embed> (open, close, or self-close)
const DANGEROUS_TAG_RE = /<\/?\s*(?:iframe|object|embed)\b[^>]*\/?>/gi;

// 4. Remove inline event handlers: onclick="...", onerror="..."
const EVENT_HANDLER_RE = /\s+on[a-z]\w*\s*=\s*(?:"[^"]*"|'[^']*'|[^\s/>]*)/gi;
```

---

## 16. semantic-anchor-projections.ts

> **Legacy wrapper — 69 LOC.** Called by `vocabulary-batch/index.ts` (export) và re-exported từ `renderer.ts`. Now delegates to `renderArtifactUi()`.

### Functions

| Function | Trigger | Gọi | Output |
|----------|---------|-----|--------|
| `renderSemanticAnchorProjection(request)` | vocabulary-batch export | `renderArtifactUi({family:"navy-ticket", ...})` | `Promise<string>` |
| `renderSemanticAnchorProjectionSet(cluster, practiceSet, lang)` | vocabulary-batch export | `renderArtifactUiSet({cluster, practiceSet, lang})` | `Promise<ArtifactUiSet>` |

---

## 17. inverse-thinking-renderer.ts

> **Legacy wrapper — 67 LOC.** Called by quality gates và test files. Delegates to `renderArtifactUi()`.

### Functions

| Function | Trigger | Gọi | Output |
|----------|---------|-----|--------|
| `renderInverseThinkingHtml(input, audience)` | quality gates, tests | `renderArtifactUi({family:"investigation-folder", kind:"inverse-thinking", ...})` | `Promise<string>` |

---

## 18. contracts/

> **Type definitions — input shapes cho renderers.** No runtime code, pure interfaces.

### Contract files

| File | Interface | Used by |
|------|-----------|---------|
| `lesson.ts` | `LessonData`, `LessonSection`, `VocabEntry`, `LessonSidebar`, `LessonHero` | `agent-renderer.ts`, `paper-dossier.ts` adapter |
| `quiz.ts` | `QuizData`, `MCQuestion` | `agent-renderer.ts` |
| `drill.ts` | `DrillData` | `agent-renderer.ts` |
| `recap.ts` | `RecapData` | `agent-renderer.ts` |
| `infographic.ts` | `InfographicData` | `agent-renderer.ts` |
| `worksheet.ts` | `WorksheetData`, `WorksheetSection` | `agent-renderer.ts` |
| `answer_key.ts` | `AnswerKeyData` | `agent-renderer.ts`, `paper-dossier.ts` |
| `root-cause-session.ts` | `RootCauseSessionData` | `paper-dossier.ts` |
| `video-route.ts` | `VideoRouteData` | `transit-route.ts` |
| `components.ts` | `ContentComponent` (24-variant discriminated union) | `agent-component-projection.ts` |
| `index.ts` | `ArtifactDataMap`, `ArtifactType` | `renderer.ts`, `agent-renderer.ts` |

### ArtifactDataMap dispatch

```typescript
export interface ArtifactDataMap {
  lesson:          LessonData;
  quiz:            QuizData;
  drill:           DrillData;
  worksheet:       WorksheetData;
  recap:           RecapData;
  infographic:     InfographicData;
  answer_key:      AnswerKeyData;
  flashcard_deck:  FlashcardDeckData;
  reading_passage: ReadingPassageData;
  exit_ticket:     ExitTicketData;
  roadmap:         RoadmapData;
  teaching_pack:   TeachingPackData;
}

export type ArtifactType = keyof ArtifactDataMap;
```

---

## 19. inline-assets.ts

> **Asset inlining utility.** Converts external references → inline data URIs cho standalone HTML.

### Functions

| Function | Purpose | Gọi |
|----------|---------|-----|
| `inlineAssets(html)` | Scan HTML for `src="http..."` → fetch + base64 inline | HTTP fetch, Buffer |
| `inlineCss(css)` | Inline `@import url(...)` → embed CSS content | HTTP fetch |

### Usage

Called by preview-server để ensure all assets inline trước khi serve.

---

## 20. preview-server/

> **Sandboxed HTML preview server.** Wraps rendered HTML in `<iframe sandbox>` + CSP headers.

### Files

| File | Responsibility |
|------|---------------|
| `index.ts` | HTTP server setup, route mounting |
| `router.ts` | `GET /preview/:runId/:artifactId` → fetch from store → wrap → serve |
| `store.ts` | `PreviewStore` class: Map<runId, Map<artifactId, html>> |
| `iframe-wrapper.ts` | Wraps HTML in `<iframe sandbox="allow-scripts">` |
| `csp.ts` | Content-Security-Policy headers: `default-src 'self'; script-src 'none'` |

### Preview flow

```
Browser → GET /preview/{runId}/{artifactId}
  │
  ├─ router.ts: extract runId, artifactId from params
  ├─ PreviewStore.get(runId, artifactId) → html string
  ├─ iframeWrapper.wrap(html) → <iframe sandbox="allow-scripts">{html}</iframe>
  ├─ csp.ts: set Content-Security-Policy header
  │    default-src 'self'; script-src 'none'
  └→ return wrapped HTML response
```

---

## 21. exporters/

> **Non-HTML export formats** — QTI XML, JSON dump.

### Exporters

| Directory | Format | Key function |
|-----------|--------|-------------|
| `qti/` | QTI 2.1 XML (LMS) | `exportQTI(artifacts)` |
| `qti/serializers/` | Per-question-type QTI serializers | choice, fill-gap, match, order, open, interactive, multimedia, text-entry |
| `json/` | JSON dump | `exportJSON(artifacts)` |
| `variant-generator/` | Quiz variant generation | `generateVariant(quiz, options)` |

---

## 22. diagrams/

> **Inline SVG rendering + sanitization.**

| File | Purpose |
|------|---------|
| `index.ts` | Public API: `renderDiagram(svgContent)` |
| `svg-sanitizer.ts` | Strip `<script>`, event handlers from SVG, keep `<path>`, `<circle>`, etc. |

---

## 23. scoring/

> **Question scoring strategies** — used by quiz/drill rendering.

| File | Strategy |
|------|----------|
| `strategies/all-or-nothing.ts` | Full points if all correct, 0 otherwise |
| `strategies/partial-credit.ts` | Points proportional to correct answers |
| `strategies/rubric.ts` | Rubric-based scoring (essay, open-ended) |
| `strategies/vietnamese-tf-2025.ts` | QĐ 764 scoring: 1 TF item = 0.1đ, 2 = 0.25đ, 3 = 0.5đ, 4 = 1.0đ |
| `types.ts` | `ScoringStrategy` interface |

---

## 24. design-kit/

> **Brand theme extraction (LLM-driven).** Experimental module.

| File | Purpose |
|------|---------|
| `extractor.ts` | Extract brand colors/fonts from reference images |
| `llm-extractor.ts` | LLM-powered brand extraction (sends images to GPT-4V) |
| `mapper.ts` | Map extracted values → `ThemeTokens` |
| `proposer.ts` | Propose theme variants (light/dark/high-contrast) |
| `validator.ts` | Validate proposed theme meets accessibility standards |
| `index.ts` | Public API: `extractTheme(source)` |

---

## 25. Cross-cutting: Dependency graph

### Module dependency matrix (what imports what)

```
agent-worker.ts
  └→ agent-renderer.ts

agent-renderer.ts
  ├→ @oh-my-class/schemas (ArtifactContentSchema)
  ├→ agent-component-projection.ts
  ├→ renderer.ts (renderArtifact)
  └→ artifact-ui/renderer.ts (renderArtifactUi)

renderer.ts
  ├→ eta-engine.ts
  ├→ contracts/index.ts (ArtifactDataMap, ArtifactType)
  ├→ theme/loader.ts (loadTheme)
  ├→ sanitizer.ts (sanitizeHtml) — legacy path
  ├→ sanitizer/index.ts (sanitize) — modern path
  └→ re-exports: semantic-anchor-projections.ts, artifact-ui/renderer.ts

artifact-ui/renderer.ts
  ├→ eta-engine.ts
  ├→ sanitizer/index.ts (sanitizeArtifactUi)
  ├→ artifact-ui/loader.ts (loadArtifactCSS)
  ├→ artifact-ui/registry.ts (getFamily)
  ├→ artifact-ui/adapters/* (adaptXxx)
  ├→ contracts/lesson.ts, answer_key.ts, root-cause-session.ts, video-route.ts
  ├→ inverse-thinking-renderer.ts (type only)
  └→ @oh-my-class/schemas (SemanticAnchorCluster, PracticeSet)

artifact-ui/adapters/*
  ├→ contracts/* (typed data input)
  └→ agent-component-projection.ts (preserveComponents for some)

theme/loader.ts
  ├→ theme/generator.ts (ThemeCSSGenerator)
  ├→ theme/tokens.ts (ThemeTokens)
  └→ theme/themes/*.json (theme files)

eta-engine.ts
  └→ eta (npm package)

sanitizer/index.ts
  ├→ sanitizer/base-config.ts
  ├→ sanitizer/configs/*.ts (per-type configs)
  └→ sanitize-html (npm package)
```

### Render call graph (who triggers whom)

```
services/gateway/renderer_pool.py
  │ stdin: JSON
  ▼
agent-worker.ts:runWorkerLoop()
  │
  ▼
agent-renderer.ts:renderAgentArtifact()
  │
  ├─ artifact_type ∈ {quiz, worksheet, drill, recap, infographic}
  │    │
  │    ▼
  │  renderer.ts:renderArtifact(type, data)
  │    ├─ theme/loader.ts:loadTheme(name)
  │    │    └→ theme/generator.ts:generate(tokens)
  │    │    └→ readFileSync("themes/{name}.json")
  │    ├─ eta-engine.ts:eta.renderAsync("pages/{type}", data)
  │    │    └→ templates/pages/{type}.html
  │    └─ sanitizer/index.ts:sanitize(html, type)
  │         └→ sanitize-html library
  │
  └─ artifact_type ∈ {lesson, answer_key}
       │
       ▼
     artifact-ui/renderer.ts:renderArtifactUi(request)
       ├─ artifact-ui/registry.ts:getFamily(familyId)
       ├─ artifact-ui/loader.ts:loadArtifactCSS(family)
       │    └→ readFileSync × 4 (tokens/contract, tokens/{family}, primitives, families/{family})
       ├─ artifact-ui/adapters/{family}.ts:adaptXxx(data, css, ...)
       ├─ eta-engine.ts:eta.renderAsync("artifact/{family}/{kind}.html", templateData)
       │    └→ templates/artifact/{family}/{kind}.html
       └─ sanitizer/index.ts:sanitizeArtifactUi(html)
            └→ sanitize-html library

packages/exporters/vocabulary-batch/index.ts
  │
  ▼
semantic-anchor-projections.ts:renderSemanticAnchorProjectionSet()
  │
  ▼
artifact-ui/renderer.ts:renderArtifactUiSet()
  └→ Promise.all([renderArtifactUi × 4])
```
