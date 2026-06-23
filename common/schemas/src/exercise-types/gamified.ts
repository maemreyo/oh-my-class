import { z } from "zod";
import { BaseQuestionSchema } from "./base.js";

// ── 6.1 Timed Challenge ──

export const TimedChallengeSchema = z.object({
  type: z.literal("timed_challenge"),
  timerMode: z.enum(["per_question", "total"]),
  defaultTimeLimit: z.number().int(),
  difficultyTimeMultipliers: z.record(z.string(), z.number()).optional(),
  scoring: z.object({
    basePoints: z.number(),
    timeBonus: z.boolean(),
    timeBonusFormula: z.string().optional(),
    streakBonus: z.number().optional(),
  }),
});

// ── 6.2 Streak System ──

export const StreakSystemSchema = z.object({
  type: z.literal("streak_system"),
  dailyStreak: z.object({
    enabled: z.boolean(),
    resetHour: z.number().int(),
    freezeItem: z.string().optional(),
    freezeCost: z.number().int().optional(),
  }),
  combo: z.object({
    enabled: z.boolean(),
    multiplierStep: z.number(),
    maxMultiplier: z.number(),
    comboBreakOnWrong: z.boolean(),
    comboBreakOnTimeout: z.boolean(),
  }),
});

// ── 6.4 Adaptive Difficulty ──

export const AdaptiveDifficultySchema = z.object({
  type: z.literal("adaptive_difficulty"),
  algorithm: z.enum(["elo_based", "item_response_theory"]),
  startingDifficulty: z.string(),
  adjustmentRules: z.record(
    z.string(),
    z.object({
      action: z.enum([
        "increase_difficulty",
        "decrease_difficulty",
        "maintain",
      ]),
      target: z.string(),
    }),
  ),
  eloConfig: z
    .object({
      kFactor: z.number(),
      initialRating: z.number(),
      questionRatingRange: z.tuple([z.number(), z.number()]),
    })
    .optional(),
  targetAccuracy: z.number().min(0).max(1),
});

// ── 6.5 Branching Scenario ──

export const BranchingScenarioNodeSchema = z.object({
  id: z.string(),
  prompt: z.string(),
  choices: z.array(
    z.object({
      text: z.string(),
      nextNode: z.string(),
      xpReward: z.number().int().optional(),
    }),
  ),
  question: z.record(z.string(), z.unknown()).optional(),
});

export const BranchingScenarioSchema = BaseQuestionSchema.extend({
  type: z.literal("branching_scenario"),
  title: z.string(),
  initialPrompt: z.string(),
  nodes: z.array(BranchingScenarioNodeSchema),
  outcomes: z.record(z.string(), z.string()),
});

// ── 6.7 Collaborative Activity ──

export const CollaborativeActivitySchema = BaseQuestionSchema.extend({
  type: z.literal("collaborative_activity"),
  groupSize: z.object({
    min: z.number().int(),
    max: z.number().int(),
  }),
  roles: z.array(z.string()),
  structure: z.enum([
    "jigsaw",
    "think_pair_share",
    "gallery_walk",
    "debate",
  ]),
  task: z.string(),
  deliverable: z.string(),
  peerReview: z
    .object({
      enabled: z.boolean(),
      criteria: z.array(z.string()),
    })
    .optional(),
});
