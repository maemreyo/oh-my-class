import type { BaseQuestion, Rubric } from '../base.js';
export interface Essay extends BaseQuestion {
    type: 'essay';
    prompt: string;
    wordLimit?: {
        min: number;
        max: number;
    };
    rubric?: Rubric;
}
export interface Paraphrase extends BaseQuestion {
    type: 'paraphrase';
    originalSentence: string;
    techniques: string[];
    sampleAnswer?: string;
    rubric?: Rubric;
}
export interface Translation extends BaseQuestion {
    type: 'translation';
    direction: 'en_to_vi' | 'vi_to_en';
    sourceText: string;
    expectedTranslation: string;
    focusPoints?: Array<{
        source: string;
        note: string;
    }>;
}
export interface LabReportSection {
    name: string;
    prompt?: string;
    type?: 'list' | 'numbered_steps';
    fields?: Array<{
        label: string;
    }>;
    columns?: string[];
    rows?: number;
    optional?: boolean;
}
export interface LabReport extends BaseQuestion {
    type: 'lab_report';
    experimentTitle: string;
    sections: LabReportSection[];
}
export interface Drawing extends BaseQuestion {
    type: 'drawing';
    instructions: string;
    canvas: {
        width: number;
        height: number;
    };
    rubric?: Rubric;
}
export interface Performance extends BaseQuestion {
    type: 'performance';
    task: string;
    format: 'presentation' | 'experiment' | 'speech' | 'project';
    timeLimit?: number;
    rubric?: Rubric;
}
export interface Dictation extends BaseQuestion {
    type: 'dictation';
    text: string;
    mode: 'sentence_by_sentence' | 'full_passage';
    grading: {
        exactMatch: boolean;
        ignorePunctuation: boolean;
        caseSensitive: boolean;
    };
}
export type OpenQuestion = Essay | Paraphrase | Translation | LabReport | Drawing | Performance | Dictation;
