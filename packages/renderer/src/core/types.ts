import type { z } from "zod";

export type RenderAudience = "teacher" | "student";
export type RenderLocale = "vi" | "en";
export type RenderMode = "preview" | "export" | "print";
export type RenderAssetPolicy = "inline-only";
export type RenderDiagnosticSeverity = "info" | "warning" | "error";

export type RenderVersionContext = {
  readonly rendererVersion: string;
};

export type RenderContext = {
  readonly audience: RenderAudience;
  readonly locale: RenderLocale;
  readonly theme: string;
  readonly renderMode: RenderMode;
  readonly requestId: string;
  readonly versions: RenderVersionContext;
  readonly assetPolicy: RenderAssetPolicy;
};

export type RenderRequest = {
  readonly kind: string;
  readonly input: unknown;
  readonly context: RenderContext;
};

export type RenderBatchRequest = {
  readonly requests: readonly RenderRequest[];
};

export type RenderDiagnostic = {
  readonly severity: RenderDiagnosticSeverity;
  readonly code: string;
  readonly message: string;
};

export type RenderMetrics = {
  readonly renderTimeMs: number;
};

export type RenderManifest = {
  readonly kind: string;
  readonly rendererVersion: string;
  readonly pluginVersion: string;
  readonly templateVersion: string;
  readonly themeVersion: string;
  readonly sanitizerPolicyVersion: string;
  readonly renderedAt: string;
  readonly contentHash: string;
  readonly childManifests?: readonly RenderManifest[];
};

export type RenderResponse = {
  readonly html: string;
  readonly manifest: RenderManifest;
  readonly diagnostics: readonly RenderDiagnostic[];
  readonly metrics: RenderMetrics;
};

export type AudiencePolicy = {
  readonly supported: readonly RenderAudience[];
};

export type ArtifactKindCapabilities = {
  readonly supportsPrint: boolean;
};

export type SanitizerPolicy = {
  readonly version: string;
  readonly config?: "base" | "quiz" | "infographic" | "lesson" | "answer_key" | "flashcard_deck" | "reading_passage" | "exit_ticket" | "roadmap" | "artifact_ui";
};

export type ManagedScriptDeclaration = {
  readonly id: string;
  readonly sourcePath: string;
  readonly sha256: string;
};

export type ManagedScript = {
  readonly id: string;
  readonly source: string;
  readonly sha256: string;
};

export type RenderServices = {
  readonly themeCss: string;
  readonly managedScripts: readonly ManagedScript[];
  readonly renderChild: (request: RenderRequest) => Promise<RenderResponse>;
};

export type ArtifactKindPlugin<TTemplateData extends object> = {
  readonly kind: string;
  readonly version: string;
  readonly templateVersion: string;
  readonly themeVersion: string;
  readonly schema: z.ZodType<unknown>;
  readonly audience: AudiencePolicy;
  readonly capabilities: ArtifactKindCapabilities;
  readonly sanitizerPolicy: SanitizerPolicy;
  readonly familyId?: string;
  readonly managedScripts?: readonly ManagedScriptDeclaration[];
  readonly adapt: (input: unknown, context: RenderContext, services: RenderServices) => TTemplateData | Promise<TTemplateData>;
  readonly templatePath: (context: RenderContext) => string;
};

export type PluginMetadata = {
  readonly kind: string;
  readonly version: string;
  readonly templateVersion: string;
  readonly themeVersion: string;
  readonly supportedAudiences: readonly RenderAudience[];
  readonly supportsPrint: boolean;
  readonly sanitizerPolicyVersion: string;
};
