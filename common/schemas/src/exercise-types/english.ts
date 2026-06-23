import { z } from "zod";
import { BaseQuestionSchema, RubricSchema } from "./base.js";

// ── 2.1 Vocabulary Scaffolded ──

export const VocabularyScaffoldedSchema = BaseQuestionSchema.extend({
	type: z.literal("vocabulary_scaffolded"),
	targetWord: z.string(),
	level: z.string(),
	stages: z.array(
		z.object({
			stage: z.enum([
				"recognition",
				"comprehension",
				"production_sentence",
				"production_paragraph",
			]),
			activity: z.record(z.string(), z.unknown()),
		}),
	),
});

// ── 2.2 Cloze Mixed ──

export const ClozeMixedSchema = BaseQuestionSchema.extend({
	type: z.literal("cloze_mixed"),
	clozeSubtype: z.enum(["grammar", "vocabulary", "contextual"]),
	passage: z.string(),
	blanks: z.array(
		z.object({
			id: z.number().int(),
			correctAnswer: z.string(),
			type: z.enum(["grammar", "vocabulary"]),
		}),
	),
	wordBank: z.array(z.string()).optional(),
	cefr: z.string().optional(),
});

// ── 2.3 Matching Vocabulary ──

export const MatchingVocabularySchema = BaseQuestionSchema.extend({
	type: z.literal("matching_vocabulary"),
	matchType: z.enum(["definition", "synonym", "antonym"]),
	leftColumn: z.array(z.object({ id: z.string(), text: z.string() })),
	rightColumn: z.array(
		z.object({
			id: z.string(),
			text: z.string(),
			isDistractor: z.boolean().optional(),
		}),
	),
});

// ── 2.4 Reading Comprehension ──

export const ReadingComprehensionSchema = BaseQuestionSchema.extend({
	type: z.literal("reading_comprehension"),
	passage: z.object({
		text: z.string(),
		source: z.string().optional(),
		wordCount: z.number().int().optional(),
		cefr: z.string().optional(),
	}),
	annotationTools: z
		.array(z.enum(["highlight", "underline", "comment"]))
		.optional(),
	questions: z.array(z.record(z.string(), z.unknown())),
});

// ── 2.5 Grammar Transformation ──

export const GrammarTransformationSchema = BaseQuestionSchema.extend({
	type: z.literal("grammar_transformation"),
	sourceSentence: z.string(),
	expectedAnswer: z.string(),
	acceptableAnswers: z.array(z.string()).default([]),
	grammarPoint: z.string(),
});

// ── 2.6 Error Correction ──

export const ErrorCorrectionSchema = BaseQuestionSchema.extend({
	type: z.literal("error_correction"),
	subtype: z.enum(["identification", "correction"]),
	sentence: z.string(),
	errorLocation: z.string(),
	correction: z.string(),
	grammarPoint: z.string(),
});

// ── 2.7 Sentence Manipulation ──

export const SentenceManipulationSchema = BaseQuestionSchema.extend({
	type: z.literal("sentence_manipulation"),
	subtype: z.enum(["combining", "splitting"]),
	inputSentences: z.array(z.string()),
	expectedOutput: z.string(),
	targetStructure: z.string(),
});

// ── 2.8 Paraphrase ──

export const ParaphraseSchema = BaseQuestionSchema.extend({
	type: z.literal("paraphrase"),
	originalSentence: z.string(),
	techniques: z.array(z.string()),
	sampleAnswer: z.string().optional(),
	rubric: RubricSchema.optional(),
});

// ── 2.9 Dialogue Completion ──

export const DialogueCompletionSchema = BaseQuestionSchema.extend({
	type: z.literal("dialogue_completion"),
	context: z.string(),
	dialogue: z.array(
		z.object({
			speaker: z.string(),
			text: z.string(),
		}),
	),
	blanks: z.array(
		z.object({
			id: z.number().int(),
			expectedIntent: z.string(),
			expectedAnswer: z.string(),
		}),
	),
});

// ── 2.10 Phonics ──

export const PhonicsSchema = BaseQuestionSchema.extend({
	type: z.literal("phonics"),
	subtype: z.enum(["sound_identification", "letter_sound", "blending"]),
	instruction: z.string(),
	items: z.array(
		z.object({
			words: z.array(z.string()),
			correctIndex: z.number().int(),
			reason: z.string(),
		}),
	),
	cefr: z.string().optional(),
});

// ── 2.11 Dictation ──

export const DictationSchema = BaseQuestionSchema.extend({
	type: z.literal("dictation"),
	text: z.string(),
	mode: z.enum(["sentence_by_sentence", "full_passage"]),
	grading: z.object({
		exactMatch: z.boolean(),
		ignorePunctuation: z.boolean(),
		caseSensitive: z.boolean(),
	}),
});

// ── 2.12 Translation ──

export const TranslationSchema = BaseQuestionSchema.extend({
	type: z.literal("translation"),
	direction: z.enum(["en_to_vi", "vi_to_en"]),
	sourceText: z.string(),
	expectedTranslation: z.string(),
	focusPoints: z
		.array(
			z.object({
				source: z.string(),
				note: z.string(),
			}),
		)
		.optional(),
});

// ── 2.13 Idioms ──

export const IdiomsSchema = BaseQuestionSchema.extend({
	type: z.literal("idioms"),
	activity: z.object({
		type: z.enum(["match_meaning", "fill_blank", "identify_context"]),
		idioms: z.array(
			z.object({
				idiom: z.string(),
				meaning: z.string(),
			}),
		),
	}),
});

// ── 2.14 Collocation ──

export const CollocationSchema = BaseQuestionSchema.extend({
	type: z.literal("collocation"),
	collocationType: z.enum([
		"verb_noun",
		"adjective_noun",
		"adverb_adjective",
		"verb_preposition",
	]),
	leftItems: z.array(z.string()),
	rightItems: z.array(z.string()),
	correctPairs: z.array(
		z.object({
			left: z.string(),
			right: z.string(),
		}),
	),
});

// ── 2.15 Word Analysis ──

export const WordAnalysisSchema = BaseQuestionSchema.extend({
	type: z.literal("word_analysis"),
	word: z.string(),
	morphemes: z.array(
		z.object({
			part: z.string(),
			type: z.enum(["prefix", "root", "suffix"]),
			meaning: z.string(),
		}),
	),
	questions: z.array(
		z.object({
			stem: z.string(),
			correctAnswer: z.string(),
		}),
	),
});

// ── 2.16 Tense Timeline ──

export const TenseTimelineSchema = BaseQuestionSchema.extend({
	type: z.literal("tense_timeline"),
	events: z.array(
		z.object({
			time: z.string(),
			label: z.string(),
		}),
	),
	questions: z.array(
		z.object({
			stem: z.string(),
			correctAnswer: z.string(),
			tense: z.string(),
		}),
	),
});

// ── 2.17 Conditional Builder ──

export const ConditionalBuilderSchema = BaseQuestionSchema.extend({
	type: z.literal("conditional_builder"),
	conditionals: z.array(z.enum(["type0", "type1", "type2", "type3", "mixed"])),
	activities: z.array(
		z.object({
			subtype: z.enum(["completion", "transformation", "identification"]),
			stem: z.string().optional(),
			sourceSentence: z.string().optional(),
			correctAnswer: z.string(),
			conditionalType: z.string(),
		}),
	),
});

// ── 2.18 Reported Speech ──

export const ReportedSpeechSchema = BaseQuestionSchema.extend({
	type: z.literal("reported_speech"),
	directSpeech: z.string(),
	expectedAnswer: z.string(),
	changes: z
		.array(
			z.object({
				from: z.string(),
				to: z.string(),
				type: z.enum(["pronoun", "tense", "time", "place"]),
			}),
		)
		.optional(),
});

// ── 2.19 Passive Voice ──

export const PassiveVoiceSchema = BaseQuestionSchema.extend({
	type: z.literal("passive_voice"),
	direction: z.enum(["active_to_passive", "passive_to_active"]),
	activeSentence: z.string().optional(),
	passiveSentence: z.string().optional(),
	expectedPassive: z.string().optional(),
	expectedActive: z.string().optional(),
	tense: z.string(),
});
