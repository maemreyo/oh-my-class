# Export Assistant Skill

## Purpose
Generate export formats (GIFT, H5P, QTI) from ArtifactContent JSON.

## Triggers
- "export to Moodle"
- "generate GIFT"
- "create H5P package"
- "export quiz"

## Supported Formats

### Moodle GIFT (.txt)
- Simplest format. Line-oriented.
- Supports: MCQ, TF, short answer, matching, numerical, essay, missing word
- Partial credit via `%50%` syntax
- Category: `$CATEGORY: oh-my-class/{subject}/{topic}`

### H5P (.h5p ZIP)
- Richest interactivity.
- Bundle: `h5p.json` + `content/content.json` + library files
- Key types: H5P.MultiChoice, H5P.Blanks, H5P.DragText, H5P.Summary, H5P.Flashcards
- Generate only `content/content.json`

### QTI 2.1 (XML ZIP)
- Most interoperable standard (1EdTech). Export-only.
- Structure: `imsmanifest.xml` + `assessments/test.xml` + `items/*.xml`
