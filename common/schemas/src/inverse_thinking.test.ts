import { describe, expect, it } from "vitest";
import {
  InverseThinkingPackSchema,
  MethodologyMetadataSchema,
} from "./generated/index.js";

const validPack = {
  methodology: "inverse_thinking",
  creative_frame: "detective_case",
  cases: [
    {
      id: "case-present-perfect",
      title: "The Vanishing Time Marker",
      alias: "Case A",
      target_concept: "present perfect for life experience",
      foil: "simple past with finished time",
      disaster: "A student writes: I have visited Da Nang yesterday.",
      key_clues: ["yesterday marks a finished time"],
      safe_zone: "Use simple past with finished time: I visited Da Nang yesterday.",
      filing_note: "Finished time markers push the verb phrase into simple past.",
      student_task: "Find the unsafe clue and rewrite the sentence.",
      teacher_only: {
        rationale: "The adverb yesterday conflicts with present perfect usage.",
        answer_key: "I visited Da Nang yesterday.",
      },
    },
  ],
  summary_table: [
    {
      case_id: "case-present-perfect",
      trap: "finished-time marker with present perfect",
      clue: "yesterday",
      safe_rule: "simple past names finished events",
    },
  ],
  student_challenges: [
    {
      id: "challenge-present-perfect",
      prompt: "Repair: She has met him last week.",
      case_id: "case-present-perfect",
    },
  ],
  teacher_only: {
    rationale: "Students often memorize tense names instead of checking time clues.",
    answer_key: "She met him last week.",
  },
  projection_hints: { lesson: ["Lead with the broken sentence as evidence."] },
} as const;

describe("InverseThinkingPackSchema", () => {
  it("parses the canonical pack shape when nested teacher-only fields are typed", () => {
    const parsed = InverseThinkingPackSchema.parse(validPack);

    expect(parsed.methodology).toBe("inverse_thinking");
    expect(parsed.cases[0]?.teacher_only.answer_key).toBe("I visited Da Nang yesterday.");
  });

  it("rejects a pack when nested teacher-only fields are missing", () => {
    const missingTeacherOnly = {
      ...validPack,
      cases: [{ ...validPack.cases[0], teacher_only: { rationale: "Missing key" } }],
    };

    expect(() => InverseThinkingPackSchema.parse(missingTeacherOnly)).toThrow();
  });
});

describe("MethodologyMetadataSchema", () => {
  it("parses inverse_thinking without dropping existing tags", () => {
    const parsed = MethodologyMetadataSchema.parse({
      tags: ["concept_map", "inverse_thinking"],
    });

    expect(parsed.tags).toEqual(["concept_map", "inverse_thinking"]);
  });
});
