import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";

import { adaptInverseThinking, adaptRootCauseSession, adaptVideoRoute } from "../artifact-ui/adapters/index.js";
import type { ArtifactKindPlugin, RenderContext, RenderServices } from "../core/types.js";

const currentDir = dirname(fileURLToPath(import.meta.url));
const interactivitySourcePath = join(currentDir, "../../src/artifact-ui/interactivity.js");
const interactivityScriptId = "artifact-ui-interactivity";

function sha256File(path: string): string {
  return createHash("sha256").update(readFileSync(path, "utf8")).digest("hex");
}

const managedInteractivity = [{
  id: interactivityScriptId,
  sourcePath: interactivitySourcePath,
  sha256: sha256File(interactivitySourcePath),
}] as const;

const inverseThinkingCaseSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  alias: z.string().nullable().optional(),
  disaster: z.string().min(1),
  key_clues: z.array(z.string()).min(1),
  safe_zone: z.string().min(1),
  filing_note: z.string().min(1),
  student_task: z.string().min(1),
  teacher_only: z.object({ rationale: z.string().min(1), answer_key: z.string().min(1) }),
});

const inverseThinkingInputSchema = z.object({
  artifactType: z.union([z.literal("lesson"), z.literal("worksheet"), z.literal("quiz"), z.literal("drill"), z.literal("teacher_only")]),
  title: z.string().min(1),
  subject: z.string().min(1),
  gradeLevel: z.string().min(1),
  frame: z.union([z.literal("detective_case"), z.literal("neutral")]),
  lang: z.string().optional(),
  cases: z.array(inverseThinkingCaseSchema).min(1),
  summaryTable: z.array(z.object({
    case_id: z.string().min(1),
    trap: z.string().min(1),
    clue: z.string().min(1),
    safe_rule: z.string().min(1),
  })).default([]),
  teacherOnly: z.object({ rationale: z.string().min(1), answer_key: z.string().min(1) }),
});

const rootCauseInputSchema = z.object({
  title: z.string().min(1),
  subtitle: z.string().optional(),
  subject: z.string().min(1),
  gradeLevel: z.string().min(1),
  lang: z.union([z.literal("vi"), z.literal("en")]),
  theme: z.string().optional(),
  sessionCode: z.string().min(1),
  difficulty: z.union([z.literal("low"), z.literal("mid"), z.literal("high")]),
  estimatedMinutes: z.number().positive(),
  targetConcept: z.string().min(1),
  anchorTimeline: z.array(z.object({
    id: z.string().min(1),
    label: z.string().min(1),
    event: z.string().min(1),
    significance: z.string().min(1),
    isKeyAnchor: z.boolean().optional(),
  })),
  comparisons: z.array(z.object({
    id: z.string().min(1),
    constant: z.string().min(1),
    variants: z.array(z.object({ label: z.string().min(1), value: z.string().min(1), isControl: z.boolean().optional() })).min(1),
    insight: z.string().min(1),
  })),
  scenarioAnchors: z.array(z.object({ id: z.string().min(1), scenario: z.string().min(1), connection: z.string().min(1) })).optional(),
  generalizationCheckpoints: z.array(z.object({
    id: z.string().min(1),
    learnerClaim: z.string().min(1),
    verdict: z.union([z.literal("confirmed"), z.literal("refined"), z.literal("rejected")]),
    evidence: z.string().min(1),
    refinedClaim: z.string().optional(),
  })),
  stressTests: z.array(z.object({ id: z.string().min(1), brokenExample: z.string().min(1), whyItBreaks: z.string().min(1), fix: z.string().optional() })).optional(),
  metaphorLogs: z.array(z.object({ id: z.string().min(1), landedAttempt: z.string().min(1), collapsedAttempts: z.array(z.string()).optional() })).optional(),
  masteryMarkers: z.array(z.object({ label: z.string().min(1), level: z.union([z.literal("aware"), z.literal("applying"), z.literal("mastered")]) })).optional(),
  teacherNotes: z.string().optional(),
});

const videoRouteInputSchema = z.object({
  title: z.string().min(1),
  subject: z.string().min(1),
  gradeLevel: z.string().min(1),
  unit: z.string().optional(),
  routeTitle: z.string().optional(),
  estimatedMinutes: z.number().positive().optional(),
  videoMetadata: z.object({
    videoDuration: z.string().optional(),
    videoTitle: z.string().optional(),
    channel: z.string().optional(),
    difficulty: z.union([z.literal("easy"), z.literal("medium"), z.literal("hard")]).optional(),
  }).optional(),
  stations: z.array(z.object({
    code: z.string().min(1),
    title: z.string().min(1),
    description: z.string().min(1),
    catIndex: z.number().int().positive().optional(),
    cues: z.array(z.object({ text: z.string().min(1), emphasis: z.boolean().optional() })).optional(),
  })).min(1),
  completionBadge: z.string().optional(),
  theme: z.string().optional(),
  lang: z.string().optional(),
});

const artifactUiPolicy = { version: "artifact-ui-specialty-policy-v1", config: "artifact_ui" } as const;

function managedInteractivitySource(services: RenderServices): string {
  return services.managedScripts.find((script) => script.id === interactivityScriptId)?.source ?? "";
}

function adaptInverse(input: unknown, context: RenderContext, services: RenderServices) {
  const parsed = inverseThinkingInputSchema.parse(input);
  return adaptInverseThinking(parsed, context.audience, services.themeCss);
}

function adaptRootCause(input: unknown, context: RenderContext, services: RenderServices) {
  const parsed = rootCauseInputSchema.parse(input);
  return adaptRootCauseSession(parsed, context.audience, services.themeCss, managedInteractivitySource(services));
}

function adaptRoute(input: unknown, _context: RenderContext, services: RenderServices) {
  const parsed = videoRouteInputSchema.parse(input);
  return adaptVideoRoute(parsed, services.themeCss);
}

export const inverseThinkingPlugin: ArtifactKindPlugin<ReturnType<typeof adaptInverseThinking>> = {
  kind: "investigation-folder.inverse-thinking",
  version: "0.1.0",
  templateVersion: "inverse-thinking-template-v1",
  themeVersion: "theme-resolver-v1",
  familyId: "investigation-folder",
  schema: inverseThinkingInputSchema,
  audience: { supported: ["teacher", "student"] },
  capabilities: { supportsPrint: true },
  sanitizerPolicy: artifactUiPolicy,
  adapt: adaptInverse,
  templatePath: () => "artifact/investigation-folder/inverse-thinking.html",
};

export const rootCauseSessionPlugin: ArtifactKindPlugin<ReturnType<typeof adaptRootCauseSession>> = {
  kind: "paper-dossier.root-cause-session",
  version: "0.1.0",
  templateVersion: "root-cause-session-template-v1",
  themeVersion: "theme-resolver-v1",
  familyId: "paper-dossier",
  schema: rootCauseInputSchema,
  audience: { supported: ["teacher", "student"] },
  capabilities: { supportsPrint: true },
  sanitizerPolicy: artifactUiPolicy,
  managedScripts: managedInteractivity,
  adapt: adaptRootCause,
  templatePath: () => "artifact/paper-dossier/root-cause-session.html",
};

export const videoRoutePlugin: ArtifactKindPlugin<ReturnType<typeof adaptVideoRoute>> = {
  kind: "transit-route.video-route",
  version: "0.1.0",
  templateVersion: "video-route-template-v1",
  themeVersion: "theme-resolver-v1",
  familyId: "transit-route",
  schema: videoRouteInputSchema,
  audience: { supported: ["teacher", "student"] },
  capabilities: { supportsPrint: true },
  sanitizerPolicy: artifactUiPolicy,
  adapt: adaptRoute,
  templatePath: () => "artifact/transit-route/video-route.html",
};
