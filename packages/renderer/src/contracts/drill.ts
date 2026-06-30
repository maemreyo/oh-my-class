/**
 * Drill artifact data contract.
 *
 * Used by ContentCreator Agent when artifact_type == "drill".
 * Rendered by pages/drill.html template.
 */

export interface DrillQuestion {
  id: string;
  prompt: string;
  answer: string;
  type: "mc" | "fill" | "tf";
  options?: { label: string; text: string }[];
  timeMinutes?: number;
}

export interface DrillData {
  title: string;
  subject: string;
  gradeLevel: string;
  questions: DrillQuestion[];
  timeLimit?: number;
  theme?: string;
  lang?: string;
}
