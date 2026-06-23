/**
 * AUTO-GENERATED from Pydantic model_json_schema()
 * Source: common/contracts/ → Pydantic → JSON Schema → Zod
 * DO NOT EDIT MANUALLY — run `python scripts/generate_zod_schemas.py` to regenerate
 */

import { z } from "zod"

export const ArtifactContentSchema = z.object({ "artifact_type": z.enum(["lesson","worksheet","quiz","drill","recap","infographic"]), "theme": z.string().describe("Visual theme name").default("default"), "title": z.string().min(3).max(200), "sections": z.array(z.record(z.string(), z.any())).min(1).describe("List of content sections; structure varies by artifact_type"), "metadata": z.record(z.string(), z.any()).describe("Arbitrary metadata (duration, difficulty, etc.)").optional(), "accessibility": z.record(z.string(), z.any()).describe("Language, reading_level, alt_texts, etc.").optional() }).describe("A single artifact within a teaching pack.\n\nThe Content Creator Agent produces JSON conforming to this schema.\nThe template renderer consumes it to produce standalone HTML.")


export const TeachingPackSchema = z.object({ "run_id": z.string().describe("Pipeline run identifier"), "artifacts": z.array(ArtifactContentSchema).optional(), "metadata": z.record(z.string(), z.any()).optional() }).describe("A complete teaching pack containing one or more artifacts.")

export type ArtifactContent = z.infer<typeof ArtifactContentSchema>;
export type TeachingPack = z.infer<typeof TeachingPackSchema>;
