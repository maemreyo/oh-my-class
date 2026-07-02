export {
  adaptNavyTicketTeaching,
  adaptNavyTicketPractice,
} from "./navy-ticket.js";
export type {
  NavyTicketAudience,
  NavyTicketKind,
  NavyTicketTeachingTemplateData,
  NavyTicketPracticeTemplateData,
} from "./navy-ticket.js";

export { adaptLesson, adaptAnswerKey, adaptRootCauseSession } from "./paper-dossier.js";
export type {
  PaperDossierAudience,
  PaperDossierLessonTemplateData,
  PaperDossierAnswerKeyTemplateData,
  PaperDossierRootCauseTemplateData,
  AnswerKeyQuestion,
} from "./paper-dossier.js";

export { adaptVideoRoute, adaptVideoRouteLegacy } from "./transit-route.js";
export type {
  VideoRouteInput,
  VideoRouteStation_Legacy,
  TransitRouteVideoTemplateData,
  TemplateStation,
} from "./transit-route.js";

export { adaptInverseThinking } from "./investigation-folder.js";
export type {
  InvestigationFolderAudience,
  InvestigationFolderFrameVariant,
  InvestigationFolderTemplateData,
} from "./investigation-folder.js";
