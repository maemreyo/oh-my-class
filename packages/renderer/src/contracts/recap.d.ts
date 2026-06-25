/**
 * Recap artifact data contract.
 *
 * Used by ContentCreator Agent when artifact_type == "recap".
 * Rendered by pages/recap.html template.
 */
export interface RecapItem {
    id: string;
    concept: string;
    summary: string;
}
export interface RecapData {
    title: string;
    subject: string;
    gradeLevel: string;
    items: RecapItem[];
    theme?: string;
    lang?: string;
}
