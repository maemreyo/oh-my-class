# AI Educational Content Generation — Research Findings

> Compiled for "oh-my-class" architecture & schema design.
> Date: 2026-06-23

---

## TABLE OF CONTENTS

1. [AI in Education Frameworks & Platforms](#1-ai-in-education-frameworks--platforms)
   - 1.1 Production Systems (Khan Academy, Quizlet, Kahoot)
   - 1.2 Academic Research Papers
   - 1.3 Open-Source Implementations
2. [Pedagogical Frameworks for Content Structure](#2-pedagogical-frameworks-for-content-structure)
   - 2.1 Bloom's Taxonomy (Revised)
   - 2.2 Backward Design (UbD)
   - 2.3 Gagné's Nine Events of Instruction
3. [Educational Content Schemas](#3-educational-content-schemas)
   - 3.1 Lesson Plan Schema
   - 3.2 Quiz/Assessment Data Model
   - 3.3 Worksheet Structure Patterns
   - 3.4 Infographic Data Model
   - 3.5 Complete Teaching Pack Schema
4. [Quality Standards](#4-quality-standards)
   - 4.1 Academic Accuracy & Hallucination Detection
   - 4.2 Pedagogical Quality Rubrics
   - 4.3 Age-Appropriate Content Filtering
   - 4.4 WCAG for Educational HTML
   - 4.5 Vietnamese Education Context
5. [Export Formats](#5-export-formats)
   - 5.1 Moodle GIFT Format
   - 5.2 H5P Interactive Content
   - 5.3 QTI 2.1
   - 5.4 Google Forms API
   - 5.5 Format Comparison Matrix

---

## 1. AI in Education Frameworks & Platforms

### 1.1 Production Systems

#### Khan Academy — Khanmigo

| Aspect | Detail |
|---|---|
| **Architecture** | Multi-model: GPT-4o (tutoring), custom "Math Agent" for computation; Socratic prompting; Chain-of-Thought reasoning |
| **Key Features** | Socratic tutor (never gives answers), teacher dashboard, moderation layer, real-time math verification |
| **Pedagogical Approach** | Guided discovery via questioning; zone of proximal development; mastery-based progression |
| **Evaluation** | Rigorous A/B testing across 1.35M+ tutoring threads; 5.09% cognitive engagement lift from conversation log improvements |
| **Accuracy System** | Specialized Math Agent runs behind-the-scenes; Wolfram Alpha integration explored; textual representations of all graphics |
| **Scale** | 700K+ users in year 1; 380+ school districts; partnership with OpenAI |
| **Reference** | [Khan Academy Blog: How We Built AI Tutoring Tools](https://blog.khanacademy.org/how-we-built-ai-tutoring-tools/) |

Key finding: Khanmigo's architecture separates tutoring dialogue from computation — the "Math Agent" handles calculations while the LLM handles the Socratic conversation. This separation-of-concerns pattern is directly applicable to oh-my-class.

#### Quizlet — Q-Chat

| Aspect | Detail |
|---|---|
| **Architecture** | Concept Graph (300+ nodes/subject) × Knowledge State Tracker × Spaced Repetition × Socratic Prompting |
| **Core Model** | Socratic AI tutor: responds with questions, not answers. "Productive friction" |
| **Knowledge Modeling** | Each student tracked across concept hierarchy: mastery level, misconception patterns, knowledge stability |
| **Question Generation** | LSH-based clustering for 400M Q&A pairs; ranked by grade level, subject domain, similarity, quality score |
| **Formats** | Flashcards, practice tests, interactive experiences (Magic Notes); MCQ, fill-in-blank, Q&A, term/definition |
| **Key Differentiator** | Misconception Pattern Library — identifies specific false beliefs, designs targeted correction sequences |
| **Reference** | [Quizlet Blog: Q-Chat Launch](https://quizlet.com/blog/meet-q-chat) |

Key finding: Q-Chat's concept graph with 300+ nodes per subject and explicit misconception detection library is a powerful pattern for adaptive content generation.

#### Kahoot! — AI Question Generator

| Aspect | Detail |
|---|---|
| **Architecture** | Multi-model: Azure OpenAI GPT 3.5/4/5, Google Gemini 2.5 Pro, Apple Foundation Models, Perplexity.ai |
| **Generation Sources** | Topic text, PDF, Wikipedia article, URL, handwritten notes (VisionKit/ML Kit), Google Slides |
| **Question Types** | Quiz (MCQ), True/False, Slider, Type Answer |
| **Formats** | Quiz, Presentation, Micro lesson, Vocab review, Practice test, Question extractor, Brainstorm, Exit ticket |
| **Key Features** | AI image generation, semantic search across 1.9B user-generated questions, on-device AI (Apple Foundation Models) |
| **Reference** | [Kahoot! Trust Center: AI Features](https://trust.kahoot.com/ai-powered-features-in-kahoot/) |

### 1.2 Academic Research Papers

#### LessonPlanLM (2025)
- **Source**: Nature Humanities & Social Sciences Communications
- **Approach**: Knowledge-enhanced LLM with 100K+ real-world lesson plans in LPKB (Lesson Plan Knowledge Base)
- **Key Innovation**: RAFT (Retrieval-Augmented Fine-Tuning) + step-by-step structural generation
- **Evaluation Framework**: Four perspectives — structural integrity, logical coherence, content accuracy, pedagogical alignment
- **Code**: https://github.com/ai4ed/LessonPlan

#### Self-Critique Prompting for Lesson Plans (AIED 2024)
- **Approach**: Three-stage: RAG → Self-critique → Refinement
- **Domain**: Math grades 2-5, 80+ topics
- **Result**: Human evaluation showed quality comparable to teacher-crafted plans

#### LessonPlan Alignment with Bloom's Taxonomy via XAI (2025)
- **Approach**: Multi-task transformer classifier + GPT generator conditioned on Bloom levels
- **Metrics**: F1-score 91.8% for Bloom classification; expert rating 4.43/5 for pedagogical alignment
- **Key Innovation**: SHAP-based token-level explanations for transparency

#### EduPlanner — Multi-Agent System
- **Approach**: Evaluator Agent + Optimizer Agent + Question Analyst in adversarial collaboration
- **Key Innovation**: Skill-Tree structure to model student knowledge; CIDDP 5-dimension evaluation (Clarity, Integrity, Depth, Practicality, Pertinence)
- **Code**: https://github.com/Zc0812/Edu_Planner

#### TeachPlanAlign (2026)
- **Approach**: Dual-profile (teacher + class) personalization via retrieval-augmented fine-tuning
- **Key Innovation**: Curriculum-grounded with explicit evidence citations; constraint-guided self-refinement loop
- **Evaluation**: Teacher-in-the-loop; reduced editing effort

#### COGENT (2025)
- **Approach**: Curriculum-oriented framework for grade-appropriate content
- **Key Components**: Science concepts, core ideas, learning objectives + readability control (length, vocabulary, sentence complexity) + "wonder-based" inquiry
- **Finding**: Properly guided LLMs can match or exceed human-written educational passages

#### AgentLesson (2025/2026)
- **Approach**: Multi-agent (Writer × Evaluator) using Gagné's Nine Events
- **Evaluation**: 5-dimension rubric (Clarity, Integrity, Depth, Practicality, Pertinence)
- **Result**: Multi-round agent collaboration significantly improves Depth and Pertinence

#### BloomXplain (AAAI-style)
- **Approach**: Generate + evaluate LLM explanations across Bloom's levels
- **Dataset**: STEM-focused QA pairs annotated with Bloom levels
- **Finding**: Explicit Bloom-level prompting (BAQ) outperforms inferred-level prompting

### 1.3 Open-Source Implementations

| Project | Stack | Key Features | Stars/Activity |
|---|---|---|---|
| **[LessonCraft](https://github.com/CheickDiakite-yikes/AI-Lessons-k12)** | Next.js 15, Gemini 2.5, Drizzle ORM, PostgreSQL | 7 plan lengths, 4 subjects, MA DESE standards, PDF export | New (Feb 2026) |
| **[Lessora AI](https://github.com/Javabutdif/Lessora-AI)** | React 18, Node.js/Express, MongoDB, GPT-4o-mini | DOC/PDF export, JWT auth, Zod validation | v1.0.7 (Jun 2026) |
| **[Claw-ED](https://github.com/SirhanMacx/eduagent)** | TypeScript, Python CLI | 51 agent tools, 9-file output, DOCX/PPTX/Anki/Kahoot export, teacher voice cloning | 16 stars (Apr 2026) |
| **[TeachAI](https://github.com/LQ458/lesson-plan-generator)** | Next.js 15, ChromaDB, RAG | 95K+ educational chunks, semantic search, multi-format output | Active |
| **[Astral Learning](https://github.com/Biboswan/astral-learning)** | Next.js 15, Supabase, GPT-4o-mini, DALL-E 3 | TypeScript-validated lesson content, interactive blocks | New (Oct 2025) |
| **[Shiksha AI](https://github.com/skully-coder/shiksha-ai)** | Next.js, Firebase, Google Gemini | Low-resource focus, lesson planning + assessment + resource creation | 9 stars |
| **[Better Lessons](https://github.com/llegomark/betterlessons)** | Next.js, OpenAI | Lesson plan templating via streaming API | 4 stars |

---

## 2. Pedagogical Frameworks for Content Structure

### 2.1 Bloom's Taxonomy (Revised — Anderson & Krathwohl, 2001)

| Level | Cognitive Process | Typical Verbs | Assessment Types |
|---|---|---|---|
| 1. Remember | Recall facts | List, define, identify, name | MCQ, matching, fill-in-blank |
| 2. Understand | Explain ideas | Explain, summarize, interpret | Short answer, concept map |
| 3. Apply | Use in new situations | Solve, implement, demonstrate | Problem sets, simulations |
| 4. Analyze | Draw connections | Compare, contrast, distinguish | Case studies, data analysis |
| 5. Evaluate | Justify decisions | Critique, judge, defend | Essays, peer review, rubrics |
| 6. Create | Produce new work | Design, construct, plan | Projects, portfolios, presentations |

**For oh-my-class**: Each level maps to a distinct question template family. The system should tag every learning objective and assessment item with its Bloom level, enabling scaffolded difficulty progression.

**Recent work**: The AIEd Bloom's Taxonomy (Kalantzis-Cope, 2024) proposes 6 new levels aligned with AI capabilities: Collect, Adapt, Simulate, Process, Evaluate, Innovate.

### 2.2 Backward Design (Understanding by Design — Wiggins & McTighe)

**Three-Stage Process**:

| Stage | Focus | Key Questions |
|---|---|---|
| **Stage 1: Desired Results** | Learning goals, enduring understandings, essential questions | What should students know, understand, and be able to do? |
| **Stage 2: Evidence** | Performance tasks, other evidence | How will we know if students achieved the results? |
| **Stage 3: Learning Plan** | Activities, instruction, sequence | What learning experiences will achieve the results? |

**UbD Template Structure**:
```
Stage 1: Desired Results
├── Established Goals (standards alignment)
├── Understandings (big ideas + enduring understandings)
├── Essential Questions
├── Knowledge (students will know...)
└── Skills (students will be able to...)

Stage 2: Evidence
├── Performance Tasks (GRASPS: Goal, Role, Audience, Situation, Product, Standards)
└── Other Evidence (quizzes, tests, observations, journals)

Stage 3: Learning Plan
└── WHERETO elements
    ├── W — Where is it going? Hook?
    ├── H — Hook students
    ├── E — Explore/Experience/Equip
    ├── R — Rethink/Revise/Reflect
    ├── E — Exhibit/Evaluate
    ├── T — Tailor to needs
    └── O — Organize sequence
```

**For oh-my-class**: The UbD template provides a comprehensive lesson schema. The WHERETO acronym maps directly to structural components of a lesson plan.

### 2.3 Gagné's Nine Events of Instruction

| # | Event | Cognitive Process | Implementation in Content |
|---|---|---|---|
| 1 | Gain attention | Reception | Hook, problem scenario, surprising fact |
| 2 | Inform learners of objectives | Expectancy | Learning objectives section |
| 3 | Stimulate recall of prior learning | Retrieval | Prerequisite quiz, connection questions |
| 4 | Present content | Selective perception | Core material delivery |
| 5 | Provide learning guidance | Semantic encoding | Worked examples, scaffolds, hints |
| 6 | Elicit performance | Responding | Practice exercises, activities |
| 7 | Provide feedback | Reinforcement | Answer keys, explanations |
| 8 | Assess performance | Retrieval | Quiz, assessment |
| 9 | Enhance retention & transfer | Generalization | Real-world applications, review |

**Used by**: AgentLesson (Writer/Evaluator multi-agent system), many LMS platforms.

**For oh-my-class**: This provides the **sequence of a teaching pack**. Each event becomes a content section or component.

---

## 3. Educational Content Schemas

### 3.1 Lesson Plan Schema (Comprehensive)

Based on UbD + Gagné + research literature synthesis:

```typescript
interface LessonPlan {
  // Identity & Metadata
  id: string;
  title: string;
  subject: string;           // Math, Science, ELA, etc.
  topic: string;
  gradeLevel: string[];      // e.g. ["grade-3", "grade-4"]
  ageRange: { min: number; max: number };
  duration: number;          // minutes
  language: string;
  
  // Curriculum Alignment
  standards: CurriculumStandard[];
  prerequisites: string[];   // Prior knowledge required
  
  // Stage 1: Desired Results (UbD)
  learningObjectives: LearningObjective[];
  essentialQuestions: string[];
  enduringUnderstandings: string[];
  
  // Stage 2: Evidence
  performanceTasks: PerformanceTask[];
  assessmentCriteria: AssessmentCriterion[];
  
  // Stage 3: Learning Plan (Gagné-aligned)
  lessonPhases: LessonPhase[];
  
  // Resources
  materials: Material[];
  vocabulary: VocabularyTerm[];
  
  // Differentiation
  differentiation: {
    forStruggling: string[];
    forAdvanced: string[];
    forELL: string[];
  };
  
  // Metadata
  metadata: ContentMetadata;
  tags: string[];
}
```

### 3.2 Quiz/Assessment Data Model

```typescript
interface Quiz {
  id: string;
  title: string;
  instructions: string;
  timeLimit?: number;         // minutes
  shuffleQuestions: boolean;
  passingScore: number;       // percentage
  
  questions: Question[];
  
  metadata: {
    bloomLevel: BloomLevel;
    difficulty: 1 | 2 | 3 | 4 | 5;
    estimatedTimePerQuestion: number;
    tags: string[];
  };
}

interface Question {
  id: string;
  type: QuestionType;
  stem: string;               // Question text
  media?: MediaAttachment[];
  
  // Answer configuration (type-dependent)
  options?: ChoiceOption[];    // MCQ, matching
  correctAnswer?: string | string[] | number | number[];
  
  // Scoring
  points: number;
  partialCredit: boolean;
  
  // Feedback
  feedbackCorrect?: string;
  feedbackIncorrect?: string;
  feedbackGeneral?: string;
  
  // Metadata
  bloomLevel: BloomLevel;
  difficulty: 1 | 2 | 3 | 4 | 5;
  topic: string;
  tags: string[];
}

type QuestionType =
  | "multiple_choice"
  | "multiple_answer"       // Checkbox
  | "true_false"
  | "short_answer"
  | "essay"
  | "matching"
  | "fill_in_blank"
  | "numerical"
  | "ordering"
  | "drag_drop"
  | "hotspot";

interface ChoiceOption {
  id: string;
  text: string;
  isCorrect: boolean;
  feedback?: string;
}

interface MatchingPair {
  id: string;
  prompt: string;    // Left column
  match: string;     // Right column
}
```

### 3.3 Worksheet Structure Patterns

```typescript
interface Worksheet {
  id: string;
  title: string;
  instructions: string;
  
  sections: WorksheetSection[];
  
  metadata: {
    difficulty: number;
    estimatedTime: number;
    answerKeyIncluded: boolean;
    skillsPracticed: string[];
  };
}

interface WorksheetSection {
  id: string;
  type: "instruction" | "example" | "practice" | "challenge" | "review";
  title: string;
  instruction?: string;
  
  // Content blocks within section
  blocks: WorksheetBlock[];
}

type WorksheetBlock =
  | { type: "text"; content: string }
  | { type: "question"; question: Question }
  | { type: "table"; headers: string[]; rows: string[][] }
  | { type: "grid"; columns: number; cells: GridCell[] }
  | { type: "blank_lines"; count: number; label?: string }
  | { type: "space_for_work"; height: number }
  | { type: "fill_in_table"; headers: string[]; rows: (string | null)[][] }
  | { type: "matching_lines"; pairs: { left: string; right: string; blank: boolean }[] }
  | { type: "diagram_space"; instructions: string }
  | { type: "code_block"; language: string; code: string }
  | { type: "media"; attachment: MediaAttachment };
```

### 3.4 Infographic Data Model for Educational Visuals

```typescript
interface Infographic {
  id: string;
  title: string;
  subject: string;
  topic: string;
  
  // Layout
  layout: "vertical" | "horizontal" | "grid" | "timeline" | "flowchart" | "comparison" | "diagram";
  width: number;    // px
  height: number;   // px
  
  // Color scheme (generated, WCAG-compliant)
  theme: ColorTheme;
  
  // Content layers
  sections: InfographicSection[];
  
  // Accessibility
  alternativeText: string;
  longDescription?: string;
}

interface InfographicSection {
  id: string;
  type: "header" | "body" | "stat" | "quote" | "step" | "comparison_column" | "diagram" | "callout";
  
  title?: string;
  content: RichTextContent;
  
  // Position & styling
  position: { x: number; y: number; width: number; height: number };
  style: {
    backgroundColor?: string;
    textColor?: string;
    icon?: string;
    borderStyle?: "solid" | "dashed" | "none";
  };
  
  // Diagram-specific
  diagramData?: DiagramData;
}

interface DiagramData {
  type: "flowchart" | "venn" | "cycle" | "hierarchy" | "timeline";
  nodes: DiagramNode[];
  edges: DiagramEdge[];
}

interface ColorTheme {
  primary: string;       // Headings, accents
  secondary: string;     // Supporting elements
  background: string;    // Page bg
  text: string;          // Body text
  accent: string[];      // Data series colors (3-6)
  
  // WCAG compliance metadata
  contrastRatios: {
    textOnBg: number;    // Must be ≥ 4.5:1
    largeTextOnBg: number; // Must be ≥ 3:1
  };
}
```

### 3.5 Complete Teaching Pack Schema (oh-my-class focus)

A teaching pack = all materials a teacher needs for one lesson unit:

```typescript
interface TeachingPack {
  // Identity
  id: string;
  title: string;
  subject: string;
  gradeLevel: string[];
  duration: number;
  
  // Core content
  lessonPlan: LessonPlan;
  worksheets: Worksheet[];
  quizzes: Quiz[];
  
  // Supplementary
  vocabularyCards: VocabularyCard[];
  infographics: Infographic[];
  recapSlides: Slide[];
  drills: DrillExercise[];
  
  // Teacher resources
  answerKeys: AnswerKey[];
  teachingNotes: string;
  differentiationGuides: DifferentiationGuide;
  
  // Standards alignment
  standards: CurriculumStandard[];
  
  // Generation metadata
  generatorVersion: string;
  generationDate: string;
  modelUsed: string;
  qualityScore: QualityScore;
  humanReviewed: boolean;
}
```

---

## 4. Quality Standards

### 4.1 Academic Accuracy & Hallucination Detection

**TEAS Framework** (Trusted Educational AI Standard):
- **V**erifiability: Content traceable to authoritative sources
- **S**tability: Deterministic consistency for core knowledge
- **A**uditability: Independent validation of system's logic
- **P**edagogical Soundness: Evidence-based teaching methods

**ACIF Framework** (AI Content Integrity for Curriculum):
- **4 Risk Tiers**: Low (Tier 1) → Critical (Tier 4)
- **6 Age Bands**: Early Childhood (3-5) to Pre-Tertiary (18+)
- **5-Gate Pipeline**:
  1. Pre-Delivery Screening
  2. Factual Verification
  3. Age-Appropriateness
  4. Curriculum Alignment
  5. Final Approval
- **FACT Hallucination Protocol**:
  - **F**ind the claim — identify every factual assertion
  - **A**ssess the risk — is this verifiable?
  - **C**ross-reference — verify against 2+ authoritative sources
  - **T**ag the result — VERIFIED / MODIFIED / REMOVED

**For oh-my-class**: Every AI-generated assertion must pass through FACT pipeline before output. Implement as a quality gate in the generation pipeline.

### 4.2 Pedagogical Quality Rubrics

**5-Dimension Rubric** (used by EduPlanner, AgentLesson):
1. **Clarity** — Is the content clear and understandable?
2. **Integrity** — Is the structure complete (all sections present)?
3. **Depth** — Does it go beyond surface-level coverage?
4. **Practicality** — Can a teacher implement this as-is?
5. **Pertinence** — Is it relevant to the stated objectives?

**Quality Evaluation Index System for AIGDER** (4 dimensions, 20 indicators):
| Dimension | Sample Indicators |
|---|---|
| Content | Accuracy, completeness, structure, authority |
| Expression | Clarity, readability, engagement, visual quality |
| User | Relevance, difficulty fit, personalization |
| Technical | Format compatibility, accessibility, load time |

**For oh-my-class**: Implement automated scoring across these 5 dimensions. Set minimum thresholds for each before pack is considered "production-ready".

### 4.3 Age-Appropriate Content Filtering

Based on ACIF Age Bands specification:

| Band | Age Range | Grade Level (VN) | Content Restrictions |
|---|---|---|---|
| Early Childhood | 3-5 | Preschool | No abstract concepts; play-based |
| Lower Primary | 6-8 | Grade 1-3 | Simple cause-effect; concrete examples |
| Upper Primary | 9-11 | Grade 4-5 | Abstract concepts introduced |
| Lower Secondary | 12-14 | Grade 6-9 | Complex inference; argumentation |
| Upper Secondary | 15-17 | Grade 10-12 | Critical analysis; nuanced topics |
| Pre-Tertiary | 18+ | University-prep | Full academic rigor |

**Controls**:
- **Vocabulary**: Lexile/Flesch-Kincaid grade-level matching
- **Sentence complexity**: Max clause count per age band
- **Concept abstraction**: Filter by Bloom level (e.g., "Evaluate" prohibited before Upper Primary)
- **Sensitive topics**: Tier 3/4 require special handling

### 4.4 WCAG for Educational HTML

**Target**: WCAG 2.2 Level AA (minimum)

**Key Requirements for Educational HTML**:

| Principle | Criterion | Implementation |
|---|---|---|
| **Perceivable** | 1.1.1 Non-text Content | Alt text on all images, diagrams, icons |
| | 1.3.1 Info and Relationships | Semantic HTML (h1-h6, nav, main, aside) |
| | 1.4.3 Contrast (Minimum) | Text ≥ 4.5:1; large text ≥ 3:1 |
| | 1.4.11 Non-text Contrast | UI/graphics ≥ 3:1 |
| **Operable** | 2.1.1 Keyboard | All quiz interactions keyboard-accessible |
| | 2.4.4 Link Purpose | Descriptive link text (no "click here") |
| | 2.4.11 Focus Not Obscured (WCAG 2.2) | Focused elements never hidden by sticky headers |
| | 2.5.8 Target Size (WCAG 2.2) | Interactive targets ≥ 24×24 CSS px |
| **Understandable** | 3.1.1 Language of Page | `<html lang="vi">` for Vietnamese |
| | 3.3.2 Labels or Instructions | Form fields have clear labels |
| | 3.3.7 Redundant Entry (WCAG 2.2) | Don't re-ask same info |
| | 3.3.8 Accessible Authentication (WCAG 2.2) | No memorization-only login |
| **Robust** | 4.1.2 Name, Role, Value | ARIA roles on custom components |

**For oh-my-class**: Generate HTML that passes axe-core automated checks for WCAG 2.2 AA. Embed accessibility metadata in every output file.

### 4.5 Vietnamese Education Context

**Ministry of Education Framework**:

- **2018 General Education Program**: Competency-based approach; 5 qualities + 10 core competencies
- **Decision 3439/QĐ-BGDĐT** (Dec 2025): AI education framework for K-12 with 4 knowledge strands:
  1. Human-centered thinking
  2. AI ethics
  3. AI techniques & applications
  4. AI system design
- **Circular 02/2025/TT-BGDĐT**: Digital Competence Framework for learners — 6 domains, 24 sub-competencies, 4 proficiency levels (8 bands)

**Structure of Vietnamese Curriculum**:
```
General Education
├── Basic Education (Grade 1-9)
│   ├── Primary (Grade 1-5): Comprehensive, integrated
│   └── Lower Secondary (Grade 6-9): Foundation
└── Career-Oriented Education (Grade 10-12)
    └── Upper Secondary: Differentiated, career prep
```

**Regulatory Requirements for Content**:
- Must be "basic, comprehensive, practical, modern, systematic"
- Preserve national cultural identity
- Age-appropriate physical/intellectual/psycho-physiological development
- Textbooks require National Review Council approval
- STEM/STEAM education emphasized (Decision 131/QĐ-TTg)

**For oh-my-class**: Support Vietnamese as a first-class language. Implement VN curriculum standards mapping. Generate bilingual (EN/VI) content as an option.

---

## 5. Export Formats

### 5.1 Moodle GIFT Format

**Type**: Plain text, line-oriented  
**MIME**: `.txt` (convention)  
**Best for**: Bulk import into Moodle question bank

**Supported Question Types**:

| Type | Syntax | Notes |
|---|---|---|
| Multiple Choice | `Question{ =Correct ~Wrong1 ~Wrong2 }` | `=` prefix for correct, `~` for wrong |
| True/False | `Statement{TRUE}` or `{FALSE}` | Also `{T}` / `{F}` |
| Short Answer | `Question{ =answer1 =answer2 }` | Multiple correct answers with `=` |
| Matching | `Prompt{ =item1->match1 =item2->match2 }` | `->` separates pair |
| Numerical | `Question{ #answer:error_margin }` | `#` starts numeric; colon for tolerance |
| Essay | `Question{ }` | No answer syntax |
| Missing Word | `Fill { =correct ~wrong } blank` | Embedded `{}` in sentence |

**Advanced Features**:
- `::name::` — Question name
- `#feedback` — Per-answer feedback after `#`
- `%50%` — Percentage weight (partial credit)
- `[html]` / `[markdown]` — Text format specifier
- `//` — Comment lines (not imported)
- `$CATEGORY: path` — Category assignment

**Example**:
```
::Addition Facts::
[html]What is 2 + 2?{
  =4#Correct!
  ~3#Try again.
  ~5#Not quite.
}
```

**For oh-my-class**: Implement GIFT export as a text serializer. Straightforward to generate from the Question data model.

### 5.2 H5P Interactive Content

**Type**: ZIP package (`.h5p` extension)  
**Architecture**:
```
package.h5p
├── h5p.json                    # Package metadata
├── content/
│   └── content.json            # Content instance data
├── H5P.LibraryName/            # Library code
│   ├── library.json            # Library metadata + dependencies
│   └── semantics.json          # Content type schema
└── other-libraries/...
```

**Key Data Structures**:

`h5p.json` (package-level):
```json
{
  "title": "Fill in the blanks",
  "language": "en",
  "mainLibrary": "H5P.Blanks",
  "embedTypes": ["div"],
  "preloadedDependencies": [
    { "machineName": "H5P.Blanks", "majorVersion": 1, "minorVersion": 0 }
  ]
}
```

`content/content.json` (instance data — structure defined by semantics.json):
```json
{
  "text": "Hello, my name is !*James*! and I am from !*France*!",
  "behaviour": {
    "enableRetry": true,
    "enableSolutionsButton": true
  }
}
```

**Educational Content Types for oh-my-class**:
| H5P Type | Use Case |
|---|---|
| H5P.MultiChoice | Quiz questions |
| H5P.TrueFalse | True/false items |
| H5P.Blanks | Fill-in-blank exercises |
| H5P.DragText | Drag words into text |
| H5P.DragQuestion | Drag-drop matching |
| H5P.Summary | Lesson recap |
| H5P.Flashcards | Vocabulary cards |
| H5P.Column / H5P.QuestionSet | Composed assessments |

**For oh-my-class**: Generate the `content/content.json` files. Pre-built library packages make inclusion straightforward. The `semantics.json` file acts as the content type's schema definition.

### 5.3 QTI 2.1 (Question and Test Interoperability)

**Type**: XML-based, ZIP package  
**Standard Body**: 1EdTech Consortium (formerly IMS Global)  
**Version**: 2.1 Final (Aug 2012); 2.2 available

**Package Structure**:
```
qti-package.zip
├── imsmanifest.xml          # IMS Content Packaging manifest
├── assessments/
│   └── test.xml             # assessmentTest
└── items/
    ├── item-001.xml         # assessmentItem
    └── item-002.xml
```

**Core Data Model**:
```
assessmentTest
├── testPart (timing, control modes)
│   └── assessmentSection
│       ├── assessmentItemRef → assessmentItem
│       └── assessmentSection (nested)

assessmentItem
├── responseDeclaration (response variables, correct answers)
├── outcomeDeclaration (score variables)
├── itemBody (presentation — HTML with interactions)
└── responseProcessing (scoring rules)
```

**Interaction Types** (question types):
| QTI Type | Description |
|---|---|
| `choiceInteraction` | Multiple choice (single/multiple select) |
| `orderInteraction` | Reorder items |
| `associateInteraction` | Matching pairs |
| `matchInteraction` | Matrix match |
| `gapMatchInteraction` | Drag text into gaps |
| `inlineChoiceInteraction` | Dropdown in text |
| `textEntryInteraction` | Fill-in-blank |
| `extendedTextInteraction` | Essay |
| `hotspotInteraction` | Click on image |
| `sliderInteraction` | Numeric range |
| `drawingInteraction` | Freehand drawing |
| `uploadInteraction` | File upload |

**Results Reporting**:
```xml
<assessmentResult>
  <context>...</context>
  <testResult>
    <itemVariable identifier="SCORE" baseType="float" cardinality="single">
      <value>85.0</value>
    </itemVariable>
  </testResult>
  <itemResult identifier="item-001">
    <itemVariable identifier="duration" baseType="float">
      <value>120.0</value>
    </itemVariable>
  </itemResult>
</assessmentResult>
```

**For oh-my-class**: QTI is complex but the most interoperable standard. Implement it as an export-only format (not import). The schema defines interaction types that map to QuestionType.

### 5.4 Google Forms API

**Type**: REST JSON API  
**Base URL**: `https://forms.googleapis.com/v1/forms`  
**Scope**: OAuth 2.0 (`forms.body`, `drive`, `drive.file`)

**Workflow**:
1. `POST /v1/forms` — Create form with title only
2. `POST /v1/forms/{formId}:batchUpdate` — Add items, set quiz settings

**Question Types Supported**:
| Type | API Object | Auto-gradable |
|---|---|---|
| Multiple Choice | `choiceQuestion.type: RADIO` | ✅ |
| Checkboxes | `choiceQuestion.type: CHECKBOX` | ✅ |
| Dropdown | `choiceQuestion.type: DROP_DOWN` | ✅ |
| Short Answer | `textQuestion` | ✅ (exact match) |
| Paragraph | `textQuestion.paragraph: true` | ❌ |
| Linear Scale | `scaleQuestion` | ❌ |
| Date/Time | `dateQuestion` / `timeQuestion` | ❌ |
| File Upload | `fileUploadQuestion` | ❌ |

**Grading JSON** (auto-gradable types):
```json
{
  "questionItem": {
    "question": {
      "required": true,
      "grading": {
        "pointValue": 2,
        "correctAnswers": {
          "answers": [{"value": "Maya Angelou"}]
        },
        "whenRight": {"text": "Correct!"},
        "whenWrong": {"text": "Incorrect"}
      },
      "choiceQuestion": {
        "type": "RADIO",
        "options": [
          {"value": "Maya Angelou"},
          {"value": "bell hooks"}
        ]
      }
    }
  }
}
```

**For oh-my-class**: Implement as an export target for quiz content. The `grading` object maps directly to our `Grading` interface. Note: only exact-match auto-grading is supported.

### 5.5 Format Comparison Matrix

| Feature | Moodle GIFT | H5P | QTI 2.1 | Google Forms |
|---|---|---|---|---|
| **Format type** | Plain text | ZIP package | XML ZIP | REST API |
| **Question types** | 6 | 10+ content types | 12+ interactions | 8 |
| **Partial credit** | ✅ (percentage) | ✅ (per question) | ✅ (mapping) | ❌ (all-or-nothing) |
| **Feedback** | ✅ per-answer | ✅ per-answer | ✅ per-response | ✅ correct/incorrect |
| **Images/media** | ❌ (text only) | ✅ embedded | ✅ URI references | ✅ via Drive |
| **Scoring** | ✅ default grade | ✅ max score | ✅ complex outcomes | ✅ point value |
| **Branching** | ❌ | ❌ | ✅ via testPart | ✅ section routing |
| **Math/LaTeX** | ⚠️ escape needed | ✅ | ✅ MathML | ❌ |
| **Accessibility** | ❌ | ✅ (built-in) | ✅ (APIP) | ✅ (basic) |
| **Self-contained** | ✅ (text file) | ✅ (all assets) | ✅ (manifest) | ❌ (API only) |
| **Open standard** | ✅ (Moodle) | ✅ (open source) | ✅ (1EdTech) | ❌ (proprietary) |
| **Adoption** | Moodle only | 40K+ sites | Wide (LMS market) | Google ecosystem |
| **Ease of generation** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |

---

## Quick Action Items for oh-my-class

1. **Schema first** — Define the TeachingPack, LessonPlan, Quiz, Worksheet, and Infographic TypeScript interfaces (Section 3). These drive all generation, validation, and export.

2. **Pedagogical backbone** — Use Gagné's 9 Events as the sequence template for every teaching pack. Tag all content with Bloom's Taxonomy levels. Support UbD-style backward design metadata.

3. **Quality gates** — Implement the FACT hallucination protocol (Section 4.1) as a post-generation checker. Score every pack on the 5-dimension rubric (Section 4.2). Enforce age-appropriate filters (Section 4.3).

4. **Export targets** — Start with GIFT (simplest) and H5P (richest). Add QTI 2.1 and Google Forms API later. The internal data model should be format-agnostic.

5. **Vietnamese first** — VN curriculum standards, bilingual output, WCAG 2.2 AA compliance from day one. Support Decision 3439 framework strands.