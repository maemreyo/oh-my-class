import { z } from "zod";
import { BaseQuestionSchema, RubricSchema } from "./base.js";

// ── 3.1 Step-by-Step Math ──

export const StepByStepMathSchema = BaseQuestionSchema.extend({
  type: z.literal("step_by_step_math"),
  cgiType: z.enum([
    "join_result_unknown",
    "join_change_unknown",
    "join_start_unknown",
    "separate_result_unknown",
    "separate_change_unknown",
    "separate_start_unknown",
    "part_part_whole_total_unknown",
    "part_part_whole_part_unknown",
    "compare_difference_unknown",
    "compare_referent_unknown",
  ]),
  problem: z.string(),
  steps: z.array(
    z.object({
      order: z.number().int(),
      instruction: z.string(),
      type: z.enum([
        "fill_blank",
        "multiple_choice_single",
        "fill_blank_free",
        "true_false",
      ]),
      correctAnswer: z.union([z.string(), z.boolean()]),
      options: z
        .array(
          z.object({
            id: z.string(),
            text: z.string(),
            isCorrect: z.boolean(),
          }),
        )
        .optional(),
    }),
  ),
});

// ── 3.2 Geometric Proof ──

export const GeometricProofSchema = BaseQuestionSchema.extend({
  type: z.literal("geometric_proof"),
  diagram: z.object({
    type: z.string(),
    givens: z.array(z.string()),
  }),
  prove: z.string(),
  format: z.enum(["two_column", "paragraph"]),
  steps: z.array(
    z.object({
      statement: z.string(),
      reason: z.string(),
      type: z.enum(["given", "inference", "blank"]),
      correctReason: z.string().optional(),
    }),
  ),
});

// ── 3.3 Data Interpretation ──

export const DataInterpretationSchema = BaseQuestionSchema.extend({
  type: z.literal("data_interpretation"),
  dataDisplay: z.object({
    type: z.enum([
      "line_graph",
      "bar_chart",
      "pie_chart",
      "scatter_plot",
      "table",
    ]),
    title: z.string(),
    xAxis: z.string().optional(),
    yAxis: z.string().optional(),
    data: z.array(z.record(z.string(), z.unknown())),
  }),
  questions: z.array(z.record(z.string(), z.unknown())),
});

// ── 3.4 Lab Report ──

export const LabReportSchema = BaseQuestionSchema.extend({
  type: z.literal("lab_report"),
  experimentTitle: z.string(),
  sections: z.array(
    z.object({
      name: z.string(),
      prompt: z.string().optional(),
      type: z.enum(["list", "numbered_steps"]).optional(),
      fields: z
        .array(z.object({ label: z.string() }))
        .optional(),
      columns: z.array(z.string()).optional(),
      rows: z.number().int().optional(),
      optional: z.boolean().optional(),
    }),
  ),
});

// ── 3.5 Measurement ──

export const MeasurementSchema = BaseQuestionSchema.extend({
  type: z.literal("measurement"),
  subtype: z.enum(["tool_reading", "unit_conversion", "estimation"]),
  tool: z
    .object({
      type: z.string(),
      readings: z.array(
        z.object({
          value: z.number(),
          unit: z.string(),
          tolerance: z.number(),
        }),
      ),
    })
    .optional(),
  questions: z.array(
    z.object({
      stem: z.string(),
      correctAnswer: z.string(),
      tolerance: z.number().optional(),
    }),
  ),
});

// ── 3.6 Coding Exercise ──

export const CodingExerciseSchema = BaseQuestionSchema.extend({
  type: z.literal("coding_exercise"),
  subtype: z.enum([
    "trace_output",
    "bug_find",
    "write_code",
    "pseudo_code",
  ]),
  language: z.string().optional(),
  codeBlock: z.string(),
  question: z.string(),
  correctAnswer: z.string(),
});

// ── 3.7 Financial Literacy ──

export const FinancialLiteracySchema = BaseQuestionSchema.extend({
  type: z.literal("financial_literacy"),
  scenario: z.string(),
  questions: z.array(
    z.object({
      type: z.string(),
      stem: z.string(),
      correctAnswer: z.string(),
      tolerance: z.number().optional(),
    }),
  ),
});
