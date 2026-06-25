import type { BaseQuestion } from '../base.js';
export interface FillBlankWordBank extends BaseQuestion {
    type: 'fill_blank_wordbank';
    context: string;
    blanks: Array<{
        id: number;
        correctAnswer: string;
    }>;
    wordBank: string[];
    distractors: string[];
    shuffleWordBank: boolean;
}
export interface ClozeMixed extends BaseQuestion {
    type: 'cloze_mixed';
    clozeSubtype: 'grammar' | 'vocabulary' | 'contextual';
    passage: string;
    blanks: Array<{
        id: number;
        correctAnswer: string;
        type: 'grammar' | 'vocabulary';
    }>;
    wordBank?: string[];
    cefr?: string;
}
export interface DialogueTurn {
    speaker: string;
    text: string;
}
export interface DialogueBlank {
    id: number;
    expectedIntent: string;
    expectedAnswer: string;
}
export interface DialogueCompletion extends BaseQuestion {
    type: 'dialogue_completion';
    context: string;
    dialogue: DialogueTurn[];
    blanks: DialogueBlank[];
}
export type FillGapQuestion = FillBlankWordBank | ClozeMixed | DialogueCompletion;
