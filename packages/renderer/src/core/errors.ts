export const RendererErrorCode = {
  DuplicateKind: "duplicate_kind",
  UnknownKind: "unknown_kind",
  ValidationFailed: "validation_failed",
  UnsupportedAudience: "unsupported_audience",
  UnsupportedMode: "unsupported_mode",
  TemplateMissing: "template_missing",
  ExternalAsset: "external_asset",
} as const;

export type RendererErrorCode = (typeof RendererErrorCode)[keyof typeof RendererErrorCode];

export const RendererErrorCategory = {
  Registry: "registry",
  Validation: "validation",
  Policy: "policy",
  Template: "template",
} as const;

export type RendererErrorCategory = (typeof RendererErrorCategory)[keyof typeof RendererErrorCategory];

export class RendererError extends Error {
  readonly code: RendererErrorCode;
  readonly category: RendererErrorCategory;
  readonly retryable: boolean;
  readonly details: Readonly<Record<string, unknown>>;

  constructor(input: {
    readonly code: RendererErrorCode;
    readonly category: RendererErrorCategory;
    readonly message: string;
    readonly retryable?: boolean;
    readonly details?: Readonly<Record<string, unknown>>;
  }) {
    super(input.message);
    this.name = "RendererError";
    this.code = input.code;
    this.category = input.category;
    this.retryable = input.retryable ?? false;
    this.details = input.details ?? {};
  }
}
