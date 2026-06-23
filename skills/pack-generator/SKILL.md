# Pack Generator Skill

## Purpose
Generate structured JSON content for each artifact type, rendered via Eta templates into standalone HTML.

## Triggers
- "generate worksheet"
- "create quiz"
- "make a teaching pack"
- "generate HTML artifacts"

## Workflow
1. Receive ArtifactContent JSON from content creator agent
2. Select appropriate Eta template based on artifact_type
3. Inject theme CSS (from branding/theme_{name}.css)
4. Render via Eta template engine
5. Sanitize HTML (DOMPurify)
6. Validate no external assets (INVARIANT-04)
7. Output: standalone HTML file

## Constraints
- All CSS inlined — no `<link rel="stylesheet">`
- System font stack only (zero weight)
- Images: inline SVG preferred; small bitmaps as base64 data URIs
- JS: minimal, inline, vanilla; no frameworks; no `eval()`
- Answer keys MUST be in `teacher_only` sections (INVARIANT-05)
- Brand string "oh-my-class" must appear in output (Layer 3 check)
- No CDN references anywhere in output
