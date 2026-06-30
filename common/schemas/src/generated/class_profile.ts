/**
 * AUTO-GENERATED from Pydantic model_json_schema()
 * Source: common/contracts/ → Pydantic → JSON Schema → Zod
 * DO NOT EDIT MANUALLY — run `python scripts/generate_zod_schemas.py` to regenerate
 */

import { z } from "zod"

export const LearningPreferencesSchema = z.object({ "preferred_modalities": z.array(z.string()).max(8).optional(), "preferred_methodologies": z.array(z.string()).max(8).optional(), "avoid_methodologies": z.array(z.string()).max(8).optional() })


export const StudentProfileSchema = z.object({ "student_id": z.string(), "learning_style": z.lazy(() => LearningStyleSchema), "personality_traits": z.array(z.lazy(() => PersonalityTraitSchema)).optional(), "weaknesses": z.array(z.string()).optional(), "strengths": z.array(z.string()).optional(), "target_score": z.union([z.number().int(), z.null()]).default(null), "target_exam": z.union([z.enum(["HSA","IELTS","TOEIC"]), z.null()]).default(null), "study_duration_months": z.number().int().gte(1).lte(24).default(6), "tools": z.array(z.string()).optional(), "raw_context": z.string().default("") }).describe("Complete learner profile produced by the Profiler Agent.")


export const LearningStyleSchema = z.object({ "primary": z.enum(["visual","auditory","kinesthetic","reading"]), "media_preference": z.union([z.string(), z.null()]).default(null), "format_preference": z.union([z.string(), z.null()]).default(null) }).describe("How the student best absorbs new information.")


export const PersonalityTraitSchema = z.object({ "trait": z.string(), "vn_name": z.string(), "teaching_principle": z.string() }).describe("A single MBTI-style or pedagogical personality trait.")


export const ClassProfileSchema = z.object({ "schema_version": z.literal("class_profile.v1").default("class_profile.v1"), "class_id": z.union([z.string().max(64), z.null()]).default(null), "grade": z.string().min(1).max(64), "age_band": z.enum(["early_primary","upper_primary","lower_secondary","upper_secondary","adult"]), "subject_focus": z.string().min(1).max(80), "language": z.string().min(2).max(32), "class_size": z.number().int().gte(1).lte(80), "proficiency_level": z.enum(["beginner","developing","proficient","advanced"]), "known_misconceptions": z.array(z.string()).max(20).optional(), "prior_knowledge_gaps": z.array(z.string()).max(20).optional(), "learning_preferences": z.lazy(() => LearningPreferencesSchema).optional(), "attention_span_band": z.enum(["short","medium","long"]).default("medium"), "differentiation_needs": z.array(z.string()).max(20).optional(), "prior_topics_taught": z.array(z.string()).max(50).optional(), "students": z.array(z.lazy(() => StudentProfileSchema)).max(40).optional() })

export type ClassProfile = z.infer<typeof ClassProfileSchema>;
export type LearningPreferences = z.infer<typeof LearningPreferencesSchema>;
export type StudentProfile = z.infer<typeof StudentProfileSchema>;
export type LearningStyle = z.infer<typeof LearningStyleSchema>;
export type PersonalityTrait = z.infer<typeof PersonalityTraitSchema>;
