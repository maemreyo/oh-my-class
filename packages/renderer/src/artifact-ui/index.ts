export { loadArtifactCSS, clearArtifactCSSCache } from "./loader.js";
export { ARTIFACT_FAMILIES, getFamily } from "./registry.js";
export type { ArtifactFamily, ArtifactFamilyId } from "./registry.js";

export { renderArtifactUi, renderArtifactUiSet } from "./renderer.js";
export type {
  ArtifactUiAudience,
  ArtifactUiRenderRequest,
  ArtifactUiSetRequest,
  ArtifactUiSet,
  NavyTicketTeachingRequest,
  NavyTicketPracticeRequest,
  PaperDossierLessonRequest,
  PaperDossierAnswerKeyRequest,
  PaperDossierRootCauseRequest,
  TransitRouteRequest,
  InvestigationFolderRequest,
} from "./renderer.js";
