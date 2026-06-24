/**
 * Infographic artifact data contract.
 *
 * Used by ContentCreator Agent when artifact_type == "infographic".
 * Rendered by pages/infographic.html template.
 */

export interface InfographicSection {
  title: string;
  content: string;
}

export interface InfographicData {
  title: string;
  subject: string;
  gradeLevel: string;
  sections: InfographicSection[];
  theme?: string;
  lang?: string;
}
