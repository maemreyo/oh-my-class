export const ACTIVE_ARTIFACT_TYPES = [
  "lesson",
  "worksheet",
  "quiz",
  "drill",
  "recap",
  "infographic",
] as const;

export type ActiveArtifactType = (typeof ACTIVE_ARTIFACT_TYPES)[number];

export function richAgentArtifact(type: ActiveArtifactType) {
  const base = {
    artifact_type: type,
    theme: "default",
    title: `Equivalent Fractions ${type}`,
    metadata: {
      subject: "Math",
      grade_level: "Grade 5",
      summary: "A component-rich pack for comparing equivalent fractions.",
    },
    accessibility: { language: "en" },
  };

  switch (type) {
    case "lesson":
      return {
        ...base,
        sections: [
          {
            id: "objective",
            type: "objective",
            title: "Learning Targets",
            content: "Students compare equivalent fractions using area models and number lines.",
            components: [
              { type: "callout", variant: "note", title: "Teacher move", body: "Ask students to explain why the shaded area stays equal." },
              { type: "flow_step", steps: [{ time: "5 min", title: "Activate", body: "Compare two fraction strips." }] },
            ],
          },
          {
            id: "guided-practice",
            title: "Guided Practice",
            content: "Model how 1/2, 2/4, and 3/6 name the same amount.",
            components: [
              {
                type: "question_card",
                id: "lq1",
                text: "Which fraction is equivalent to 1/2?",
                options: { A: "1/3", B: "2/4", C: "3/5", D: "4/5" },
                answer: "B",
                explain: "2/4 covers the same area as 1/2 when both parts are equal.",
              },
            ],
          },
        ],
      };
    case "worksheet":
      return {
        ...base,
        sections: [
          {
            title: "Visual Models",
            content: "Shade each model, then explain which fractions are equivalent.",
            questions: [
              { id: "w1", prompt: "Shade 1/2 and 2/4. What stays the same?", type: "short_answer" },
              { id: "w2", prompt: "Draw a model for 3/6 that matches 1/2.", type: "long_answer" },
            ],
          },
          {
            title: "Number Line Check",
            content: "Place each fraction on a number line.",
            questions: [
              { id: "w3", prompt: "Mark 1/2 and 4/8 on the same line.", type: "short_answer" },
              { id: "w4", prompt: "Explain why both marks overlap.", type: "short_answer" },
            ],
          },
        ],
      };
    case "quiz":
      return {
        ...base,
        sections: [
          { id: "q1", content: "Which fraction equals 1/2?", options: { A: "1/4", B: "2/4", C: "2/3", D: "3/4" }, answer: "B", explanation: "2/4 simplifies to 1/2." },
          { id: "q2", content: "Which pair is equivalent?", options: { A: "1/3 and 2/5", B: "2/6 and 1/3", C: "3/4 and 4/5", D: "1/2 and 3/5" }, answer: "B", explanation: "2/6 simplifies to 1/3." },
          { id: "q3", content: "What does equivalent mean?", options: { A: "same value", B: "same numerator", C: "larger denominator", D: "different shape" }, answer: "A", explanation: "Equivalent fractions have the same value." },
          { id: "q4", content: "Which model can prove equivalence?", options: { A: "area model", B: "spelling list", C: "weather chart", D: "story map" }, answer: "A", explanation: "Area models show equal parts visually." },
          { id: "q5", content: "Which fraction equals 3/6?", options: { A: "1/2", B: "1/4", C: "2/3", D: "5/6" }, answer: "A", explanation: "3/6 simplifies to 1/2." },
        ],
      };
    case "drill":
      return {
        ...base,
        sections: [
          { id: "d1", content: "Fill in: 1/2 = __/4", answer: "2", type: "fill" },
          { id: "d2", content: "Choose an equivalent fraction for 2/3.", options: { A: "4/6", B: "3/4", C: "2/5", D: "1/3" }, answer: "A", type: "question_card" },
          { id: "d3", content: "Fill in: 3/5 = 6/__", answer: "10", type: "fill" },
          { id: "d4", content: "True or false: 2/4 equals 1/2.", answer: "true", type: "tf" },
          { id: "d5", content: "Find a denominator that makes 4/8 = 1/__.", answer: "2", type: "fill" },
          { id: "d6", content: "Choose the pair with the same value.", options: { A: "3/6 and 1/2", B: "2/5 and 1/2", C: "4/9 and 1/3", D: "5/8 and 1/4" }, answer: "A", type: "question_card" },
        ],
      };
    case "recap":
      return {
        ...base,
        sections: [
          { title: "Same Value", content: "Equivalent fractions name the same amount even with different numerators and denominators." },
          { title: "Area Models", content: "Area models prove equivalence by showing equal shaded regions." },
          { title: "Common Mistake", content: "Do not compare only denominators; compare the value of the whole fraction." },
          { title: "Exit Reflection", content: "Write one pair of equivalent fractions and explain your proof." },
        ],
      };
    case "infographic":
      return {
        ...base,
        sections: [
          { title: "Equivalent Means Equal Value", content: "Different-looking fractions can land on the same point." },
          { title: "Model", content: "1/2 = 2/4 = 3/6", items: [{ label: "Area", value: "same shaded amount" }, { label: "Line", value: "same position" }] },
          { title: "Strategy", content: "Multiply or divide numerator and denominator by the same number." },
          { title: "Check", content: "Use a model before applying a shortcut." },
        ],
      };
  }
}
