# Blueprint Designer Skill

## Purpose
Design lesson plans using backward design (UbD), Bloom's taxonomy, and Gagné's 9 Events of Instruction.

## Triggers
- "design a lesson plan"
- "create blueprint"
- "plan a lesson for Grade X"
- "UbD design"

## Workflow
1. Parse teacher request → extract topic, grade, subject, duration
2. Apply UbD framework: identify desired results → determine evidence → plan learning
3. Map learning objectives to Bloom's taxonomy (≥2 levels required)
4. Structure learning plan using Gagné's 9 Events
5. Define assessment checkpoints
6. Output: LessonPlan JSON (validate via Pydantic schema)

## Constraints
- Minimum 1, maximum 10 learning objectives
- Must cover ≥2 Bloom's taxonomy levels
- Duration: 10–180 minutes
- Grade-appropriate vocabulary and complexity
- Align with GDPT 2018 (Vietnamese curriculum) when applicable

## Output Schema
```python
class LessonPlan(BaseModel):
    topic: str
    grade_level: str
    subject: str
    duration_minutes: int
    learning_objectives: list[LearningObjective]
    prerequisite_knowledge: list[str]
    learning_plan: dict  # Gagné 9-event phases
    assessment_checkpoints: list[dict]
```
