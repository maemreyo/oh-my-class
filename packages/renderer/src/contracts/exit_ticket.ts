/**
 * Exit ticket artifact data contract.
 *
 * Used by ContentCreator Agent when artifact_type == "exit_ticket".
 * Rendered by pages/exit_ticket.html template.
 */

export interface ExitTicketQuestion {
  id: string;
  prompt: string;
  type: "mc" | "short_answer" | "rating";
  options?: { label: string; text: string }[];
}

export interface ExitTicketData {
  title: string;
  subject: string;
  gradeLevel: string;
  questions: ExitTicketQuestion[];
  theme?: string;
  lang?: string;
}
