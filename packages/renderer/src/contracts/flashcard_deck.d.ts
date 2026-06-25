/**
 * Flashcard deck artifact data contract.
 *
 * Used by ContentCreator Agent when artifact_type == "flashcard_deck".
 * Rendered by pages/flashcard_deck.html template.
 */
export interface Flashcard {
    id: string;
    front: string;
    back: string;
    hint?: string;
}
export interface FlashcardDeckData {
    title: string;
    subject: string;
    gradeLevel: string;
    cards: Flashcard[];
    theme?: string;
    lang?: string;
}
