/**
 * Worksheet artifact data contract.
 *
 * Used by ContentCreator Agent when artifact_type == "worksheet".
 * Rendered by pages/worksheet.html template.
 */

export interface WorksheetSection {
  title: string;
  questions: {
    id: string;
    prompt: string;
    type: string;
  }[];
}

export interface WorksheetData {
  title: string;
  subject: string;
  gradeLevel: string;
  sections: WorksheetSection[];
  theme?: string;
  lang?: string;
}
