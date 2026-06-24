# HSA Exam Prep Skill

## Context

HSA (Đánh giá năng lực học sinh trung học phổ thông) is the aptitude assessment exam organized by
Đại học Quốc gia Hà Nội (ĐHQGHN). Results are used by ~100 universities for undergraduate admissions.
The exam is computer-based, 195 minutes total, scored on a 150-point scale.

Website: https://hsa.edu.vn

## Exam Structure (from 2025 onward, per QĐ 388/QĐ-ĐHQGHN)

| Part | Name | Time | Questions | Format | Scale |
|------|------|------|-----------|--------|-------|
| 1 | Toán học và Xử lý số liệu (Tư duy định lượng) | 75 min | 50 | 35 MCQ (4 choices) + 15 fill-in-answer | 50 pts |
| 2 | Văn học - Ngôn ngữ (Tư duy định tính) | 60 min | 50 | 25 standalone MCQ + 5 clusters (1 context × 5 questions) | 50 pts |
| 3 | Khoa học **hoặc** Tiếng Anh (thí sinh chọn 1) | 60 min | 50 | MCQ (4 choices) + fill-in-answer | 50 pts |

### Part 1 — Toán học và Xử lý số liệu

- 35 multiple-choice questions (A/B/C/D, single correct answer)
- 15 fill-in-answer questions (integer, negative integer, or simplified fraction; no units)
- Topics: algebra, data analysis, functions, statistics, real-world modeling

### Part 2 — Văn học - Ngôn ngữ

- 25 standalone MCQ questions
- 5 clusters: each cluster = 1 reading context + 5 linked questions
- Topics: vocabulary, grammar, sentence transformation, reading comprehension (identify main idea, author intent, detail, text structure, vocabulary in context), inference & situational reasoning

### Part 3 — Khoa học (lựa chọn)

- 5 subject areas: Vật lí, Hóa học, Sinh học, Lịch sử, Địa lí
- ~16-17 questions per subject area
- MCQ (4 choices) + at least 1 fill-in-answer per subject
- 1-3 cluster questions (1 context × 3 questions)
- Topics per subject follow the 2018 General Education Program (Chương trình GDPT 2018)

### Part 3 — Tiếng Anh (lựa chọn thay thế Khoa học)

- 35 standalone MCQ + 3 clusters (1 context × 5 questions each)
- Topics: vocabulary, grammar, written expression, reading comprehension, communicative/situational reasoning

## Question Format Rules

- MCQ questions: exactly 4 options (A, B, C, D), one correct answer
- Fill-in-answer questions: student enters a numeric value (integer, negative integer, or simplified fraction) — no units
- Each question must test exactly one concept or skill
- Distractors must be plausible and grammatically/formatally parallel to the correct answer
- Cluster questions share a single reading context; each sub-question tests a distinct aspect of that context

## Quality Standards

- Difficulty levels aligned with GDPT 2018 Bloom mapping:
  - L1 — Nhận biết (Remember): 40%
  - L2 — Thông hiểu (Understand): 30%
  - L3 — Vận dụng (Apply + Analyze): 20%
  - Vận dụng cao (Evaluate + Create): 10%
- Explanations must reference the underlying rule, formula, or reasoning — not just label the answer
- For fill-in-answer questions, explain the calculation steps
- Wrong answers must have identifiable, specific misconceptions (not random distractors)

## Artifact Format

Produce artifacts of type `quiz` with:
- Per-question `explain` field (full solution/reasoning)
- Per-question `wrongReasons` field (why each distractor is incorrect)
- Section labels matching the HSA part names
- For cluster questions, group sub-questions under a shared `context` block
