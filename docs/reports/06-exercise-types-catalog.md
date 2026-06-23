# Oh-My-Class: Comprehensive Exercise Types Catalog

> **Purpose**: Complete catalog of all educational exercise types, special homework formats, and assessment types the system must support.
> **Date**: 2026-06-23
> **Context**: Built for the Vietnamese education system (Chương trình GDPT 2018) and English language learning.

---

## Table of Contents

1. [Assessment Formats (Core Question Types)](#1-assessment-formats-core-question-types)
2. [English Language Learning Exercise Types](#2-english-language-learning-exercise-types)
3. [Math/Science Special Exercise Types](#3-math-science-special-exercise-types)
4. [Special Homework Formats (Multimedia)](#4-special-homework-formats-multimedia)
5. [Large-Scale Exam Prep (500-700 Question Banks)](#5-large-scale-exam-prep)
6. [Interactive & Gamified Formats](#6-interactive--gamified-formats)
7. [Vietnamese Education System Requirements](#7-vietnamese-education-system-requirements)
8. [IMS QTI Standards Alignment](#8-ims-qti-standards-alignment)
9. [Master Schema: Question Union Type](#9-master-schema-question-union-type)
10. [Artifact Type Matrix](#10-artifact-type-matrix)

---

## 1. Assessment Formats (Core Question Types)

### 1.1 Multiple Choice — Single Answer
**VN**: Trắc nghiệm một đáp án | **EN**: Multiple Choice Single Answer

**Description**: Four options, one correct answer. The dominant format in Vietnamese exams. Used by: English (100% of multiple-choice section), all other subjects.

**Difficulty**: All levels (Nhan biet -> Van dung cao)
**Supported by**: Lesson (checkpoints), Worksheet, Quiz, Drill, Recap

```json
{
  "type": "multiple_choice_single",
  "stem": "What is the past tense of 'go'?",
  "options": [
    { "id": "A", "text": "goed", "isCorrect": false },
    { "id": "B", "text": "went", "isCorrect": true },
    { "id": "C", "text": "gone", "isCorrect": false },
    { "id": "D", "text": "going", "isCorrect": false }
  ],
  "explanation": "'Went' is the irregular past tense of 'go.'",
  "difficulty": "remember"
}
```

---

### 1.2 Multiple Choice — Multiple Answers
**VN**: Trắc nghiệm nhiều đáp án | **EN**: Multiple Choice Multiple Answer

**Description**: One stem, multiple correct options. Student must select ALL correct answers. Grading: partial credit or all-or-nothing.

**Difficulty**: Understand -> Analyze
**Supported by**: Quiz, Drill, Worksheet

```json
{
  "type": "multiple_choice_multiple",
  "stem": "Which of the following are renewable energy sources?",
  "options": [
    { "id": "A", "text": "Solar power", "isCorrect": true },
    { "id": "B", "text": "Natural gas", "isCorrect": false },
    { "id": "C", "text": "Wind power", "isCorrect": true },
    { "id": "D", "text": "Nuclear fission", "isCorrect": false },
    { "id": "E", "text": "Hydroelectric", "isCorrect": true }
  ],
  "scoring": { "type": "all_or_nothing", "pointsPerCorrect": 1 },
  "difficulty": "understand"
}
```

---

### 1.3 True/False (Dung/Sai) — Vietnamese Exam Format
**VN**: Trắc nghiệm Đúng/Sai (4 ý) | **EN**: True/False (4-item)

**Description**: **Critical for Vietnamese 2025+ exams.** Each question has 4 sub-items. Student marks each as True/False. Scoring (per MOET Decision 764/QD-BGDDT):
- 1 correct = 0.1d, 2 correct = 0.25d, 3 correct = 0.5d, 4 correct = 1.0d
- Random chance of max score: 1/16 (4x harder to guess than MC)

**Difficulty**: Understand -> Evaluate
**Supported by**: Quiz, Drill, Recap

```json
{
  "type": "true_false_4item",
  "stem": "Consider f(x) = x^2 - 4x + 3. Mark each statement T or F.",
  "items": [
    { "id": "i1", "text": "The vertex is at x = 2", "isTrue": true },
    { "id": "i2", "text": "The roots are x = 1 and x = -3", "isTrue": false },
    { "id": "i3", "text": "The parabola opens upward", "isTrue": true },
    { "id": "i4", "text": "f(0) = 3", "isTrue": true }
  ],
  "scoring": {
    "type": "vietnamese_tf_2025",
    "correct1": 0.1, "correct2": 0.25, "correct3": 0.5, "correct4": 1.0
  },
  "difficulty": "understand"
}
```

---

### 1.4 Short Answer (Tra Loi Ngan)
**VN**: Trả lời ngắn | **EN**: Short Answer

**Description**: Vietnamese exam format (2025+). Student computes answer and fills it in. Only final answer scored. 0.5d for Math, 0.25d for others.

**Difficulty**: Apply -> Evaluate
**Supported by**: Quiz, Drill, Worksheet

```json
{
  "type": "short_answer",
  "stem": "What is the derivative of f(x) = 3x^2 + 2x - 5?",
  "correctAnswer": "6x + 2",
  "acceptableAnswers": ["6x+2", "6x + 2", "f'(x)=6x+2"],
  "tolerance": null,
  "unit": null,
  "difficulty": "apply"
}
```

---

### 1.5 Essay / Long Response
**VN**: Tự luận | **EN**: Essay / Extended Response

**Description**: Extended written response with rubric scoring. Only format for Literature exam (120 min). Uses analytic rubric.

**Difficulty**: Analyze -> Create
**Supported by**: Lesson (guided), Worksheet, Quiz

```json
{
  "type": "essay",
  "prompt": "Analyze the character of Santiago...",
  "wordLimit": { "min": 300, "max": 500 },
  "rubric": {
    "criteria": [
      {
        "name": "Content & Analysis", "weight": 40,
        "descriptors": {
          "excellent": "Deep analysis with textual evidence",
          "good": "Good analysis with some evidence",
          "fair": "Basic understanding",
          "poor": "Misunderstands the text"
        }
      },
      {
        "name": "Organization", "weight": 30,
        "descriptors": {
          "excellent": "Clear thesis, logical flow",
          "good": "Good structure with minor lapses",
          "fair": "Some organization but lacks coherence",
          "poor": "No clear structure"
        }
      },
      {
        "name": "Language & Grammar", "weight": 30
      }
    ]
  },
  "difficulty": "create"
}
```

---

### 1.6 Fill in the Blank (with Word Bank)
**VN**: Điền vào chỗ trống (có gợi ý) | **EN**: Fill in the Blank (Word Bank)

**Description**: Passage/sentence with blanks. Word bank provided. Student selects correct word. Reduces cognitive load.

**Difficulty**: Remember -> Understand
**Supported by**: Lesson, Worksheet, Drill

```json
{
  "type": "fill_blank_wordbank",
  "context": "The quick brown {{1}} jumps over the {{2}} dog.",
  "blanks": [
    { "id": 1, "correctAnswer": "fox" },
    { "id": 2, "correctAnswer": "lazy" }
  ],
  "wordBank": ["fox", "lazy", "dog", "quick", "jumps"],
  "distractors": ["cat", "sleepy"],
  "shuffleWordBank": true,
  "difficulty": "remember"
}
```

---

### 1.7 Fill in the Blank (Free / Cloze)
**VN**: Điền vào chỗ trống (tự do) | **EN**: Cloze / Gap Fill

**Description**: No word bank. Student produces the word. Higher cognitive load. Types: grammar-based, vocabulary-based, contextual.

**Difficulty**: Understand -> Apply
**Supported by**: Worksheet, Drill, Quiz

```json
{
  "type": "cloze",
  "clozeType": "grammar",
  "passage": "Yesterday, I {{1}} (go) to the market.",
  "blanks": [
    { "id": 1, "correctAnswer": "went", "hint": "past tense of go" }
  ],
  "caseSensitive": false,
  "difficulty": "apply"
}
```

---

### 1.8 Matching Exercise
**VN**: Nối / Ghép cặp | **EN**: Matching

**Description**: Two columns. Match items from left to right. Extensively researched in EFL (Nation, Schmitt). Can include distractors.

**Difficulty**: Remember -> Understand
**Supported by**: Worksheet, Drill, Lesson

```json
{
  "type": "matching",
  "instructions": "Match each word with its definition.",
  "leftColumn": [
    { "id": "L1", "text": "Benevolent" },
    { "id": "L2", "text": "Malevolent" },
    { "id": "L3", "text": "Volunteer" }
  ],
  "rightColumn": [
    { "id": "R1", "text": "Well-meaning and kindly" },
    { "id": "R2", "text": "Having a wish to do evil" },
    { "id": "R3", "text": "A person who freely offers" },
    { "id": "R4", "text": "Watches over something", "isDistractor": true }
  ],
  "correctMatches": [
    { "left": "L1", "right": "R1" },
    { "left": "L2", "right": "R2" },
    { "left": "L3", "right": "R3" }
  ],
  "difficulty": "remember"
}
```

---

### 1.9 Ordering / Sequencing
**VN**: Sắp xếp thứ tự | **EN**: Ordering / Sequencing

**Description**: Arrange items in correct logical, chronological, or procedural order.

**Difficulty**: Understand -> Analyze
**Supported by**: Worksheet, Drill, Quiz

```json
{
  "type": "ordering",
  "instructions": "Arrange steps of the water cycle in correct order.",
  "items": [
    { "id": 1, "text": "Water evaporates from oceans", "correctPosition": 1 },
    { "id": 2, "text": "Vapor condenses into clouds", "correctPosition": 2 },
    { "id": 3, "text": "Precipitation falls as rain", "correctPosition": 3 },
    { "id": 4, "text": "Water collects in rivers", "correctPosition": 4 }
  ],
  "difficulty": "understand"
}
```

---

### 1.10 Drag and Drop
**VN**: Kéo thả | **EN**: Drag and Drop

**Description**: Visual interactive format. Drag elements into target zones. Used for labeling diagrams, categorizing, sorting.

**Difficulty**: Remember -> Apply
**Supported by**: Lesson (interactive), Drill, Quiz

```json
{
  "type": "drag_and_drop",
  "instructions": "Drag labels to the correct parts of the plant cell.",
  "zones": [
    { "id": "Z1", "label": "Nucleus" },
    { "id": "Z2", "label": "Cell Wall" }
  ],
  "draggables": [
    { "id": "D1", "text": "Nucleus", "correctZone": "Z1" },
    { "id": "D2", "text": "Cell Wall", "correctZone": "Z2" },
    { "id": "D3", "text": "Mitochondria", "isDistractor": true }
  ],
  "difficulty": "remember"
}
```

---

### 1.11 Drawing / Diagramming
**VN**: Vẽ / Sơ đồ | **EN**: Drawing / Diagramming

**Description**: Student creates a visual response -- diagram, graph, mind map, sketch. Assessed via rubric.

**Difficulty**: Apply -> Create
**Supported by**: Worksheet, Lesson, Recap

```json
{
  "type": "drawing",
  "instructions": "Draw a Venn diagram comparing renewable and non-renewable energy.",
  "canvas": { "width": 600, "height": 400 },
  "rubric": {
    "criteria": [
      { "name": "Accuracy", "weight": 50 },
      { "name": "Completeness", "weight": 30 },
      { "name": "Clarity", "weight": 20 }
    ]
  },
  "difficulty": "apply"
}
```

---

### 1.12 Performance-Based (Rubric-Scored)
**VN**: Đánh giá qua thực hiện | **EN**: Performance-Based Assessment

**Description**: Student performs a task (presentation, experiment, speech, project) scored against an analytic rubric. Used for formative (Thong tu 22/2021) and summative assessment.

**Difficulty**: Apply -> Create
**Supported by**: Lesson, Quiz, Recap

```json
{
  "type": "performance",
  "task": "Present a 3-minute argument for or against school uniforms.",
  "format": "presentation",
  "timeLimit": 180,
  "rubric": {
    "criteria": [
      { "name": "Argument Quality", "weight": 40,
        "levels": [
          { "score": 4, "description": "Clear thesis, strong evidence" },
          { "score": 3, "description": "Clear thesis with good evidence" },
          { "score": 2, "description": "Weak evidence" },
          { "score": 1, "description": "No clear argument" }
        ]
      },
      { "name": "Delivery", "weight": 30 },
      { "name": "Language Use", "weight": 30 }
    ]
  },
  "difficulty": "create"
}
```

---

## 2. English Language Learning Exercise Types

### 2.1 Vocabulary: Word -> Definition -> Sentence -> Paragraph
**VN**: Từ vựng: Từ -> Định nghĩa -> Câu -> Đoạn văn

**Description**: Scaffolded vocabulary progression (Nation's four strands). Word recognition -> comprehension -> sentence production -> paragraph production.

**Difficulty**: Remember -> Create
**Supported by**: Lesson, Worksheet, Drill, Recap

```json
{
  "type": "vocabulary_scaffolded",
  "targetWord": "ubiquitous",
  "level": "B2",
  "stages": [
    { "stage": "recognition", "activity": { "type": "matching" } },
    { "stage": "comprehension", "activity": { "type": "multiple_choice_single", "stem": "Which sentence uses 'ubiquitous' correctly?" } },
    { "stage": "production_sentence", "activity": { "type": "short_answer", "stem": "Write a sentence using 'ubiquitous'." } },
    { "stage": "production_paragraph", "activity": { "type": "essay", "prompt": "Write a paragraph using 'ubiquitous'.", "wordLimit": { "min": 50, "max": 100 } } }
  ],
  "difficulty": "remember"
}
```

---

### 2.2 Cloze Test -- Grammar/Vocabulary/Contextual
**VN**: Bài tập điền khuyết | **EN**: Cloze Test

**Description**: Three subtypes for English testing (Cambridge FCE, IELTS, Vietnamese exams):
- Grammar-based: Articles, prepositions, tenses, conjunctions
- Vocabulary-based: Synonyms, antonyms, word choice
- Contextual: Full passage understanding

**Difficulty**: Understand -> Evaluate
**Supported by**: Worksheet, Quiz, Drill, Recap

```json
{
  "type": "cloze_mixed",
  "clozeSubtype": "contextual",
  "passage": "The Amazon rainforest, often {{1}} as the 'lungs of the Earth,' plays a {{2}} role...",
  "blanks": [
    { "id": 1, "correctAnswer": "referred", "type": "vocabulary" },
    { "id": 2, "correctAnswer": "crucial", "type": "vocabulary" },
    { "id": 3, "correctAnswer": "However", "type": "grammar" }
  ],
  "wordBank": ["referred", "crucial", "However", "called", "important", "Therefore"],
  "cefr": "B2",
  "difficulty": "understand"
}
```

---

### 2.3 Matching: Word-Definition, Synonym-Antonym
**VN**: Ghép: Từ-Định nghĩa, Đồng nghĩa-Trái nghĩa

**Description**: Classic receptive vocabulary test format (Nation's VLT, Schmitt's UVLT). Two-column matching with distractors.

**Difficulty**: Remember
**Supported by**: Worksheet, Drill, Lesson

```json
{
  "type": "matching_vocabulary",
  "matchType": "definition",
  "leftColumn": [
    { "id": "L1", "text": "Ephemeral" },
    { "id": "L2", "text": "Pernicious" }
  ],
  "rightColumn": [
    { "id": "R1", "text": "Lasting for a very short time" },
    { "id": "R2", "text": "Having a harmful effect" },
    { "id": "R3", "text": "Extremely delicate", "isDistractor": true }
  ],
  "difficulty": "remember"
}
```

---

### 2.4 Reading Comprehension with Annotation
**VN**: Đọc hiểu có chú thích | **EN**: Reading Comprehension with Annotation

**Description**: Passage + comprehension questions at multiple levels (literal, inferential, evaluative). Vietnamese format: 4 points of Literature exam. Includes annotation/highlighting.

**Difficulty**: Understand -> Evaluate
**Supported by**: Lesson, Worksheet, Quiz, Recap

```json
{
  "type": "reading_comprehension",
  "passage": {
    "text": "Climate change is one of the most pressing issues...",
    "source": "Adapted from National Geographic",
    "wordCount": 350,
    "cefr": "B2"
  },
  "annotationTools": ["highlight", "underline", "comment"],
  "questions": [
    { "type": "multiple_choice_single", "stem": "What is the main idea?", "level": "main_idea" },
    { "type": "short_answer", "stem": "What does 'tipping point' mean in line 15?", "level": "vocabulary_in_context" },
    { "type": "essay", "prompt": "Do you agree with the author?", "level": "evaluative" }
  ],
  "difficulty": "understand"
}
```

---

### 2.5 Grammar Transformation
**VN**: Biến đổi câu | **EN**: Sentence Transformation

**Description**: Rewrite a sentence with given structure while preserving meaning. Core of Vietnamese English exams and Cambridge FCE Use of English.

**Difficulty**: Apply
**Supported by**: Worksheet, Drill, Quiz

```json
{
  "type": "grammar_transformation",
  "sourceSentence": "I haven't been to the cinema for months. (since)",
  "expectedAnswer": "It has been months since I last went to the cinema.",
  "acceptableAnswers": ["It's been months since I last went to the cinema."],
  "grammarPoint": "present_perfect_since",
  "difficulty": "apply"
}
```

---

### 2.6 Error Correction / Identification
**VN**: Tìm và sửa lỗi sai | **EN**: Error Correction / Identification

**Description**: Two variants: **Identification** (find error in A/B/C/D) -- Vietnamese exam staple, and **Correction** (find AND fix).

**Difficulty**: Analyze
**Supported by**: Worksheet, Drill, Quiz, Recap

```json
{
  "type": "error_correction",
  "subtype": "identification",
  "sentence": "The students (A) [was] (B) [excited] about the (C) [upcoming] (D) [field trip].",
  "errorLocation": "A",
  "correction": "were",
  "grammarPoint": "subject_verb_agreement",
  "difficulty": "analyze"
}
```

---

### 2.7 Sentence Combining / Splitting
**VN**: Kết hợp / Tách câu | **EN**: Sentence Combining / Splitting

**Description**: Combine simple sentences into complex/compound, or split complex sentences into simpler ones.

**Difficulty**: Apply -> Analyze
**Supported by**: Worksheet, Drill

```json
{
  "type": "sentence_manipulation",
  "subtype": "combining",
  "inputSentences": ["The rain stopped.", "We went for a walk."],
  "expectedOutput": "After the rain stopped, we went for a walk.",
  "targetStructure": "complex_sentence_time_clause",
  "difficulty": "apply"
}
```

---

### 2.8 Paraphrase Exercises
**VN**: Diễn đạt lại | **EN**: Paraphrasing

**Description**: Express same meaning using different words/structures. Essential for IELTS/TOEFL/advanced writing.

**Difficulty**: Apply -> Create
**Supported by**: Worksheet, Lesson, Quiz

```json
{
  "type": "paraphrase",
  "originalSentence": "The increase in temperature has led to dramatic changes in weather patterns.",
  "techniques": ["synonym_substitution", "voice_change", "word_form_change", "structure_reordering"],
  "sampleAnswer": "Weather patterns have changed dramatically as a result of rising temperatures.",
  "rubric": {
    "criteria": [
      { "name": "Meaning Preservation", "weight": 40 },
      { "name": "Vocabulary Range", "weight": 30 },
      { "name": "Grammatical Accuracy", "weight": 30 }
    ]
  },
  "difficulty": "apply"
}
```

---

### 2.9 Dialogue Completion
**VN**: Hoàn thành hội thoại | **EN**: Dialogue Completion

**Description**: Complete a conversation with missing lines. Tests functional language and social register.

**Difficulty**: Apply
**Supported by**: Worksheet, Lesson, Drill

```json
{
  "type": "dialogue_completion",
  "context": "Tom and Anna meet for the first time at a conference.",
  "dialogue": [
    { "speaker": "Tom", "text": "Hi, I'm Tom." },
    { "speaker": "Anna", "text": "{{1}}" },
    { "speaker": "Tom", "text": "What brings you here?" },
    { "speaker": "Anna", "text": "{{2}}" }
  ],
  "blanks": [
    { "id": 1, "expectedIntent": "greeting", "expectedAnswer": "Nice to meet you, Tom. I'm Anna." },
    { "id": 2, "expectedIntent": "explain_purpose", "expectedAnswer": "I'm here to learn about AI developments." }
  ],
  "difficulty": "apply"
}
```

---

### 2.10 Phonics Worksheets (Sound-Letter Mapping)
**VN**: Ngữ âm: Ghép âm-chữ | **EN**: Phonics (Sound-Letter Mapping)

**Description**: For early literacy. Match sounds to letters. Pronunciation identification for Vietnamese English exams.

**Difficulty**: Remember
**Supported by**: Worksheet, Lesson, Drill

```json
{
  "type": "phonics",
  "subtype": "sound_identification",
  "instruction": "Which word has a different sound?",
  "items": [
    { "words": ["cat", "bat", "mate", "hat"], "correctIndex": 2, "reason": "'mate' has /eI/, others have /ae/" },
    { "words": ["phone", "graph", "photo", "potato"], "correctIndex": 3, "reason": "'potato' has /p/, others /f/" }
  ],
  "cefr": "A1-A2",
  "difficulty": "remember"
}
```

---

### 2.11 Dictation Exercises
**VN**: Chính tả / Nghe viết | **EN**: Dictation

**Description**: Teacher/audio reads a passage; student writes it verbatim. Tests listening + spelling + grammar.

**Difficulty**: Understand
**Supported by**: Lesson, Worksheet, Quiz

```json
{
  "type": "dictation",
  "text": "The quick brown fox jumps over the lazy dog.",
  "mode": "sentence_by_sentence",
  "grading": { "exactMatch": true, "ignorePunctuation": true, "caseSensitive": false },
  "difficulty": "understand"
}
```

---

### 2.12 Translation Exercises (EN <-> VI)
**VN**: Dịch (Anh <-> Việt) | **EN**: Translation (EN <-> VI)

**Description**: Translate between English and Vietnamese. Essential for Vietnamese English classes. EN->VI (decoding) and VI->EN (encoding/production).

**Difficulty**: Apply -> Create
**Supported by**: Worksheet, Drill, Lesson, Quiz

```json
{
  "type": "translation",
  "direction": "en_to_vi",
  "sourceText": "The advancement of technology has transformed the way we communicate.",
  "expectedTranslation": "Sự tiến bộ của công nghệ đã thay đổi cách chúng ta giao tiếp.",
  "focusPoints": [
    { "source": "advancement", "note": "Can be 'tien bo' or 'phat trien'" },
    { "source": "has transformed", "note": "Present perfect -> da + verb in Vietnamese" }
  ],
  "difficulty": "apply"
}
```

---

### 2.13 Idiomatic Expressions
**VN**: Thành ngữ | **EN**: Idiomatic Expressions

**Description**: Practice idioms through matching, gap-fill, context identification, and production.

**Difficulty**: Understand -> Apply
**Supported by**: Worksheet, Drill, Lesson

```json
{
  "type": "idioms",
  "activity": {
    "type": "match_meaning",
    "idioms": [
      { "idiom": "break the ice", "meaning": "To initiate conversation socially" },
      { "idiom": "hit the nail on the head", "meaning": "To describe exactly what is causing a situation" },
      { "idiom": "bite the bullet", "meaning": "To endure a painful situation bravely" }
    ]
  },
  "difficulty": "understand"
}
```

---

### 2.14 Collocation Exercises
**VN**: Kết hợp từ | **EN**: Collocation Exercises

**Description**: Practice natural word partnerships. Types: adjective+noun, verb+noun, adverb+adjective, verb+preposition.

**Difficulty**: Understand -> Apply
**Supported by**: Worksheet, Drill

```json
{
  "type": "collocation",
  "collocationType": "verb_noun",
  "leftItems": ["make", "do", "take", "have"],
  "rightItems": ["a decision", "homework", "a break", "a shower", "a mistake"],
  "correctPairs": [
    { "left": "make", "right": "a decision" },
    { "left": "do", "right": "homework" },
    { "left": "take", "right": "a break" },
    { "left": "have", "right": "a shower" }
  ],
  "difficulty": "understand"
}
```

---

### 2.15 Prefix/Suffix/Root Word Analysis
**VN**: Phân tích tiền tố/hậu tố/gốc từ | **EN**: Word Analysis

**Description**: Break down words into morphemes. Build vocabulary through word families.

**Difficulty**: Remember -> Analyze
**Supported by**: Lesson, Worksheet, Drill

```json
{
  "type": "word_analysis",
  "word": "unbelievable",
  "morphemes": [
    { "part": "un", "type": "prefix", "meaning": "not" },
    { "part": "believe", "type": "root", "meaning": "to accept as true" },
    { "part": "able", "type": "suffix", "meaning": "capable of" }
  ],
  "questions": [
    { "stem": "What does 'unbelievable' mean?", "correctAnswer": "not capable of being believed" }
  ],
  "difficulty": "remember"
}
```

---

### 2.16 Tense Timeline Exercises
**VN**: Bài tập thì qua trục thời gian | **EN**: Tense Timeline

**Description**: Visual timeline-based tense identification. Place events on a timeline and choose appropriate tense.

**Difficulty**: Understand -> Apply
**Supported by**: Lesson, Worksheet, Drill, Recap

```json
{
  "type": "tense_timeline",
  "events": [
    { "time": "past_perfect", "label": "had finished homework" },
    { "time": "past_simple", "label": "went to bed" },
    { "time": "present", "label": "now" },
    { "time": "future", "label": "will wake up" }
  ],
  "questions": [
    { "stem": "By the time he went to bed, he ___ his homework.", "correctAnswer": "had finished", "tense": "past_perfect" }
  ],
  "difficulty": "understand"
}
```

---

### 2.17 Conditional Sentence Builders
**VN**: Câu điều kiện | **EN**: Conditional Sentence Builders

**Description**: Practice Type 0, 1, 2, 3 and mixed conditionals. Includes identification, completion, transformation.

**Difficulty**: Apply -> Create
**Supported by**: Lesson, Worksheet, Drill, Quiz

```json
{
  "type": "conditional_builder",
  "conditionals": ["type0", "type1", "type2", "type3", "mixed"],
  "activities": [
    {
      "subtype": "completion",
      "stem": "If I ___ (know) about the party, I ___ (come).",
      "correctAnswer": "had known, would have come",
      "conditionalType": "type3"
    },
    {
      "subtype": "transformation",
      "sourceSentence": "She didn't study, so she failed.",
      "expectedAnswer": "If she had studied, she wouldn't have failed.",
      "conditionalType": "type3"
    }
  ],
  "difficulty": "apply"
}
```

---

### 2.18 Reported Speech Conversion
**VN**: Câu tường thuật | **EN**: Reported Speech Conversion

**Description**: Convert direct speech to indirect speech. Tense shift, pronoun changes, time/place adjustments.

**Difficulty**: Apply
**Supported by**: Worksheet, Drill, Quiz

```json
{
  "type": "reported_speech",
  "directSpeech": "\"I am going to the market tomorrow,\" she said.",
  "expectedAnswer": "She said that she was going to the market the next day.",
  "changes": [
    { "from": "I", "to": "she", "type": "pronoun" },
    { "from": "am going", "to": "was going", "type": "tense" },
    { "from": "tomorrow", "to": "the next day", "type": "time" }
  ],
  "difficulty": "apply"
}
```

---

### 2.19 Passive Voice Transformation
**VN**: Câu bị động | **EN**: Passive Voice Transformation

**Description**: Convert active <-> passive voice across all tenses. Core of Vietnamese English grammar exams.

**Difficulty**: Apply
**Supported by**: Worksheet, Drill, Quiz

```json
{
  "type": "passive_voice",
  "direction": "active_to_passive",
  "activeSentence": "The chef prepares the meal every evening.",
  "expectedPassive": "The meal is prepared by the chef every evening.",
  "tense": "present_simple",
  "difficulty": "apply"
}
```

---

## 3. Math/Science Special Exercise Types

### 3.1 Step-by-Step Problem Solving with Verification
**VN**: Giải bài toán từng bước có kiểm chứng | **EN**: Step-by-Step Problem Solving

**Description**: Problem broken into scaffolded steps. Each step verified. Supports CGI types: Join, Separate, Part-Part-Whole, Compare, Group.

**Difficulty**: Apply -> Evaluate
**Supported by**: Lesson, Worksheet, Drill, Recap

```json
{
  "type": "step_by_step_math",
  "cgiType": "join_result_unknown",
  "problem": "Ann had 6 pencils. Juan gave her 8 more. How many now?",
  "steps": [
    { "order": 1, "instruction": "Starting amount: ___ pencils", "type": "fill_blank", "correctAnswer": "6" },
    { "order": 2, "instruction": "Juan gave her ___ more", "type": "fill_blank", "correctAnswer": "8" },
    { "order": 3, "instruction": "Operation?", "type": "multiple_choice_single", "options": [
      { "id": "A", "text": "Addition (+)", "isCorrect": true },
      { "id": "B", "text": "Subtraction (-)", "isCorrect": false }
    ]},
    { "order": 4, "instruction": "Number sentence: ___ + ___ = ___", "type": "fill_blank_free", "correctAnswer": "6 + 8 = 14" },
    { "order": 5, "instruction": "Verify: Is 6+8=14 correct?", "type": "true_false", "correctAnswer": true }
  ],
  "difficulty": "apply"
}
```

---

### 3.2 Geometric Proof Builder
**VN**: Chứng minh hình học | **EN**: Geometric Proof Builder

**Description**: Construct proof step by step. Given + diagram -> Prove. Fill in reasons. Two-column or paragraph format.

**Difficulty**: Evaluate
**Supported by**: Lesson, Worksheet, Drill

```json
{
  "type": "geometric_proof",
  "diagram": { "type": "triangle", "givens": ["AB = AC", "angle BAD = angle CAD"] },
  "prove": "BD = CD",
  "format": "two_column",
  "steps": [
    { "statement": "AB = AC", "reason": "Given", "type": "given" },
    { "statement": "angle BAD = angle CAD", "reason": "Given", "type": "given" },
    { "statement": "AD = AD", "reason": "Reflexive Property", "type": "inference" },
    { "statement": "Triangle ABD = Triangle ACD", "reason": "__", "type": "blank", "correctReason": "SAS" },
    { "statement": "BD = CD", "reason": "__", "type": "blank", "correctReason": "CPCTC" }
  ],
  "difficulty": "evaluate"
}
```

---

### 3.3 Data Interpretation (Charts, Graphs, Tables)
**VN**: Đọc và phân tích dữ liệu | **EN**: Data Interpretation

**Description**: Interpret information from visual data. Line graphs, bar charts, pie charts, scatter plots, tables.

**Difficulty**: Understand -> Evaluate
**Supported by**: Lesson, Worksheet, Quiz, Recap

```json
{
  "type": "data_interpretation",
  "dataDisplay": {
    "type": "line_graph",
    "title": "Global Temperature Change (2000-2025)",
    "xAxis": "Year", "yAxis": "Temp Anomaly (C)",
    "data": [{ "x": 2000, "y": 0.42 }, { "x": 2010, "y": 0.73 }, { "x": 2020, "y": 1.02 }]
  },
  "questions": [
    { "type": "short_answer", "stem": "Temp anomaly in 2010?", "correctAnswer": "0.73C", "level": "literal" },
    { "type": "short_answer", "stem": "Rate of change per decade?", "correctAnswer": "0.2C", "level": "computational" }
  ],
  "difficulty": "understand"
}
```

---

### 3.4 Lab Report Template
**VN**: Báo cáo thí nghiệm | **EN**: Lab Report

**Description**: Structured scientific report following scientific method. Scaffolded template. Based on NGSS practices.

**Difficulty**: Apply -> Create
**Supported by**: Lesson, Worksheet

```json
{
  "type": "lab_report",
  "experimentTitle": "The Effect of Light on Plant Growth",
  "sections": [
    { "name": "question", "prompt": "What question are you investigating?" },
    { "name": "hypothesis", "prompt": "Write hypothesis using If...then...because..." },
    { "name": "variables", "fields": [
      { "label": "Independent variable" },
      { "label": "Dependent variable" },
      { "label": "Controlled variables" }
    ]},
    { "name": "materials", "type": "list" },
    { "name": "procedure", "type": "numbered_steps" },
    { "name": "data_table", "columns": ["Day", "Plant A", "Plant B", "Plant C"], "rows": 7 },
    { "name": "results", "prompt": "What patterns do you notice?" },
    { "name": "conclusion", "prompt": "Did evidence support hypothesis?" },
    { "name": "error_analysis", "prompt": "Sources of error?", "optional": true }
  ],
  "difficulty": "apply"
}
```

---

### 3.5 Measurement Activities
**VN**: Bài tập đo lường | **EN**: Measurement Activities

**Description**: Practice reading measurement tools (ruler, thermometer, scale, graduated cylinder, protractor), unit conversion, estimation.

**Difficulty**: Understand -> Apply
**Supported by**: Worksheet, Lesson, Drill

```json
{
  "type": "measurement",
  "subtype": "tool_reading",
  "tool": { "type": "graduated_cylinder", "readings": [{ "value": 47, "unit": "mL", "tolerance": 1 }] },
  "questions": [
    { "stem": "What is the volume of liquid?", "correctAnswer": "47 mL", "tolerance": 1 }
  ],
  "difficulty": "understand"
}
```

---

### 3.6 Code / Algorithm Exercises
**VN**: Bài tập lập trình / Thuật toán | **EN**: Code / Algorithm Exercises

**Description**: For Informatics (Tin hoc) -- new elective in 2026 exam. Pseudo-code reading, algorithm tracing, bug finding.

**Difficulty**: Apply -> Create
**Supported by**: Lesson, Worksheet, Drill, Quiz

```json
{
  "type": "coding_exercise",
  "subtype": "trace_output",
  "language": "python",
  "codeBlock": "x = 5\ny = 3\nx = x + y\nprint(x)",
  "question": "What will be the output?",
  "correctAnswer": "8",
  "difficulty": "apply"
}
```

---

### 3.7 Financial Literacy Activities
**VN**: Bài tập tài chính cá nhân | **EN**: Financial Literacy Activities

**Description**: Part of GDPT 2018's GDKT&PL subject. Budgeting, compound interest, taxes, savings, investment math.

**Difficulty**: Apply -> Evaluate
**Supported by**: Lesson, Worksheet, Quiz

```json
{
  "type": "financial_literacy",
  "scenario": "Lan has 5,000,000 VND. She deposits at 6% annual interest, compounded monthly for 2 years.",
  "questions": [
    { "type": "short_answer", "stem": "Write the compound interest formula.", "correctAnswer": "A = P(1+r/n)^(nt)" },
    { "type": "short_answer", "stem": "Calculate final amount.", "correctAnswer": "5,636,000 VND", "tolerance": 10000 }
  ],
  "difficulty": "apply"
}
```

---

## 4. Special Homework Formats (Multimedia)

*Based on 2026 Google Classroom AVS updates, Seesaw creative tools, and UDL principles.*

### 4.1 Video Recording Assignment
**VN**: Bài tập quay video | **EN**: Video Recording Assignment

**Description**: Student records video response. Use cases: verbal explanation, demonstration, presentation, role-play. Google Classroom AVS supports up to 5 min. Research shows 3.56 effect size for UDL-based multimodal submission (2026 study).

**Difficulty**: Apply -> Create
**Supported by**: Lesson, Worksheet, Quiz, Recap

```json
{
  "type": "multimedia_video",
  "instructions": "Record a 2-minute video explaining how photosynthesis works.",
  "maxDuration": 120,
  "rubric": {
    "criteria": [
      { "name": "Content Accuracy", "weight": 40 },
      { "name": "Clarity of Explanation", "weight": 30 },
      { "name": "Presentation Quality", "weight": 30 }
    ]
  },
  "aiCheatMitigation": "Require spontaneous verbal reflection; ask personalized follow-up questions.",
  "difficulty": "apply"
}
```

---

### 4.2 Audio Recording / Podcast
**VN**: Bài tập ghi âm / Podcast | **EN**: Audio Recording

**Description**: Student records audio only. Good for: pronunciation, oral reading fluency, storytelling, interview, music.

**Difficulty**: Apply -> Create
**Supported by**: Lesson, Worksheet, Recap

```json
{
  "type": "multimedia_audio",
  "instructions": "Record yourself reading the poem aloud with proper intonation and emotion.",
  "maxDuration": 180,
  "rubric": {
    "criteria": [
      { "name": "Pronunciation", "weight": 30 },
      { "name": "Fluency", "weight": 25 },
      { "name": "Intonation & Stress", "weight": 25 },
      { "name": "Emotional Expression", "weight": 20 }
    ]
  },
  "difficulty": "apply"
}
```

---

### 4.3 Photo Documentation Assignment
**VN**: Bài tập chụp ảnh minh họa | **EN**: Photo Documentation

**Description**: Student takes photos as evidence of real-world learning. Seesaw's core format. Geometry in architecture, science experiments, nature journals.

**Difficulty**: Understand -> Evaluate
**Supported by**: Worksheet, Lesson, Recap

```json
{
  "type": "multimedia_photo",
  "instructions": "Find 3 examples of parallel lines in your neighborhood. Photograph and label them.",
  "minPhotos": 3,
  "maxPhotos": 5,
  "allowAnnotations": true,
  "questions": [
    "Describe where you found each example.",
    "What property confirms these are parallel lines?"
  ],
  "difficulty": "understand"
}
```

---

### 4.4 Real-World Experiment Documentation
**VN**: Bài tập thí nghiệm thực tế | **EN**: Real-World Experiment

**Description**: Student conducts experiment at home and documents (photos + video + written reflection).

**Difficulty**: Apply -> Evaluate
**Supported by**: Lesson, Worksheet

```json
{
  "type": "experiment_documentation",
  "experiment": {
    "title": "Build a Simple Circuit",
    "materials": ["AA battery", "light bulb", "copper wire", "tape"],
    "steps": ["Connect wire to battery positive", "Connect other end to bulb", "Complete circuit"]
  },
  "documentationRequirements": {
    "photos": { "min": 3 },
    "video": { "maxDuration": 60 },
    "writtenReflection": { "prompts": ["What happened?", "What would change with a stronger battery?"] }
  },
  "difficulty": "apply"
}
```

---

### 4.5 Parent-Child Collaborative Activity
**VN**: Hoạt động phụ huynh-con cái | **EN**: Parent-Child Activity

**Description**: Requires parent/guardian involvement. Seesaw's family engagement model. Family interviews, joint projects.

**Difficulty**: Understand -> Create
**Supported by**: Worksheet, Lesson

```json
{
  "type": "parent_child_activity",
  "title": "Family Recipe Story",
  "studentTasks": [
    { "task": "Interview a family member about a recipe", "format": "audio" },
    { "task": "Take photos of cooking process", "format": "photo" },
    { "task": "Write the recipe in English", "format": "writing" }
  ],
  "parentTasks": [
    { "task": "Share recipe with child" },
    { "task": "Sign completed work" }
  ],
  "difficulty": "understand"
}
```

---

### 4.6 Field Trip Journal
**VN**: Nhật ký tham quan | **EN**: Field Trip Journal

**Description**: Structured journal for educational trips -- museums, historical sites, nature parks.

**Difficulty**: Understand -> Evaluate
**Supported by**: Worksheet, Recap

```json
{
  "type": "field_trip_journal",
  "destination": "Vietnam Museum of Ethnology",
  "sections": [
    {
      "name": "pre_trip",
      "prompts": ["What do you already know?", "List 3 questions you want to answer."]
    },
    {
      "name": "during_trip",
      "format": "photo_plus_notes",
      "maxEntries": 5
    },
    {
      "name": "post_trip",
      "prompts": ["Most surprising thing?", "How does this connect to class?", "Would you recommend this trip?"]
    }
  ],
  "difficulty": "understand"
}
```

---

### 4.7 Art/Craft Project Documentation
**VN**: Bài tập thủ công / Mỹ thuật | **EN**: Art/Craft Project

**Description**: Student creates art or craft project and documents process. Seesaw portfolio format for elementary.

**Difficulty**: Create
**Supported by**: Worksheet, Recap

```json
{
  "type": "art_project",
  "prompt": "Create a 3D model of the water cycle using recycled materials.",
  "documentation": {
    "processPhotos": { "min": 3 },
    "finalPhoto": true,
    "writtenReflection": { "prompts": ["What materials did you use and why?", "What does each part represent?", "What was the hardest part?"] }
  },
  "rubric": {
    "criteria": [
      { "name": "Scientific Accuracy", "weight": 35 },
      { "name": "Creativity", "weight": 30 },
      { "name": "Effort & Craftsmanship", "weight": 35 }
    ]
  },
  "difficulty": "create"
}
```

---

## 5. Large-Scale Exam Prep

### 5.1 Question Bank Architecture (500-700 Questions)
**VN**: Ngân hàng câu hỏi (500-700 câu) | **EN**: Question Bank (500-700 Questions)

**Description**: Structure for massive question banks used in Vietnamese de cuong on tap (exam review outlines). Must support multi-dimensional categorization.

**Key Design Decisions**:
- **Categorization by**:
  1. Topic/Unit (thematic)
  2. Difficulty (Nhan biet / Thong hieu / Van dung / Van dung cao -- 4:3:3 ratio per MOET)
  3. Bloom's Taxonomy level (Remember / Understand / Apply / Analyze / Evaluate / Create)
  4. Question format (MC / TF / Short Answer / Essay)
  5. Exam variant mapping

- **Spaced Repetition Integration**: Questions marked with review intervals (1d, 3d, 7d, 14d, 30d)

- **Adaptive Testing**: Start easy, increase difficulty based on performance. Elo-rating per question.

- **Shuffle Strategies**: Per-variant seed-based shuffling. Questions AND options shuffled.

**Difficulty**: All levels
**Supported by**: Drill, Quiz, Recap

```json
{
  "type": "question_bank",
  "name": "Grade 12 Math Review Bank",
  "totalQuestions": 600,
  "distribution": {
    "difficulty": {
      "nhan_biet": { "count": 240, "ratio": 0.40 },
      "thong_hieu": { "count": 180, "ratio": 0.30 },
      "van_dung": { "count": 120, "ratio": 0.20 },
      "van_dung_cao": { "count": 60, "ratio": 0.10 }
    },
    "topics": [
      { "name": "Calculus", "count": 200, "difficultyDistribution": { "nb": 80, "th": 60, "vd": 40, "vdc": 20 } },
      { "name": "Algebra", "count": 150, "difficultyDistribution": { "nb": 60, "th": 45, "vd": 30, "vdc": 15 } },
      { "name": "Geometry", "count": 150, "difficultyDistribution": { "nb": 60, "th": 45, "vd": 30, "vdc": 15 } },
      { "name": "Probability & Stats", "count": 100, "difficultyDistribution": { "nb": 40, "th": 30, "vd": 20, "vdc": 10 } }
    ]
  },
  "examVariants": {
    "count": 24,
    "shuffleStrategy": "seed_based",
    "guaranteeUnique": true,
    "options": {
      "shuffleQuestions": true,
      "shuffleOptions": true,
      "ensureTopicCoverage": true
    }
  },
  "spacedRepetition": {
    "intervals": [1, 3, 7, 14, 30],
    "defaultNewInterval": 1,
    "masteryThreshold": 0.85,
    "reintroduceAfterDays": 90
  },
  "adaptiveTesting": {
    "enabled": true,
    "startingDifficulty": "thong_hieu",
    "adjustmentRule": "correct_2_steps_up",
    "reversionRule": "wrong_1_step_down",
    "maxDifficulty": "van_dung_cao",
    "minDifficulty": "nhan_biet"
  }
}
```

---

### 5.2 Exam Variant Generation
**VN**: Tạo mã đề thi | **EN**: Exam Variant Generation

**Description**: Generate N variants from a question bank. Each variant has same difficulty profile but different questions.

**Supported by**: Quiz, Drill (practice), Recap (exam simulation)

```json
{
  "type": "exam_variant",
  "variantId": "DE-001",
  "seed": 42,
  "structure": {
    "part1": { "format": "multiple_choice_single", "questionCount": 12, "pointsPerQuestion": 0.25, "totalPoints": 3.0 },
    "part2": { "format": "true_false_4item", "questionCount": 4, "scoring": "vietnamese_tf_2025", "totalPoints": 4.0 },
    "part3": { "format": "short_answer", "questionCount": 6, "pointsPerQuestion": 0.5, "totalPoints": 3.0 }
  },
  "questions": [
    { "bankId": "Q-0123", "position": 1, "part": 1, "variantOption": "C" },
    { "bankId": "Q-0456", "position": 2, "part": 1, "variantOption": "B" }
  ],
  "timeLimit": 90,
  "totalPoints": 10.0
}
```

---

## 6. Interactive & Gamified Formats

### 6.1 Timed Challenge (Countdown Timer)
**VN**: Thử thách thời gian | **EN**: Timed Challenge

**Description**: Each question has a countdown timer. Faster answers = bonus points. Kahoot-style live energy. Research shows timer increases engagement but can increase anxiety.

**Supported by**: Quiz, Drill

```json
{
  "type": "timed_challenge",
  "timerMode": "per_question",
  "defaultTimeLimit": 20,
  "difficultyTimeMultipliers": {
    "nhan_biet": 15,
    "thong_hieu": 20,
    "van_dung": 30,
    "van_dung_cao": 45
  },
  "scoring": {
    "basePoints": 1000,
    "timeBonus": true,
    "timeBonusFormula": "max(0, basePoints * (1 - elapsed/limit))",
    "streakBonus": 1.5
  }
}
```

---

### 6.2 Streak/Reward System
**VN**: Hệ thống chuỗi ngày/Phần thưởng | **EN**: Streak/Reward System

**Description**: Duolingo-style streaks for daily practice. Combos for consecutive correct answers. Streak Freeze mechanic.

**Supported by**: Drill, Quiz

```json
{
  "type": "streak_system",
  "dailyStreak": {
    "enabled": true,
    "resetHour": 0,
    "freezeItem": "streak_freeze",
    "freezeCost": 50
  },
  "combo": {
    "enabled": true,
    "multiplierStep": 0.1,
    "maxMultiplier": 2.0,
    "comboBreakOnWrong": true,
    "comboBreakOnTimeout": false
  }
}
```

---

### 6.3 Leaderboards (Anonymized)
**VN**: Bảng xếp hạng (ẩn danh) | **EN**: Leaderboards (Anonymized)

**Description**: Seasonal leaderboards (weekly, monthly, all-time). Anonymized for privacy. Self-progress beats social comparison for most learners. Research: micro-leaderboards per topic reduce demotivation.

**Supported by**: Quiz, Drill

```json
{
  "type": "leaderboard",
  "anonymized": true,
  "intervals": ["weekly", "monthly", "all_time"],
  "scoringMetric": "total_xp",
  "microLeaderboards": true,
  "microLeaderboardTopics": true,
  "displayCount": 20
}
```

---

### 6.4 Adaptive Difficulty
**VN**: Độ khó thích ứng | **EN**: Adaptive Difficulty

**Description**: System adjusts difficulty based on performance. Correct answers -> harder questions. Wrong answers -> easier. Elo-rating for questions. Research (Zhang & Huang, 2024): dissatisfaction decreases significantly (t(44)=10.13, p<.001) with adaptive difficulty.

**Supported by**: Drill, Quiz

```json
{
  "type": "adaptive_difficulty",
  "algorithm": "elo_based",
  "startingDifficulty": "thong_hieu",
  "adjustmentRules": {
    "correct_streak_2": { "action": "increase_difficulty", "target": "next_level" },
    "wrong_1": { "action": "decrease_difficulty", "target": "previous_level" },
    "correct_but_slow": { "action": "maintain" }
  },
  "eloConfig": {
    "kFactor": 32,
    "initialRating": 1200,
    "questionRatingRange": [800, 2000]
  },
  "targetAccuracy": 0.75
}
```

---

### 6.5 Branching Scenarios (Choose Your Adventure)
**VN**: Kịch bản phân nhánh | **EN**: Branching Scenarios

**Description**: Student makes decisions that affect the story outcome. Each choice leads to different questions/consequences. Strong narrative presence + agency. Research shows branching scenarios increase motivation and self-efficacy.

**Difficulty**: Apply -> Evaluate
**Supported by**: Lesson, Quiz

```json
{
  "type": "branching_scenario",
  "title": "Eco-City Planner",
  "initialPrompt": "You are the mayor of a new city. Choose your first priority:",
  "nodes": [
    {
      "id": "start",
      "prompt": "What is your first priority?",
      "choices": [
        { "text": "Build renewable energy", "nextNode": "energy_path", "xpReward": 100 },
        { "text": "Build public transport", "nextNode": "transport_path", "xpReward": 100 },
        { "text": "Build waste management", "nextNode": "waste_path", "xpReward": 100 }
      ]
    },
    {
      "id": "energy_path",
      "prompt": "Which energy source?",
      "choices": [
        { "text": "Solar farms", "nextNode": "solar_outcome", "xpReward": 150 },
        { "text": "Wind turbines", "nextNode": "wind_outcome", "xpReward": 150 }
      ],
      "question": { "type": "multiple_choice_single", "stem": "What is the main advantage of solar over wind?", "options": [...] }
    }
  ],
  "outcomes": {
    "success": "Your city is recognized as a sustainability leader!",
    "failure": "Budget constraints force a rollback of your plans..."
  }
}
```

---

### 6.6 Gamification Elements (Points, Badges, Levels, XP)
**VN**: Yếu tố game hóa | **EN**: Gamification Elements

**Description**: Points tied to effort. XP grows with difficulty. Badges for milestones. Levels for mastery. Research shows PBL (Points, Badges, Leaderboards) is most common but adaptive gamification is the 2026 trend.

**Supported by**: All artifacts

```json
{
  "type": "gamification_config",
  "xpScaling": {
    "nhan_biet": 10,
    "thong_hieu": 25,
    "van_dung": 50,
    "van_dung_cao": 100
  },
  "levels": [
    { "level": 1, "name": "Novice", "xpRequired": 0 },
    { "level": 2, "name": "Apprentice", "xpRequired": 200 },
    { "level": 3, "name": "Practitioner", "xpRequired": 500 },
    { "level": 4, "name": "Expert", "xpRequired": 1000 },
    { "level": 5, "name": "Master", "xpRequired": 2000 }
  ],
  "badges": [
    { "id": "first_completion", "name": "First Steps", "condition": "complete_first_quiz" },
    { "id": "streak_7", "name": "Week Warrior", "condition": "streak_7_days" },
    { "id": "perfect_score", "name": "Perfect", "condition": "score_100_percent" },
    { "id": "speed_demon", "name": "Speed Demon", "condition": "all_correct_under_5s" },
    { "id": "comeback", "name": "Comeback Kid", "condition": "improve_by_20_percent" },
    { "id": "explorer", "name": "Explorer", "condition": "try_all_artifact_types" }
  ]
}
```

---

### 6.7 Collaborative Group Activities
**VN**: Hoạt động nhóm | **EN**: Collaborative Group Activities

**Description**: Students work in teams. Roles assigned. Shared goal. Peer review. Based on cooperative learning theory.

**Difficulty**: Apply -> Create
**Supported by**: Lesson, Worksheet

```json
{
  "type": "collaborative_activity",
  "groupSize": { "min": 3, "max": 4 },
  "roles": ["researcher", "writer", "presenter", "fact_checker"],
  "structure": "jigsaw",
  "task": "Each group researches one renewable energy source, then teaches it to other groups.",
  "deliverable": "group_presentation",
  "peerReview": {
    "enabled": true,
    "criteria": ["contribution", "accuracy", "clarity"]
  },
  "difficulty": "apply"
}
```

---

## 7. Vietnamese Education System Requirements

### 7.1 MOET Exam Structure (2025+)
**VN**: Cấu trúc đề thi Bộ GD&ĐT từ 2025 | **EN**: MOET Exam Structure from 2025

**Source**: Quyet dinh 764/QD-BGDDT, Thong tu 32/2018/TT-BGDDT (GDPT 2018)

**Key Facts**:
- **4 compulsory subjects**: Literature (essay, 120min), Math (MC, 90min), 2 electives (MC, 50min each)
- **3 MC formats**: Multiple choice (single), True/False (4-item), Short answer
- **Difficulty ratio**: 4:3:3 (Nhan biet : Thong hieu : Van dung)
- **Knowledge scope**: Primarily grade 12, includes grade 10-11
- **Electives**: Physics, Chemistry, Biology, History, Geography, GDKT&PL, Informatics, Technology, Foreign Languages
- **English exam structure**: Includes pronunciation, error identification, cloze, reading comprehension, transformation, paragraph writing

### 7.2 Bloom's Taxonomy for Vietnamese Education
**VN**: Thang Bloom trong giáo dục Việt Nam | **EN**: Bloom's Taxonomy in Vietnamese Education

| Level | Vietnamese | Description | Question Types |
|-------|-----------|-------------|----------------|
| 1 - Remember | Nhan biet | Recall facts, terms | MC, Matching, Fill blank |
| 2 - Understand | Thong hieu | Explain concepts | MC, Short answer, Cloze |
| 3 - Apply | Van dung | Use in new situations | Transformation, Problem solving |
| 4 - Analyze | Phan tich | Break down, find patterns | Error correction, Data interpretation |
| 5 - Evaluate | Danh gia | Judge, justify | Essay, True/False 4-item |
| 6 - Create | Sang tao | Produce new work | Essay, Art project, Coding |

### 7.3 Competency Assessment (Thong tu 22/2021)
**VN**: Đánh giá năng lực theo Thông tư 22/2021 | **EN**: Competency Assessment

- Formative assessment (danh gia thuong xuyen): Performance tasks, projects, portfolios
- Summative assessment (danh gia dinh ky): Written tests, practical exams
- Competencies assessed: Self-regulation, Communication, Collaboration, Problem-solving, Creativity
- Qualities (pham chat): Patriotism, Compassion, Responsibility, Honesty, Diligence

---

## 8. IMS QTI Standards Alignment

### 8.1 Key QTI Concepts
**Source**: IMS QTI v3.0 Specification

The system should map to QTI concepts for interoperability:

| QTI Concept | Our Equivalent | Notes |
|------------|----------------|-------|
| assessmentItem | question | Each exercise is a QTI item |
| assessmentSection | question_group | Topic-based grouping |
| assessmentTest | quiz / exam | Full assessment with timing |
| responseDeclaration | correctAnswer | Declares correct response |
| outcomeDeclaration | scoring | How to score (score, points) |
| responseProcessing | grading_rules | Match-correct, map-response |
| interaction | question_type | Choice, textEntry, match, etc. |
| modalFeedback | explanation | Shown after submission |
| adaptive | adaptiveDifficulty | QTI adaptive attribute |
| timeDependent | timedChallenge | QTI timeDependent attribute |
| rubricBlock | rubric | Performance rubrics |
| templateDeclaration | params | Parameterized questions |

### 8.2 QTI Interaction Types Mapped
| QTI Interaction | Our Type | Description |
|----------------|----------|-------------|
| choiceInteraction | multiple_choice_single | Select from options |
| choiceInteraction (multiple) | multiple_choice_multiple | Select multiple |
| inlineChoiceInteraction | fill_blank_wordbank | Dropdown in text |
| textEntryInteraction | cloze / short_answer | Type response |
| extendedTextInteraction | essay | Long text |
| matchInteraction | matching | Two-column matching |
| orderInteraction | ordering | Reorder items |
| associateInteraction | drag_and_drop | Connect items |
| uploadInteraction | multimedia_video | File upload |
| drawingInteraction | drawing | Canvas drawing |
| sliderInteraction | measurement | Interactive slider |
| gapMatchInteraction | drag_gap_fill | Drag words into gaps |
| graphicOrderInteraction | graphic_ordering | Order elements on image |

---

## 9. Master Schema: Question Union Type

```typescript
// TypeScript type representing ALL question types the system supports

type QuestionType =
  // === ASSESSMENT FORMATS (Section 1) ===
  | MultipleChoiceSingle
  | MultipleChoiceMultiple
  | TrueFalse4Item
  | ShortAnswer
  | Essay
  | FillBlankWordBank
  | Cloze
  | Matching
  | Ordering
  | DragAndDrop
  | Drawing
  | Performance

  // === ENGLISH LANGUAGE (Section 2) ===
  | VocabularyScaffolded
  | ClozeMixed
  | MatchingVocabulary
  | ReadingComprehension
  | GrammarTransformation
  | ErrorCorrection
  | SentenceManipulation
  | Paraphrase
  | DialogueCompletion
  | Phonics
  | Dictation
  | Translation
  | Idioms
  | Collocation
  | WordAnalysis
  | TenseTimeline
  | ConditionalBuilder
  | ReportedSpeech
  | PassiveVoice

  // === MATH/SCIENCE (Section 3) ===
  | StepByStepMath
  | GeometricProof
  | DataInterpretation
  | LabReport
  | Measurement
  | CodingExercise
  | FinancialLiteracy

  // === MULTIMEDIA HOMEWORK (Section 4) ===
  | MultimediaVideo
  | MultimediaAudio
  | MultimediaPhoto
  | ExperimentDocumentation
  | ParentChildActivity
  | FieldTripJournal
  | ArtProject

  // === GAMIFIED / INTERACTIVE (Section 6) ===
  | TimedChallenge
  | BranchingScenario
  | CollaborativeActivity;

// Common base for ALL question types
interface BaseQuestion {
  id: string;
  type: string;
  difficulty: 'remember' | 'understand' | 'apply' | 'analyze' | 'evaluate' | 'create';
  bloomLevel?: 'nhan_biet' | 'thong_hieu' | 'van_dung' | 'van_dung_cao';
  tags: string[];
  metadata: {
    subject: string;
    grade: number;
    topic: string;
    lessonId?: string;
    estimatedTimeSeconds?: number;
    author?: string;
    createdAt?: string;
    updatedAt?: string;
  };
}

// Scoring system shared across types
interface ScoringConfig {
  type: 'all_or_nothing' | 'partial_credit' | 'vietnamese_tf_2025';
  pointsTotal?: number;
  penaltyPerWrong?: number;
}

// Rubric shared across essay, performance, drawing
interface Rubric {
  criteria: Array<{
    name: string;
    weight: number;
    levels?: Array<{ score: number; description: string }>;
    descriptors?: Record<string, string>;
  }>;
}
```

---

## 10. Artifact Type Matrix

Which exercise types are supported by which artifact (lesson, worksheet, quiz, drill, recap)?

| # | Exercise Type | Lesson | Worksheet | Quiz | Drill | Recap |
|---|---------------|--------|-----------|------|-------|-------|
| **Assessment Formats** | | | | | | |
| 1.1 | Multiple Choice Single | X | X | X | X | X |
| 1.2 | Multiple Choice Multiple | | X | X | X | |
| 1.3 | True/False 4-item | | | X | X | X |
| 1.4 | Short Answer | | X | X | X | X |
| 1.5 | Essay | X | X | X | | |
| 1.6 | Fill Blank (Word Bank) | X | X | | X | |
| 1.7 | Cloze / Gap Fill | | X | X | X | |
| 1.8 | Matching | X | X | | X | |
| 1.9 | Ordering | | X | X | X | |
| 1.10 | Drag and Drop | X | | X | X | |
| 1.11 | Drawing | X | X | | | X |
| 1.12 | Performance | X | | X | | X |
| **English Exercises** | | | | | | |
| 2.1 | Vocabulary Scaffolded | X | X | | X | X |
| 2.2 | Cloze Mixed | | X | X | X | X |
| 2.3 | Matching Vocabulary | X | X | | X | |
| 2.4 | Reading Comprehension | X | X | X | | X |
| 2.5 | Grammar Transformation | | X | X | X | |
| 2.6 | Error Correction | | X | X | X | X |
| 2.7 | Sentence Manipulation | | X | | X | |
| 2.8 | Paraphrase | X | X | X | | |
| 2.9 | Dialogue Completion | X | X | | X | |
| 2.10 | Phonics | X | X | | X | |
| 2.11 | Dictation | X | X | X | | |
| 2.12 | Translation | X | X | X | X | |
| 2.13 | Idioms | X | X | | X | |
| 2.14 | Collocation | | X | | X | |
| 2.15 | Word Analysis | X | X | | X | |
| 2.16 | Tense Timeline | X | X | | X | X |
| 2.17 | Conditional Builder | X | X | X | X | |
| 2.18 | Reported Speech | | X | X | X | |
| 2.19 | Passive Voice | | X | X | X | |
| **Math/Science** | | | | | | |
| 3.1 | Step-by-Step Math | X | X | | X | X |
| 3.2 | Geometric Proof | X | X | | X | |
| 3.3 | Data Interpretation | X | X | X | | X |
| 3.4 | Lab Report | X | X | | | |
| 3.5 | Measurement | X | X | | X | |
| 3.6 | Coding Exercise | X | X | X | X | |
| 3.7 | Financial Literacy | X | X | X | | |
| **Multimedia Homework** | | | | | | |
| 4.1 | Video Recording | X | X | X | | X |
| 4.2 | Audio Recording | X | X | | | X |
| 4.3 | Photo Documentation | | X | | | X |
| 4.4 | Experiment Doc | X | X | | | |
| 4.5 | Parent-Child Activity | X | X | | | |
| 4.6 | Field Trip Journal | | X | | | X |
| 4.7 | Art Project | | X | | | X |
| **Gamified** | | | | | | |
| 6.1 | Timed Challenge | | | X | X | |
| 6.5 | Branching Scenario | X | | X | | |
| 6.7 | Collaborative Activity | X | X | | | |

---

## Appendix A: Key Research Sources

1. **IMS QTI v3.0** - Question and Test Interoperability standard (1EdTech)
2. **MOET Decision 764/QD-BGDDT** (2024) - Vietnamese exam format for 2025+
3. **Thong tu 32/2018/TT-BGDDT** - GDPT 2018 curriculum framework
4. **Thong tu 22/2021/TT-BGDDT** - Competency assessment regulations
5. **Google Classroom AVS Update** (Jan 2026) - Audio/video/screencast recording
6. **Seesaw Creative Tools** - Photo/video/drawing portfolio system
7. **UDL Research** (2026) - 3.56 effect size for multimodal submission
8. **Nation's Vocabulary Levels Test** - Receptive vocabulary assessment
9. **CGI Problem Types** (Carpenter et al., 2006) - Math problem classification
10. **Adaptive Gamification Research** (Zhang & Huang, 2024) - Difficulty calibration
11. **Kahoot vs Quizizz Analysis** (2026) - Self-paced vs live modes
12. **EFL Textbook Task Analysis** (2026) - Closed/semi-open/open task classification
