/**
 * renderArtifactUi() — public entry point for all Artifact UI rendering.
 *
 * Pipeline: loadArtifactCSS → (load interactivity.js) → adapt contract
 *           → eta.renderAsync → sanitizeArtifactUi
 *
 * `audience` is always explicit — never inferred. Missing it is a TS error.
 */

import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import type { SemanticAnchorCluster, PracticeSet } from "@oh-my-class/schemas";
import { eta } from "../eta-engine.js";
import { sanitizeArtifactUi } from "../sanitizer/index.js";
import { loadArtifactCSS } from "./loader.js";
import { getFamily } from "./registry.js";
import {
  adaptNavyTicketTeaching,
  adaptNavyTicketPractice,
  adaptLesson,
  adaptAnswerKey,
  adaptRootCauseSession,
  adaptVideoRoute,
  adaptInverseThinking,
} from "./adapters/index.js";
import type { LessonData } from "../contracts/lesson.js";
import type { AnswerKeyData } from "../contracts/answer_key.js";
import type { RootCauseSessionData } from "../contracts/root-cause-session.js";
import type { VideoRouteData } from "../contracts/video-route.js";
import type { InverseThinkingRenderInput } from "../inverse-thinking-renderer.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

// Loaded once; module-level because interactivity.js never changes at runtime.
let _interactivityJS: string | undefined;
function getInteractivityJS(): string {
  if (_interactivityJS === undefined) {
    _interactivityJS = readFileSync(
      join(__dirname, "../artifact-ui/interactivity.js"),
      "utf-8",
    );
  }
  return _interactivityJS;
}

// ── Request types ─────────────────────────────────────────────────────────────

export type ArtifactUiAudience = "teacher" | "student";

interface BaseRequest {
  readonly audience: ArtifactUiAudience;
  readonly lang?: string;
}

export interface NavyTicketTeachingRequest extends BaseRequest {
  readonly family: "navy-ticket";
  readonly kind: "teaching";
  readonly cluster: SemanticAnchorCluster;
}

export interface NavyTicketPracticeRequest extends BaseRequest {
  readonly family: "navy-ticket";
  readonly kind: "practice";
  readonly cluster: SemanticAnchorCluster;
  readonly practiceSet: PracticeSet;
}

export interface PaperDossierLessonRequest extends BaseRequest {
  readonly family: "paper-dossier";
  readonly kind: "lesson";
  readonly data: LessonData;
}

export interface PaperDossierAnswerKeyRequest extends BaseRequest {
  readonly family: "paper-dossier";
  readonly kind: "answer-key";
  readonly data: AnswerKeyData;
}

export interface PaperDossierRootCauseRequest extends BaseRequest {
  readonly family: "paper-dossier";
  readonly kind: "root-cause-session";
  readonly data: RootCauseSessionData;
}

export interface TransitRouteRequest extends BaseRequest {
  readonly family: "transit-route";
  readonly kind: "video-route";
  readonly data: VideoRouteData;
}

export interface InvestigationFolderRequest extends BaseRequest {
  readonly family: "investigation-folder";
  readonly kind: "inverse-thinking";
  readonly data: InverseThinkingRenderInput;
}

export type ArtifactUiRenderRequest =
  | NavyTicketTeachingRequest
  | NavyTicketPracticeRequest
  | PaperDossierLessonRequest
  | PaperDossierAnswerKeyRequest
  | PaperDossierRootCauseRequest
  | TransitRouteRequest
  | InvestigationFolderRequest;

// ── Adapter dispatch ──────────────────────────────────────────────────────────

type TemplateData = Record<string, unknown>;

function buildTemplateData(request: ArtifactUiRenderRequest, css: string): TemplateData {
  switch (request.family) {
    case "navy-ticket": {
      if (request.kind === "teaching") {
        return adaptNavyTicketTeaching(request.cluster, request.audience, css, request.lang) as unknown as TemplateData;
      }
      return adaptNavyTicketPractice(request.cluster, request.practiceSet, request.audience, css, request.lang) as unknown as TemplateData;
    }

    case "paper-dossier": {
      if (request.kind === "lesson") {
        return adaptLesson(request.data, css) as unknown as TemplateData;
      }
      if (request.kind === "answer-key") {
        return adaptAnswerKey(request.data, css, getInteractivityJS()) as unknown as TemplateData;
      }
      return adaptRootCauseSession(request.data, request.audience, css, getInteractivityJS()) as unknown as TemplateData;
    }

    case "transit-route":
      return adaptVideoRoute(request.data, css) as unknown as TemplateData;

    case "investigation-folder":
      return adaptInverseThinking(request.data, request.audience, css) as unknown as TemplateData;
  }
}

// ── Template path helper ──────────────────────────────────────────────────────

function templatePath(family: string, kind: string, audience?: ArtifactUiAudience): string {
  // Always include .html — names like 'teaching.teacher' look like they have
  // a '.teacher' extension, which would prevent Eta from appending defaultExtension.
  if (family === "navy-ticket") {
    return `artifact/${family}/${kind}.${audience}.html`;
  }
  return `artifact/${family}/${kind}.html`;
}

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Render a single Artifact UI projection.
 *
 * Always async — Eta's renderAsync is the underlying engine.
 * Returns a sanitized, standalone HTML string (no CDN, no external assets).
 */
export async function renderArtifactUi(request: ArtifactUiRenderRequest): Promise<string> {
  // Validate family — throws descriptive error for unknown IDs
  getFamily(request.family);

  const css = loadArtifactCSS(request.family);
  const templateData = buildTemplateData(request, css);
  const tmpl = templatePath(request.family, request.kind, request.audience);

  const raw = await eta.renderAsync(tmpl, templateData);
  if (raw === undefined) {
    throw new Error(
      `Artifact UI template not found: "${tmpl}". ` +
      `Check that templates/artifact/${request.family}/${request.kind}.html exists.`,
    );
  }

  return sanitizeArtifactUi(raw);
}

// ── Batch convenience — navy-ticket projections ────────────────────────────────

export interface ArtifactUiSetRequest {
  readonly cluster: SemanticAnchorCluster;
  readonly practiceSet: PracticeSet;
  readonly lang?: string;
}

export interface ArtifactUiSet {
  readonly teachingTeacher: string;
  readonly teachingStudent: string;
  readonly practiceTeacher: string;
  readonly practiceStudent: string;
}

/**
 * Renders all 4 navy-ticket projections for a vocabulary cluster in parallel.
 * Drop-in replacement for the old renderSemanticAnchorProjectionSet() shape.
 */
export async function renderArtifactUiSet(request: ArtifactUiSetRequest): Promise<ArtifactUiSet> {
  const [teachingTeacher, teachingStudent, practiceTeacher, practiceStudent] =
    await Promise.all([
      renderArtifactUi({ family: "navy-ticket", kind: "teaching", audience: "teacher", cluster: request.cluster, lang: request.lang }),
      renderArtifactUi({ family: "navy-ticket", kind: "teaching", audience: "student", cluster: request.cluster, lang: request.lang }),
      renderArtifactUi({ family: "navy-ticket", kind: "practice", audience: "teacher", cluster: request.cluster, practiceSet: request.practiceSet, lang: request.lang }),
      renderArtifactUi({ family: "navy-ticket", kind: "practice", audience: "student", cluster: request.cluster, practiceSet: request.practiceSet, lang: request.lang }),
    ]);
  return { teachingTeacher, teachingStudent, practiceTeacher, practiceStudent };
}
